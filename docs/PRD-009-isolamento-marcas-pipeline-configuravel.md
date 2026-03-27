# PRD-009 — Isolamento de Marcas e Pipeline Configurável

**Data:** 26–27/03/2026
**Sessão:** Diagnóstico completo de isolamento RC vs BO + correções de prompt + plano de pipeline configurável
**Status:** EM PLANEJAMENTO (escopo definido, aguardando SPEC)

---

## 1. Contexto e Histórico

A plataforma foi construída originalmente para uma única marca (Best of Opera). O suporte multi-brand foi adicionado posteriormente sobre essa base, criando fallbacks que assumem BO quando dados de marca estão ausentes. Com a adição do RC (Reels Classics), esses fallbacks causaram:

- Conteúdo RC gerado com estrutura/regras do BO
- Projetos RC aparecendo na listagem do BO
- Etapas de letra/transcrição visíveis para marca instrumental
- Importação RC usando perfil BO silenciosamente

Esta sessão diagnosticou todos os pontos de contaminação e definiu o plano de correção.

---

## 2. Tarefas já concluídas nesta sessão ✅

### 2.1 Prompts usam instruções da marca como regra principal
- Brand prompts (identity, tom, escopo) agora são injetados como `BRAND INSTRUCTIONS` no início do prompt, não como apêndice
- Overlay, post e YouTube usam a mesma lógica
- **Arquivos modificados:**
  - `app-redator/backend/prompts/post_prompt.py` — reescrito
  - `app-redator/backend/prompts/overlay_prompt.py` — reescrito
  - `app-redator/backend/prompts/youtube_prompt.py` — reescrito
- **Commit:** `b7ed23a`

### 2.2 RC forçado como sem_lyrics na importação
- `importar.py:213` — `eh_instrumental_final = eh_instrumental or (perfil.sigla == "RC")`
- Projetos RC não ficam mais presos em "letra"
- **Commit:** `63e7570`

### 2.3 Strip r2_prefix na criação de projeto
- `new-project.tsx` — remove `r2_prefix` da marca antes de parsear artist/work do caminho R2
- Corrige: artist não contém mais `ReelsClassics/projetos_/` no nome
- **Commit:** `7687d7b`

### 2.4 "Prontos para o Redator" como view padrão
- `project-list.tsx` — view padrão mudou de "Em andamento" para "Prontos para o Redator"
- Ordem do dropdown reordenada
- **Commit:** `fca2c11`

### 2.5 Lista R2 aguarda marca antes de buscar
- `project-list.tsx` — `if (!selectedBrand?.slug) return` antes de fetch
- Previne listar projetos de todas as marcas quando `selectedBrand` é null
- **Commit:** `849f4f4`

### 2.6 Modal de idioma fecha após importação
- `editing-queue.tsx` — `setModalIdioma(null)` adicionado no fluxo de sucesso
- **Commit:** `2c32c50`

### 2.7 Restaurar estrutura 5 seções para marcas sem custom_post_structure
- `post_prompt.py` — quando `custom_post_structure` vazio, injeta estrutura padrão de 5 seções
- Quando preenchido, usa a estrutura customizada e critical rules genéricas
- **Commit:** `12544e2`

---

## 3. Tarefas pendentes da sessão anterior (PRD-009 original) ⚠️→✅

### P1 — RC importação: backend 422 para idioma não detectado → ✅ RESOLVIDO
Corrigido em `importar.py:169-170`: quando `eh_instrumental=True` e `music_lang is None`, usa `proj.get("language") or "und"` em vez de lançar 422.

### P2 — Vídeos RC com tarja de letra falsa → ✅ OPERACIONAL
Não requer código. Re-render manual via "Limpar Edição" → reimportar com "Sem Lyrics".

### P3 — "Selecionar tudo" nas views do Redator → ✅ FUNCIONANDO
Validado após reestruturação.

---

## 4. Novo escopo — Isolamento completo de marcas

### 4.1 Diagnóstico realizado

Auditoria end-to-end de 8 etapas (dashboard → import → pipeline → conclusão) para ambas as marcas. Resultado:

| Componente | Status atual | Problema |
|---|---|---|
| Seleção de marca | ✅ Isolado | — |
| Lista projetos redator | ✅ Isolado | — |
| Lista R2 | ✅ Isolado | — |
| Lista edições editor | ✅ Isolado | — |
| Geração de conteúdo | ⚠️ Parcial | Estrutura padrão BO injetada quando `custom_post_structure` vazio |
| Import editor | ⚠️ Fallback | `perfil_id` ausente → assume BO |
| Config loading | ⚠️ Fallback | `slug` None → assume BO |
| Model defaults | ⚠️ Hardcoded | `brand_slug` default "best-of-opera" |
| Pipeline editor | ⚠️ Hardcoded | `sigla == "RC"` para decidir instrumental |
| UI editor (etapas) | ⚠️ Visual | Etapas de letra visíveis para RC |
| Curadoria downloads | ⚠️ Misturado | Tabela `downloads` sem coluna `brand_slug` |

### 4.2 Princípios definidos com o usuário

1. **Zero fallback entre marcas** — se um dado de marca está ausente, é ERRO, não "usa BO"
2. **Cada marca usa exclusivamente seus próprios dados** — prompts, estrutura, pipeline
3. **Configuração via frontend** — operador configura a marca pelo Admin, sem precisar de código
4. **Pipeline configurável** — campo booleano `sem_lyrics_default` no perfil define se a marca é instrumental
5. **Override por projeto** — operador pode alterar instrumental/vocal na importação de cada projeto
6. **Campos obrigatórios** — identity, tom de voz, escopo, estrutura do post são obrigatórios para criar/editar marca
7. **Warning no post** — se `custom_post_structure` vazio, gera com aviso (não bloqueia)

---

## 5. Blocos de implementação

### BLOCO 1 — Pipeline configurável por marca

**Objetivo:** Substituir `perfil.sigla == "RC"` por configuração do perfil.

**Arquivos a modificar:**

| Arquivo | Mudança |
|---|---|
| `app-editor/backend/app/models/perfil.py` | Adicionar campo `sem_lyrics_default = Column(Boolean, default=False)` |
| `app-editor/backend/app/main.py` | Migration: adicionar coluna `sem_lyrics_default` na tabela `editor_perfis`; seed RC com `True` |
| `app-editor/backend/app/routes/importar.py:213` | Trocar `perfil.sigla == "RC"` por `perfil.sem_lyrics_default` |
| `app-editor/backend/app/routes/admin_perfil.py` | Incluir `sem_lyrics_default` nos schemas de leitura/escrita |
| `app-portal/lib/api/editor.ts` | Adicionar `sem_lyrics_default: boolean` no tipo `Perfil` |
| `app-portal/app/(app)/admin/marcas/[id]/page.tsx` | Toggle "Marca instrumental (sem letra por padrão)" na aba de configuração |
| `app-portal/app/(app)/admin/marcas/nova/page.tsx` | Mesmo toggle na criação de nova marca |
| `app-portal/components/editor/editing-queue.tsx` | Usar `selectedBrand.sem_lyrics_default` como default do toggle instrumental (substituir hardcode `sigla === "RC"`) |

**Snippet de referência — importar.py:**
```python
# ANTES (hardcoded):
eh_instrumental_final = eh_instrumental or (perfil is not None and perfil.sigla == "RC")

# DEPOIS (configurável):
eh_instrumental_final = eh_instrumental or (perfil is not None and perfil.sem_lyrics_default)
```

**Snippet de referência — editing-queue.tsx (toggle instrumental):**
```typescript
// ANTES (hardcoded):
const isRC = selectedBrand?.sigla === "RC"

// DEPOIS (configurável):
const defaultInstrumental = selectedBrand?.sem_lyrics_default ?? false
```

---

### BLOCO 2 — Remover fallbacks BO

**Objetivo:** Erro explícito quando dados de marca estão ausentes, em vez de assumir BO.

**Arquivos a modificar:**

| Arquivo | Linha | Mudança |
|---|---|---|
| `app-editor/backend/app/routes/importar.py` | 155-162 | Remover fallback `Perfil.sigla == "BO"`. Se `perfil_id` ausente → `HTTPException(400, "perfil_id obrigatório")` |
| `app-redator/backend/config.py` | 27, 35 | Remover `BRAND_SLUG` default. `load_brand_config(slug=None)` → `HTTPException(400, "slug obrigatório")` |
| `app-redator/backend/models.py` | 44 | Remover `default="best-of-opera"` de `brand_slug`. Schema `ProjectCreate` já exige o campo |

**Snippet — importar.py:**
```python
# ANTES:
if perfil_id:
    perfil = db.get(Perfil, perfil_id)
else:
    perfil = db.query(Perfil).filter(Perfil.sigla == "BO").first()

# DEPOIS:
if not perfil_id:
    raise HTTPException(400, "perfil_id é obrigatório para importação")
perfil = db.get(Perfil, perfil_id)
if not perfil:
    raise HTTPException(404, f"Perfil #{perfil_id} não encontrado")
```

**Snippet — config.py:**
```python
# ANTES:
BRAND_SLUG = os.getenv("BRAND_SLUG", "best-of-opera")
def load_brand_config(slug=None):
    target_slug = slug or BRAND_SLUG

# DEPOIS:
def load_brand_config(slug: str) -> dict:
    if not slug:
        raise ValueError("slug da marca é obrigatório para carregar configuração")
    # ... resto do código
```

---

### BLOCO 3 — Post prompt com warning

**Objetivo:** Quando `custom_post_structure` vazio, gerar conteúdo mas retornar warning.

**Arquivos a modificar:**

| Arquivo | Mudança |
|---|---|
| `app-redator/backend/services/claude_service.py` | `generate_post()` retorna dict `{"text": ..., "warning": ...}` em vez de string quando `custom_post_structure` vazio |
| `app-redator/backend/routers/generation.py` | Propagar warning no response |
| `app-portal/components/redator/` | Exibir warning amarelo quando post tem aviso de estrutura |
| `app-portal/app/(app)/admin/marcas/[id]/page.tsx:496` | Trocar descrição de "Deixe vazio para usar o padrão" por "Campo obrigatório — define a formatação do post" |

**Snippet — claude_service.py:**
```python
def generate_post(project, custom_prompt=None, brand_config=None) -> dict:
    custom_post = (brand_config or {}).get("custom_post_structure", "")
    warning = None
    if not custom_post:
        warning = "Estrutura de post não configurada para esta marca. Usando estrutura padrão."
    # ... gerar ...
    return {"text": result, "warning": warning}
```

---

### BLOCO 4 — UI editor: esconder etapas para instrumental

**Objetivo:** Quando edição tem `sem_lyrics=True`, não mostrar etapas de letra/transcrição/alinhamento/tradução.

**Arquivos a modificar:**

| Arquivo | Mudança |
|---|---|
| `app-portal/components/editor/overview.tsx` | Condicionar exibição dos passos 2/3/4/6 a `!edicao.sem_lyrics` |
| `app-portal/app/(app)/editor/edicao/[id]/` | Páginas de letra, alinhamento: redirecionar para corte se `sem_lyrics=True` |

**Identificar:** verificar quais componentes mostram o stepper/progress com as 9 etapas e condicionar.

---

### BLOCO 5 — Campos obrigatórios na criação de marca

**Objetivo:** Não permitir criar/salvar marca sem os campos essenciais preenchidos.

**Arquivos a modificar:**

| Arquivo | Mudança |
|---|---|
| `app-portal/app/(app)/admin/marcas/nova/page.tsx` | Validação frontend: `identity_prompt_redator`, `tom_de_voz_redator`, `escopo_conteudo`, `custom_post_structure` obrigatórios |
| `app-portal/app/(app)/admin/marcas/[id]/page.tsx` | Mesma validação na edição |
| `app-editor/backend/app/routes/admin_perfil.py` | Validação backend: rejeitar POST/PUT se campos obrigatórios vazios |

**Campos obrigatórios:**
- `identity_prompt_redator` (Identidade da marca)
- `tom_de_voz_redator` (Tom de voz)
- `escopo_conteudo` (Escopo de conteúdo)
- `custom_post_structure` (Estrutura do post)

---

### BLOCO 6 — Curadoria: filtro de downloads por marca

**Objetivo:** Downloads filtráveis por marca. Filtro dinâmico (novas marcas aparecem automaticamente).

**Arquivos a modificar:**

| Arquivo | Mudança |
|---|---|
| `app-curadoria/backend/database.py` | Adicionar coluna `brand_slug` na tabela `downloads`; migration |
| `app-curadoria/backend/database.py` | `save_download()` aceita `brand_slug` |
| `app-curadoria/backend/database.py` | `get_downloads(brand_slug=None)` filtra quando passado |
| `app-curadoria/backend/routes/curadoria.py` | `/api/downloads` aceita `?brand_slug=` |
| `app-portal/components/curadoria/downloads.tsx` | Dropdown de filtro por marca (dinâmico, busca marcas distintas dos downloads) |
| `app-portal/lib/api/curadoria.ts` | Passar `brand_slug` nas chamadas de downloads |

**Filtro dinâmico — SQL:**
```sql
-- Buscar marcas com downloads (para popular o dropdown)
SELECT DISTINCT brand_slug FROM downloads ORDER BY brand_slug
```

---

### BLOCO 7 — Prompts de letra/transcrição (baixa prioridade)

**Objetivo:** Trocar referências hardcoded a "ópera" nos prompts do Gemini.

**Arquivos a modificar:**

| Arquivo | Linha | Mudança |
|---|---|---|
| `app-editor/backend/app/services/gemini.py` | 269-318 | `"transcritor profissional de ópera"` → `"transcritor profissional de música"` |
| `app-editor/backend/app/services/gemini.py` | 396 | `"letra de ópera"` → `"letra da música"` |
| `app-editor/backend/app/services/gemini.py` | 442-458 | `"música/ária"` → `"música"` |

**Nota:** Esses prompts só são executados quando `sem_lyrics=False` (projeto com vocal). Para RC instrumental, nunca são chamados. A mudança é para o caso excepcional de um projeto RC com vocal que não seja ópera (ex: coral sacro).

---

## 6. Ordem de execução recomendada

1. **BLOCO 1** — Pipeline configurável (mais impactante, resolve hardcode `sigla == "RC"`)
2. **BLOCO 2** — Remover fallbacks BO (segurança, previne contaminação silenciosa)
3. **BLOCO 5** — Campos obrigatórios (previne marcas incompletas)
4. **BLOCO 3** — Post prompt warning (UX, informativo)
5. **BLOCO 4** — UI editor etapas (UX, visual)
6. **BLOCO 6** — Curadoria downloads (melhoria, não urgente)
7. **BLOCO 7** — Prompts Gemini (baixa prioridade)

---

## 7. Decisões tomadas

| Decisão | Justificativa |
|---|---|
| Zero fallback entre marcas | RC e BO são estruturas diferentes — fallback causa bugs silenciosos |
| `sem_lyrics_default` como booleano no perfil | Simples, atende ao caso atual (instrumental vs vocal) |
| Override por projeto na importação | Flexibilidade para exceções (RC com peça vocal) |
| Campos de prompt obrigatórios | São o coração da geração de conteúdo |
| Warning em vez de erro para post sem estrutura | Não bloqueia o fluxo, mas avisa o operador |
| Quota YouTube compartilhada | Volume atual não justifica isolamento |
| Downloads com filtro dinâmico | Novas marcas aparecem sem intervenção no código |
| Prompts Gemini genéricos | "Música" em vez de "ópera" — funciona para qualquer marca |

---

## 8. Referências

- Content Bible RC v3.4: `RC_ContentBible_v3_4-_2_ (2).txt`
- Brand Definition RC: `ReelsClassics-BrandDefinition-v1.txt`
- SPEC-008 (concluído): `docs/SPEC-008-rc-workflow-plataforma.md`
- Diagnóstico de isolamento: sessão de 27/03/2026
