# SPEC-009 — Isolamento de Marcas e Pipeline Configurável

**Data:** 27/03/2026
**Baseado em:** PRD-009
**Status:** EM EXECUÇÃO

---

## Contexto

A plataforma cresceu de single-brand (BO) para multi-brand, mas mantém fallbacks silenciosos que assumem BO quando dados de marca estão ausentes. Além disso, a lógica `perfil.sigla == "RC"` hardcoded decide se um projeto é instrumental — deveria ser uma configuração do perfil.

Este SPEC detalha 7 blocos de implementação, 28 tarefas atômicas, com arquivo exato, linha, código atual e código alvo.

**Princípios (definidos no PRD-009 §4.2):**
1. Zero fallback entre marcas — ausência de dado = erro, não "usa BO"
2. Cada marca usa exclusivamente seus próprios dados
3. Configuração via frontend (Admin), sem código
4. Pipeline configurável — `sem_lyrics_default` no perfil
5. Override por projeto na importação
6. Campos obrigatórios para criar/editar marca
7. Warning (não bloqueio) para post sem estrutura

---

## Ordem de execução

```
BLOCO 1 — Pipeline configurável por marca (T1–T8)     ← mais impactante
BLOCO 2 — Remover fallbacks BO (T9–T11)               ← segurança
BLOCO 5 — Campos obrigatórios (T18–T20)               ← previne marcas incompletas
BLOCO 3 — Post prompt com warning (T12–T15)            ← UX informativo
BLOCO 4 — UI editor: esconder etapas (T16–T17)         ← UX visual
BLOCO 6 — Curadoria downloads por marca (T21–T26)      ← melhoria
BLOCO 7 — Prompts Gemini genéricos (T27–T28)           ← baixa prioridade
```

---

## BLOCO 1 — Pipeline configurável por marca

**Objetivo:** Substituir todo `perfil.sigla == "RC"` por campo booleano `sem_lyrics_default` no perfil.

---

### T1 — Adicionar campo `sem_lyrics_default` no model Perfil

**Arquivo:** `app-editor/backend/app/models/perfil.py`
**Linha:** após linha 23 (último campo booleano `ativo`)

**Adicionar:**
```python
sem_lyrics_default = Column(Boolean, default=False, nullable=False, server_default="false")
```

**Critério de feito:** Model Python tem o campo. Não afeta nada até a migration rodar.

---

### T2 — Migration: adicionar coluna + seed RC com True

**Arquivo:** `app-editor/backend/app/main.py`
**Localização:** seção de migrations (após as ALTERs existentes, antes do seed RC)

**Adicionar migration:**
```python
# --- SPEC-009: sem_lyrics_default ---
cur.execute("""
    ALTER TABLE editor_perfis
    ADD COLUMN IF NOT EXISTS sem_lyrics_default BOOLEAN NOT NULL DEFAULT FALSE
""")

# Seed: RC é instrumental por padrão
cur.execute("""
    UPDATE editor_perfis SET sem_lyrics_default = TRUE WHERE sigla = 'RC'
""")
```

**Critério de feito:** Após restart, `SELECT sigla, sem_lyrics_default FROM editor_perfis` retorna `BO=false, RC=true`.

---

### T3 — Trocar hardcode `sigla == "RC"` na importação

**Arquivo:** `app-editor/backend/app/routes/importar.py`
**Linha:** ~213

**Código atual:**
```python
eh_instrumental_final = eh_instrumental or (perfil is not None and perfil.sigla == "RC")
```

**Código novo:**
```python
eh_instrumental_final = eh_instrumental or (perfil is not None and perfil.sem_lyrics_default)
```

**Critério de feito:** Criar marca fictícia com `sem_lyrics_default=True` e importar projeto — deve setar `sem_lyrics=True` automaticamente. Criar com `False` — deve respeitar o parâmetro `eh_instrumental` passado.

---

### T4 — Incluir `sem_lyrics_default` nos schemas de leitura/escrita do admin

**Arquivo:** `app-editor/backend/app/routes/admin_perfil.py`

**Modificar 3 schemas:**

1. **`PerfilListItem`** (~linha 80-94) — adicionar:
   ```python
   sem_lyrics_default: bool = False
   ```

2. **`PerfilDetalheOut`** (~linha 103-156) — adicionar:
   ```python
   sem_lyrics_default: bool = False
   ```

3. **Endpoint PUT `atualizar_perfil`** (~linha 339-359) — garantir que `sem_lyrics_default` é aceito no body e salvo. Se o endpoint usa `**dados.dict()` genérico, já funciona. Se lista campos explicitamente, adicionar.

4. **Endpoint POST `criar_perfil`** (~linha 302-336) — mesma verificação.

**Critério de feito:** `GET /api/v1/editor/admin/perfis` retorna `sem_lyrics_default` para cada perfil. `PUT` aceita alterar o campo.

---

### T5 — Adicionar `sem_lyrics_default` no tipo TypeScript `Perfil`

**Arquivo:** `app-portal/lib/api/editor.ts`
**Localização:** interface `Perfil` (~linha 204-249)

**Adicionar campo:**
```typescript
sem_lyrics_default: boolean;
```

**Critério de feito:** TypeScript compila sem erro.

---

### T6 — Toggle "Marca instrumental" na edição de marca

**Arquivo:** `app-portal/app/(app)/admin/marcas/[id]/page.tsx`
**Localização:** seção de configurações gerais do formulário

**Adicionar toggle/checkbox:**
```tsx
<div className="flex items-center gap-3">
  <input
    type="checkbox"
    id="sem_lyrics_default"
    checked={formData.sem_lyrics_default ?? false}
    onChange={(e) => setFormData({...formData, sem_lyrics_default: e.target.checked})}
  />
  <label htmlFor="sem_lyrics_default" className="text-sm">
    Marca instrumental (sem letra por padrão)
  </label>
  <p className="text-xs text-gray-500">
    Quando ativo, projetos importados desta marca serão automaticamente tratados como instrumentais.
    O operador pode alterar por projeto na importação.
  </p>
</div>
```

**Critério de feito:** Admin pode ligar/desligar "instrumental" para qualquer marca. Valor persiste após salvar.

---

### T7 — Mesmo toggle na criação de marca

**Arquivo:** `app-portal/app/(app)/admin/marcas/nova/page.tsx`
**Localização:** seção de configurações gerais (~linhas 160-221)

**Mudanças:**
1. Adicionar `sem_lyrics_default: false` no estado inicial do form (~linha 70-103)
2. Adicionar o mesmo toggle da T6 no formulário

**Critério de feito:** Criar nova marca com toggle ativo → `sem_lyrics_default=true` no banco.

---

### T8 — Usar `sem_lyrics_default` no toggle da fila de edição

**Arquivo:** `app-portal/components/editor/editing-queue.tsx`
**Localização:** onde o default do toggle instrumental é definido

**Buscar por:** qualquer referência a `sigla === "RC"` ou `sigla == "RC"` ou hardcode de instrumental

**Código atual (se existir):**
```typescript
const isRC = selectedBrand?.sigla === "RC"
```

**Código novo:**
```typescript
const defaultInstrumental = selectedBrand?.sem_lyrics_default ?? false
```

**Se não houver referência direta a `sigla === "RC"`:** verificar se o toggle de "Sem Lyrics" na importação tem um default. Se sim, substituir pelo campo do perfil. Se não existe toggle, este item é N/A.

**Critério de feito:** Ao selecionar marca com `sem_lyrics_default=true`, o toggle de instrumental na importação já vem ligado. Ao selecionar marca com `false`, vem desligado. Operador pode alterar manualmente (override por projeto).

---

## BLOCO 2 — Remover fallbacks BO

**Objetivo:** Erro explícito quando dados de marca estão ausentes.

---

### T9 — Remover fallback `Perfil.sigla == "BO"` na importação

**Arquivo:** `app-editor/backend/app/routes/importar.py`
**Linhas:** ~155-165

**Código atual:**
```python
perfil = None
if perfil_id:
    perfil = db.get(Perfil, perfil_id)
    if not perfil:
        raise HTTPException(404, f"Perfil #{perfil_id} não encontrado")
else:
    perfil = db.query(Perfil).filter(Perfil.sigla == "BO").first()
```

**Código novo:**
```python
if not perfil_id:
    raise HTTPException(400, "perfil_id é obrigatório para importação")
perfil = db.get(Perfil, perfil_id)
if not perfil:
    raise HTTPException(404, f"Perfil #{perfil_id} não encontrado")
```

**Critério de feito:** Chamada POST `/importar-redator/{id}` sem `perfil_id` → HTTP 400. Com `perfil_id` válido → funciona. Com `perfil_id` inválido → HTTP 404.

---

### T10 — Remover `BRAND_SLUG` default no config do redator

**Arquivo:** `app-redator/backend/config.py`
**Linha 27 e função `load_brand_config` linhas 33-55**

**Código atual (linha 27):**
```python
BRAND_SLUG = os.getenv("BRAND_SLUG", "best-of-opera")
```

**Código atual (função, ~linha 35):**
```python
def load_brand_config(slug: str = None) -> dict:
    target_slug = slug or BRAND_SLUG
```

**Código novo:**

Linha 27 — remover a variável `BRAND_SLUG` completamente (ou manter como fallback SOMENTE para o env var, sem default):
```python
BRAND_SLUG = os.getenv("BRAND_SLUG")  # sem default — None se não configurado
```

Função — exigir slug:
```python
def load_brand_config(slug: str) -> dict:
    if not slug:
        raise ValueError("slug da marca é obrigatório para carregar configuração")
    target_slug = slug
```

**Impacto colateral:** verificar TODOS os call sites de `load_brand_config()` no redator para garantir que passam `slug`. Buscar:
```
grep -rn "load_brand_config" app-redator/
```

Call sites esperados:
- `routers/generation.py` — já passa `brand_slug` do projeto
- Qualquer outro caller deve ser atualizado

**Critério de feito:** `load_brand_config()` sem argumento → `ValueError`. `load_brand_config("best-of-opera")` → funciona. `load_brand_config("reels-classics")` → funciona.

---

### T11 — Remover default "best-of-opera" no model Project do redator

**Arquivo:** `app-redator/backend/models.py`
**Linha:** ~44

**Código atual:**
```python
brand_slug: Mapped[str] = mapped_column(String(50), default="best-of-opera")
```

**Código novo:**
```python
brand_slug: Mapped[str] = mapped_column(String(50), nullable=False)
```

**Impacto:** projetos existentes no banco já têm `brand_slug` preenchido (não há NULLs). Novos projetos DEVEM passar `brand_slug` na criação.

**Verificar:** endpoint `POST /projects` em `routers/projects.py` — garantir que `brand_slug` é campo obrigatório no schema de criação.

**Critério de feito:** Criar projeto sem `brand_slug` → erro de validação. Criar com `brand_slug` → funciona.

---

## BLOCO 3 — Post prompt com warning

**Objetivo:** Quando `custom_post_structure` está vazio, gerar com aviso, não bloquear.

---

### T12 — `generate_post` retorna dict com warning

**Arquivo:** `app-redator/backend/services/claude_service.py`
**Função:** `generate_post` (~linha 301-310)

**Código atual:**
```python
def generate_post(project, custom_prompt: Optional[str] = None, brand_config=None) -> str:
    # ... lógica ...
    return result
```

**Código novo:**
```python
def generate_post(project, custom_prompt: Optional[str] = None, brand_config=None) -> dict:
    custom_post = (brand_config or {}).get("custom_post_structure", "")
    warning = None
    if not custom_post:
        warning = "Estrutura de post não configurada para esta marca. Usando estrutura padrão de 5 seções."

    lang = detect_hook_language(project)
    system = _build_language_system_prompt(lang)
    if custom_prompt:
        prompt = build_post_prompt_with_custom(project, custom_prompt, brand_config=brand_config)
    else:
        prompt = build_post_prompt(project, brand_config=brand_config)
    result = _call_claude(prompt, system=system)
    _check_language_leak(result, lang)
    return {"text": result, "warning": warning}
```

**Critério de feito:** Função retorna `dict` com chaves `text` e `warning`. Warning é `None` quando `custom_post_structure` está preenchido.

---

### T13 — Ajustar callers de `generate_post` para o novo retorno

**Arquivo:** `app-redator/backend/routers/generation.py`
**Localização:** endpoint de geração (~linhas 53-84)

**Buscar:** todas as chamadas a `generate_post()` e ajustar para o novo formato `dict`.

**Código atual (aproximado):**
```python
post_text = generate_post(project, brand_config=brand_config)
project.post_text = post_text
```

**Código novo:**
```python
post_result = generate_post(project, brand_config=brand_config)
project.post_text = post_result["text"]
# warning será propagado no response
```

**Critério de feito:** Geração de post funciona. Campo `post_text` é salvo corretamente (string, não dict).

---

### T14 — Propagar warning no response da API

**Arquivo:** `app-redator/backend/routers/generation.py`

**Adicionar warning no response JSON do endpoint de geração:**
```python
warnings = []
if post_result.get("warning"):
    warnings.append(post_result["warning"])
# No response:
return {"status": "ok", "warnings": warnings, ...}
```

**Critério de feito:** Response da API inclui `warnings: []` (vazio quando tudo ok) ou `warnings: ["Estrutura de post não configurada..."]`.

---

### T15 — Exibir warning no frontend do redator

**Arquivo:** `app-portal/components/redator/` — componente de aprovação de post (verificar nome exato)

**Buscar por:** componente que exibe o post gerado para aprovação.

**Adicionar:** banner amarelo quando a API retorna warning:
```tsx
{warnings?.length > 0 && (
  <div className="bg-yellow-50 border border-yellow-200 text-yellow-800 px-4 py-2 rounded text-sm mb-4">
    {warnings.map((w, i) => <p key={i}>{w}</p>)}
  </div>
)}
```

**Critério de feito:** Ao gerar post para marca sem `custom_post_structure`, banner amarelo aparece. Com `custom_post_structure` preenchido, nada aparece.

---

### T15b — Atualizar label no admin

**Arquivo:** `app-portal/app/(app)/admin/marcas/[id]/page.tsx`
**Localização:** campo `custom_post_structure` (~linha 496)

**Código atual (descrição):**
```
"Deixe vazio para usar o padrão"
```

**Código novo:**
```
"Recomendado — define a formatação do post. Se vazio, será usada estrutura genérica com aviso."
```

**Critério de feito:** Label atualizado no Admin.

---

## BLOCO 4 — UI editor: esconder etapas para instrumental

**Objetivo:** Edições com `sem_lyrics=True` não mostram etapas de letra/transcrição/alinhamento.

---

### T16 — Condicionar exibição de etapas no overview

**Arquivo:** `app-portal/components/editor/overview.tsx`
**Localização:** seção que lista os passos/etapas (~linhas 41-176)

**Verificar:** como as etapas são listadas. Pode ser um array de steps ou itens individuais.

**Lógica a aplicar:**
- Etapas de **letra** (passo 4), **alinhamento** (passo 5) devem ser condicionadas a `!edicao.sem_lyrics`
- Se as etapas são numeradas 1-9, os passos 4 e 5 ficam ocultos quando `sem_lyrics=true`

**Pseudocódigo:**
```tsx
const steps = [
  { num: 1, label: "Download", always: true },
  { num: 2, label: "Áudio", always: true },
  { num: 3, label: "Corte", always: true },
  { num: 4, label: "Letra", always: false },      // sem_lyrics=true → oculto
  { num: 5, label: "Alinhamento", always: false }, // sem_lyrics=true → oculto
  { num: 6, label: "Overlay", always: true },
  { num: 7, label: "Tradução", always: true },
  { num: 8, label: "Render", always: true },
  { num: 9, label: "Pacote", always: true },
]

const visibleSteps = steps.filter(s => s.always || !edicao.sem_lyrics)
```

**Critério de feito:** Overview de edição RC mostra apenas etapas relevantes. Overview de edição BO mostra todas.

---

### T17 — Redirecionar páginas de letra/alinhamento para instrumental

**Arquivo:** `app-portal/app/(app)/editor/edicao/[id]/letra/` e `/alinhamento/`

**Verificar:** se já existe redirect para `sem_lyrics=True` (PRD-009 menciona que página de letra já redireciona).

**Se não existe ou é parcial:**
```tsx
// No topo do componente de página
if (edicao.sem_lyrics) {
  redirect(`/editor/edicao/${edicao.id}/overview`)
  return null
}
```

**Critério de feito:** Navegar manualmente para `/editor/edicao/{rc_id}/letra` redireciona para overview.

---

## BLOCO 5 — Campos obrigatórios na criação de marca

**Objetivo:** Não permitir criar/salvar marca sem campos essenciais.

**Campos obrigatórios:**
- `identity_prompt_redator` (Identidade da marca)
- `tom_de_voz_redator` (Tom de voz)
- `escopo_conteudo` (Escopo de conteúdo)
- `custom_post_structure` (Estrutura do post) — **warning, não bloqueio** (por decisão no PRD-009 §4.2 item 7)

---

### T18 — Validação backend na criação/edição de perfil

**Arquivo:** `app-editor/backend/app/routes/admin_perfil.py`
**Localização:** endpoints POST `criar_perfil` (~linha 302) e PUT `atualizar_perfil` (~linha 339)

**Adicionar validação:**
```python
CAMPOS_OBRIGATORIOS_MARCA = ["identity_prompt_redator", "tom_de_voz_redator", "escopo_conteudo"]

def _validar_campos_marca(dados: dict):
    faltando = [c for c in CAMPOS_OBRIGATORIOS_MARCA if not dados.get(c, "").strip()]
    if faltando:
        raise HTTPException(
            422,
            detail=f"Campos obrigatórios não preenchidos: {', '.join(faltando)}"
        )
    # Warning para custom_post_structure (não bloqueia)
    warnings = []
    if not dados.get("custom_post_structure", "").strip():
        warnings.append("custom_post_structure não definido — posts usarão estrutura genérica")
    return warnings
```

**Chamar em POST e PUT:**
```python
warnings = _validar_campos_marca(dados.dict())
# ... salvar ...
return {"perfil": perfil_out, "warnings": warnings}
```

**Critério de feito:** Criar marca sem `identity_prompt_redator` → HTTP 422. Criar sem `custom_post_structure` → salva com warning no response.

---

### T19 — Validação frontend na criação de marca

**Arquivo:** `app-portal/app/(app)/admin/marcas/nova/page.tsx`
**Localização:** função de submit do formulário

**Adicionar validação antes de enviar:**
```typescript
const REQUIRED_FIELDS = [
  { key: "identity_prompt_redator", label: "Identidade da marca" },
  { key: "tom_de_voz_redator", label: "Tom de voz" },
  { key: "escopo_conteudo", label: "Escopo de conteúdo" },
]

const missing = REQUIRED_FIELDS.filter(f => !formData[f.key]?.trim())
if (missing.length > 0) {
  alert(`Preencha os campos obrigatórios: ${missing.map(f => f.label).join(", ")}`)
  return
}
```

**Adicionar indicação visual:** asterisco vermelho `*` nos labels dos campos obrigatórios.

**Critério de feito:** Submit sem campos obrigatórios → mensagem de erro, não envia. Com campos → funciona.

---

### T20 — Validação frontend na edição de marca

**Arquivo:** `app-portal/app/(app)/admin/marcas/[id]/page.tsx`
**Localização:** função `handleSave`

**Mesma validação da T19.** Copiar a lógica de validação (ou extrair para helper compartilhado se preferir, mas não obrigatório).

**Critério de feito:** Salvar marca editada com campo obrigatório vazio → mensagem de erro.

---

## BLOCO 6 — Curadoria: filtro de downloads por marca

**Objetivo:** Downloads filtráveis por marca, com filtro dinâmico.

---

### T21 — Adicionar coluna `brand_slug` na tabela downloads

**Arquivo:** `app-curadoria/backend/database.py`
**Localização:** CREATE TABLE downloads (~linhas 149-160)

**Adicionar à DDL:**
```sql
brand_slug TEXT DEFAULT NULL
```

**E adicionar migration separada (no init):**
```python
cur.execute("ALTER TABLE downloads ADD COLUMN IF NOT EXISTS brand_slug TEXT DEFAULT NULL")
```

**Critério de feito:** Tabela tem coluna `brand_slug`. Downloads antigos têm `NULL`.

---

### T22 — `save_download()` aceita e salva `brand_slug`

**Arquivo:** `app-curadoria/backend/database.py`
**Função:** `save_download` (~linhas 375-381)

**Código atual (aproximado):**
```python
def save_download(video_id, ...):
    cur.execute("INSERT INTO downloads (...) VALUES (...)", (...))
```

**Adicionar:** parâmetro `brand_slug=None` e incluir na query INSERT.

**Critério de feito:** `save_download(..., brand_slug="reels-classics")` salva com slug. Sem parâmetro salva `NULL`.

---

### T23 — `get_downloads()` filtra por `brand_slug`

**Arquivo:** `app-curadoria/backend/database.py`
**Função:** `get_downloads` (~linhas 383-393)

**Adicionar:** parâmetro opcional `brand_slug=None`:
```python
def get_downloads(limit=100, brand_slug=None):
    query = "SELECT * FROM downloads"
    params = []
    if brand_slug:
        query += " WHERE brand_slug = ?"
        params.append(brand_slug)
    query += " ORDER BY downloaded_at DESC LIMIT ?"
    params.append(limit)
    # ...
```

**Critério de feito:** `get_downloads(brand_slug="reels-classics")` retorna só RC. `get_downloads()` retorna todos.

---

### T24 — Endpoint aceita query param `brand_slug`

**Arquivo:** `app-curadoria/backend/routes/curadoria.py`
**Localização:** GET `/api/downloads` (~linhas 721-723)

**Adicionar:**
```python
@router.get("/api/downloads")
def get_downloads_route(brand_slug: str = None):
    return get_downloads(brand_slug=brand_slug)
```

**Adicionar endpoint para marcas distintas:**
```python
@router.get("/api/downloads/brands")
def get_download_brands():
    """Retorna lista de brand_slugs distintos que têm downloads."""
    cur.execute("SELECT DISTINCT brand_slug FROM downloads WHERE brand_slug IS NOT NULL ORDER BY brand_slug")
    return [row[0] for row in cur.fetchall()]
```

**Critério de feito:** `GET /api/downloads?brand_slug=reels-classics` filtra. `GET /api/downloads/brands` retorna lista de slugs.

---

### T25 — Frontend: dropdown de filtro por marca

**Arquivo:** `app-portal/components/curadoria/downloads.tsx`
**Localização:** componente CuradoriaDownloads (~linhas 1-74)

**Adicionar:**
1. State: `const [brandFilter, setBrandFilter] = useState<string>("")`
2. Fetch de marcas: `GET /api/downloads/brands`
3. Dropdown de seleção acima da tabela
4. Passar `brand_slug` no fetch de downloads

```tsx
<select value={brandFilter} onChange={e => setBrandFilter(e.target.value)}>
  <option value="">Todas as marcas</option>
  {brands.map(b => <option key={b} value={b}>{b}</option>)}
</select>
```

**Critério de feito:** Dropdown funciona. Filtrar por marca mostra apenas downloads daquela marca.

---

### T26 — API client passa `brand_slug`

**Arquivo:** `app-portal/lib/api/curadoria.ts`
**Localização:** função downloads (~linhas 198-206)

**Modificar:** aceitar parâmetro `brandSlug` e passar como query param:
```typescript
export async function getDownloads(brandSlug?: string) {
  const params = brandSlug ? `?brand_slug=${brandSlug}` : ""
  const res = await fetch(`${CURADORIA_URL}/api/downloads${params}`)
  return res.json()
}

export async function getDownloadBrands(): Promise<string[]> {
  const res = await fetch(`${CURADORIA_URL}/api/downloads/brands`)
  return res.json()
}
```

**Critério de feito:** Funções TypeScript existem e são tipadas.

---

## BLOCO 7 — Prompts Gemini genéricos (baixa prioridade)

**Objetivo:** Remover referências hardcoded a "ópera" nos prompts do Gemini.

---

### T27 — Substituir "ópera" nos prompts de transcrição

**Arquivo:** `app-editor/backend/app/services/gemini.py`

**Substituições:**
| Linha aprox. | Atual | Novo |
|---|---|---|
| ~269-298 | `"transcritor profissional de ópera"` | `"transcritor profissional de música"` |
| ~396-419 | `"letra de ópera"` | `"letra da música"` |
| ~442-469 | `"música/ária"` | `"música"` |

**Nota:** Estes prompts SÓ executam quando `sem_lyrics=False`. Para RC instrumental nunca são chamados. A mudança é preventiva para futuras marcas vocais não-ópera.

**Critério de feito:** `grep -n "ópera\|opera" app-editor/backend/app/services/gemini.py` retorna 0 resultados nos prompts de transcrição.

---

### T28 — Verificar outros arquivos com "opera" hardcoded

**Buscar:**
```bash
grep -rn "opera\|ópera" app-editor/backend/ --include="*.py" | grep -v "best-of-opera" | grep -v "Best of Opera"
```

**Ação:** Substituir referências a "ópera" por termos genéricos em prompts. NÃO alterar nomes de marca, slugs ou referências a "Best of Opera" como nome próprio.

**Critério de feito:** Prompts do Gemini não assumem que todo conteúdo é ópera.

---

## Resumo de arquivos modificados

| # | Arquivo | Blocos | Tipo |
|---|---|---|---|
| 1 | `app-editor/backend/app/models/perfil.py` | B1 | Model |
| 2 | `app-editor/backend/app/main.py` | B1 | Migration |
| 3 | `app-editor/backend/app/routes/importar.py` | B1, B2 | Rota |
| 4 | `app-editor/backend/app/routes/admin_perfil.py` | B1, B5 | Rota + Validação |
| 5 | `app-portal/lib/api/editor.ts` | B1 | Tipo TS |
| 6 | `app-portal/app/(app)/admin/marcas/[id]/page.tsx` | B1, B3, B5 | UI Admin |
| 7 | `app-portal/app/(app)/admin/marcas/nova/page.tsx` | B1, B5 | UI Admin |
| 8 | `app-portal/components/editor/editing-queue.tsx` | B1 | UI Editor |
| 9 | `app-redator/backend/config.py` | B2 | Config |
| 10 | `app-redator/backend/models.py` | B2 | Model |
| 11 | `app-redator/backend/services/claude_service.py` | B3 | Serviço |
| 12 | `app-redator/backend/routers/generation.py` | B3 | Rota |
| 13 | `app-portal/components/redator/` (post approval) | B3 | UI Redator |
| 14 | `app-portal/components/editor/overview.tsx` | B4 | UI Editor |
| 15 | `app-portal/app/(app)/editor/edicao/[id]/letra/` | B4 | UI Editor |
| 16 | `app-portal/app/(app)/editor/edicao/[id]/alinhamento/` | B4 | UI Editor |
| 17 | `app-curadoria/backend/database.py` | B6 | DB |
| 18 | `app-curadoria/backend/routes/curadoria.py` | B6 | Rota |
| 19 | `app-portal/components/curadoria/downloads.tsx` | B6 | UI Curadoria |
| 20 | `app-portal/lib/api/curadoria.ts` | B6 | API Client |
| 21 | `app-editor/backend/app/services/gemini.py` | B7 | Serviço |

**Total: 21 arquivos, 28 tarefas, 7 blocos.**

---

## BLOCO 8 — Campos de tamanho por posição no admin (gancho/CTA)

**Objetivo:** Expor `gancho_fontsize` e `cta_fontsize` na UI do admin para todas as marcas, permitindo ajuste de tamanho por posição do overlay sem editar JSON bruto.

---

### T29 — Adicionar campos Gancho e CTA no componente StyleTrackConfig

**Arquivo:** `app-portal/components/admin/style-track-config.tsx`

**Mudanças:**
1. Nova prop `showHookSizes?: boolean` (default `false`) na interface `StyleTrackConfigProps`
2. Quando `showHookSizes=true`, renderizar dois campos numéricos adicionais após "Font Size":
   - **Gancho (px)** → edita `gancho_fontsize`
   - **CTA (px)** → edita `cta_fontsize`

**Critério de feito:** Campos aparecem apenas no track de overlay. Valores salvos no JSON do `overlay_style`.

---

### T30 — Ativar `showHookSizes` na edição e criação de marca

**Arquivos:**
- `app-portal/app/(app)/admin/marcas/[id]/page.tsx`
- `app-portal/app/(app)/admin/marcas/nova/page.tsx`

**Mudança:** Adicionar `showHookSizes` no `<StyleTrackConfig>` do Overlay (Header) em ambos os arquivos.

**Critério de feito:** Ao abrir a edição ou criação de qualquer marca, os campos Gancho e CTA aparecem no card do Overlay.

---

### T31 — Migração: atualizar tamanhos de fonte do perfil BO

**Arquivo:** `app-editor/backend/app/main.py`
**Localização:** seção de migrations, após backfill de lyrics/traducao 40px

**Nova migração idempotente:**
```python
# Backfill: aumentar fontes BO — gancho 60, corpo/cta 58, lyrics/tradução 48
UPDATE editor_perfis SET
    overlay_style = jsonb_set(jsonb_set(jsonb_set(
        overlay_style::jsonb, '{fontsize}', '58'),
        '{gancho_fontsize}', '60'),
        '{cta_fontsize}', '58')::json,
    lyrics_style = jsonb_set(lyrics_style::jsonb, '{fontsize}', '48')::json,
    traducao_style = jsonb_set(traducao_style::jsonb, '{fontsize}', '48')::json
WHERE sigla = 'BO' AND (overlay_style->>'gancho_fontsize')::int < 60
```

**Seed atualizado:** Novos perfis BO nascem com gancho=60, corpo=58, CTA=58, lyrics=48, tradução=48.

**Critério de feito:** Após deploy, `SELECT overlay_style, lyrics_style, traducao_style FROM editor_perfis WHERE sigla='BO'` mostra os novos valores.

---

## Resumo de arquivos modificados (atualizado)

| # | Arquivo | Blocos | Tipo |
|---|---|---|---|
| 1 | `app-editor/backend/app/models/perfil.py` | B1 | Model |
| 2 | `app-editor/backend/app/main.py` | B1, B8 | Migration |
| 3 | `app-editor/backend/app/routes/importar.py` | B1, B2 | Rota |
| 4 | `app-editor/backend/app/routes/admin_perfil.py` | B1, B5 | Rota + Validação |
| 5 | `app-portal/lib/api/editor.ts` | B1 | Tipo TS |
| 6 | `app-portal/app/(app)/admin/marcas/[id]/page.tsx` | B1, B3, B5, B8 | UI Admin |
| 7 | `app-portal/app/(app)/admin/marcas/nova/page.tsx` | B1, B5, B8 | UI Admin |
| 8 | `app-portal/components/editor/editing-queue.tsx` | B1 | UI Editor |
| 9 | `app-portal/components/admin/style-track-config.tsx` | B8 | UI Admin |
| 10 | `app-redator/backend/config.py` | B2 | Config |
| 11 | `app-redator/backend/models.py` | B2 | Model |
| 12 | `app-redator/backend/services/claude_service.py` | B3 | Serviço |
| 13 | `app-redator/backend/routers/generation.py` | B3 | Rota |
| 14 | `app-portal/components/redator/` (post approval) | B3 | UI Redator |
| 15 | `app-portal/components/editor/overview.tsx` | B4 | UI Editor |
| 16 | `app-portal/app/(app)/editor/edicao/[id]/letra/` | B4 | UI Editor |
| 17 | `app-portal/app/(app)/editor/edicao/[id]/alinhamento/` | B4 | UI Editor |
| 18 | `app-curadoria/backend/database.py` | B6 | DB |
| 19 | `app-curadoria/backend/routes/curadoria.py` | B6 | Rota |
| 20 | `app-portal/components/curadoria/downloads.tsx` | B6 | UI Curadoria |
| 21 | `app-portal/lib/api/curadoria.ts` | B6 | API Client |
| 22 | `app-editor/backend/app/services/gemini.py` | B7 | Serviço |

**Total: 22 arquivos, 31 tarefas, 8 blocos.**

---

## Checklist de verificação end-to-end

Após implementação de cada bloco, validar:

- [ ] **B1:** Criar marca com `sem_lyrics_default=true` → importar projeto → `sem_lyrics=true` automático
- [ ] **B1:** Criar marca com `sem_lyrics_default=false` → importar projeto → respeita parâmetro manual
- [ ] **B1:** Toggle no Admin funciona (criar e editar marca)
- [ ] **B2:** Importar sem `perfil_id` → HTTP 400 (não fallback para BO)
- [ ] **B2:** Criar projeto redator sem `brand_slug` → erro
- [ ] **B2:** `load_brand_config()` sem slug → ValueError
- [ ] **B3:** Gerar post para marca sem `custom_post_structure` → conteúdo gerado + warning amarelo
- [ ] **B3:** Gerar post para marca com `custom_post_structure` → sem warning
- [ ] **B4:** Overview de edição RC → etapas 4/5 ocultas
- [ ] **B4:** Overview de edição BO → todas as etapas visíveis
- [ ] **B5:** Criar marca sem `identity_prompt_redator` → bloqueado
- [ ] **B5:** Editar marca removendo campo obrigatório → bloqueado
- [ ] **B6:** Downloads filtrados por marca no frontend
- [ ] **B6:** Dropdown mostra apenas marcas com downloads
- [ ] **B7:** `grep "ópera" gemini.py` → 0 resultados em prompts
- [x] **B8:** Campos Gancho e CTA visíveis no admin (edição e criação de marca)
- [ ] **B8:** Alterar gancho/CTA pelo admin → valor persiste após salvar *(aguarda deploy)*
- [ ] **B8:** Perfil BO no banco com gancho=60, corpo/CTA=58, lyrics/tradução=48 após deploy *(aguarda deploy)*
