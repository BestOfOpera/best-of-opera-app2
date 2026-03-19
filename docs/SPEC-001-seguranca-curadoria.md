# SPEC-001 — Segurança e Curadoria Multi-brand

**status: CONCLUÍDO**
**Data:** 19/03/2026
**Baseado em:** `docs/PRD-001-seguranca-curadoria.md`

---

## Descobertas da fase de leitura

### #1 — `admin/reset-total` — JÁ RESOLVIDO
- Grep em todo `app-editor/` retornou zero matches
- O endpoint não existe no código atual
- Referências são apenas em documentação de arquivo (`arquivo/MEMORIAL-REVISAO-EDITOR.md`, `arquivo/CONTEXTO-CODIGO-FINAL.md`)
- **Ação de código: nenhuma**
- Ação necessária: fechar o TODO pendente na MEMORIA-VIVA (ver Tarefa A abaixo)

### #BUG-C — `"opera live"` hardcoded confirmado
- Arquivo: `app-curadoria/backend/routes/curadoria.py` linha 94
- Código atual: `full_query = f"{q} opera live {ANTI_SPAM}"`
- `config` ainda não está carregado nesse ponto — o endpoint carrega na linha 96. Fix exige reordenar: carregar config antes de montar a query.

### #BUG-D — `ANTI_SPAM` global ignorando config da marca
- `build_curadoria_config` (editor) já exporta `"anti_spam": perfil.anti_spam_terms or ""`
- `load_brand_config` (curadoria) já recebe esse campo como `config["anti_spam"]`
- O código da curadoria ignora `config["anti_spam"]` e usa diretamente `ANTI_SPAM` (global do módulo)
- `Perfil.anti_spam_terms` tem `default="-karaoke..."` — não será NULL para perfis criados via código
- Perfis antigos inseridos sem default podem ter NULL → `build_curadoria_config` retorna `""` → usar `config.get("anti_spam") or ANTI_SPAM` como fallback seguro
- BLOCKER do PRD: verificar no banco se `anti_spam_terms` é NULL para algum perfil (instrução na Tarefa C)
- Ocorrências a corrigir: linhas 40, 94, 133, 157 — **editar em sequência, não em paralelo**

---

## Tarefas

### Tarefa A — Fechar TODO do admin/reset-total
Endpoint verificado em 19/03/2026: não existe no código atual. Nenhuma alteração na MEMORIA-VIVA.
**Critério de feito:** esta tarefa está concluída — só precisava de verificação.

---

### Tarefa B — BUG-C: remover `opera live` hardcoded (curadoria.py linha 94)
**Arquivo:** `app-curadoria/backend/routes/curadoria.py`

**Código atual (endpoint `/api/search`, linhas 86–96):**
```python
@router.get("/api/search")
async def search(
    q: str = Query(...),
    max_results: int = Query(10, ge=1, le=50),
    hide_posted: bool = Query(True),
    brand_slug: str | None = Query(None, description="Slug da marca (default: env BRAND_SLUG)"),
):
    """Manual search with anti-spam filtering"""
    full_query = f"{q} opera live {ANTI_SPAM}"
    raw = await yt_search(full_query, max_results, YOUTUBE_API_KEY)
    return _process_v7(raw, q, hide_posted, config=load_brand_config(brand_slug))
```

**Código corrigido:**
```python
@router.get("/api/search")
async def search(
    q: str = Query(...),
    max_results: int = Query(10, ge=1, le=50),
    hide_posted: bool = Query(True),
    brand_slug: str | None = Query(None, description="Slug da marca (default: env BRAND_SLUG)"),
):
    """Manual search with anti-spam filtering"""
    config = load_brand_config(brand_slug)
    anti_spam = config.get("anti_spam") or ANTI_SPAM
    full_query = f"{q} {anti_spam}"
    raw = await yt_search(full_query, max_results, YOUTUBE_API_KEY)
    return _process_v7(raw, q, hide_posted, config=config)
```

**O que muda:**
1. `config` carregado antes de montar a query (antes era na linha seguinte, agora sobe)
2. `"opera live"` removido
3. `ANTI_SPAM` global substituído por `anti_spam` local (do perfil da marca)
4. `config` reutilizado na chamada `_process_v7` (elimina segundo `load_brand_config`)

**Critério de feito:** endpoint `/api/search` montando query sem `opera live`.

---

### Tarefa C — BUG-D: substituir ANTI_SPAM global nas demais ocorrências

**Arquivo:** `app-curadoria/backend/routes/curadoria.py`

#### C1 — `populate_initial_cache` (linha 40)

**Código atual:**
```python
full_query = f"{seed_query} {ANTI_SPAM}"
```
**Código corrigido** (config já existe na linha 35 desta função):
```python
anti_spam = config.get("anti_spam") or ANTI_SPAM
full_query = f"{seed_query} {anti_spam}"
```
Inserir a linha `anti_spam = ...` logo antes de `full_query`, dentro do `for` mas fora do `try`.

#### C2 — `search_category` (linha 133)

**Código atual:**
```python
full_query = f"{seed_query} {ANTI_SPAM}"
```
**Código corrigido** (config já existe na linha 107 desta função):
```python
anti_spam = config.get("anti_spam") or ANTI_SPAM
full_query = f"{seed_query} {anti_spam}"
```

#### C3 — `ranking` (linha 157)

**Código atual:**
```python
tasks = [yt_search(f"{q} {ANTI_SPAM}", 10, YOUTUBE_API_KEY) for _, q in all_q]
```
**Código corrigido** (config já existe na linha 154 desta função):
```python
anti_spam = config.get("anti_spam") or ANTI_SPAM
tasks = [yt_search(f"{q} {anti_spam}", 10, YOUTUBE_API_KEY) for _, q in all_q]
```

**Critério de feito:** nenhuma ocorrência de `ANTI_SPAM` usada diretamente em queries de busca — todas passando por `config.get("anti_spam") or ANTI_SPAM`.

**Verificação BLOCKER:** após as edições, rodar no banco Railway:
```sql
SELECT slug, anti_spam_terms FROM editor_perfis;
```
- Se algum perfil vier com `anti_spam_terms = NULL` → o fallback `or ANTI_SPAM` no código está correto e funciona, mas documentar como aviso no HISTORICO-ERROS-CORRECOES.md
- Se todos tiverem valor → BLOCKER não se concretizou, fechar sem pendência

---

## Ordem de execução

1. Tarefa A (MEMORIA-VIVA — sem risco, sem deploy)
2. Tarefa B (BUG-C — editar curadoria.py)
3. Tarefa C (BUG-D — continuar no mesmo arquivo, em sequência)
4. Verificação BLOCKER (banco Railway — instrução SQL acima)
5. Commit e deploy de `app-curadoria/`

---

## Arquivos modificados neste ciclo

| Arquivo | Ação |
|---|---|
| `MEMORIA-VIVA.md` | Fechar TODO do admin/reset-total |
| `app-curadoria/backend/routes/curadoria.py` | BUG-C (linha 94) + BUG-D (linhas 40, 133, 157) |

## Arquivos NÃO modificados

- `app-editor/` — nenhuma mudança necessária
- `app-portal/` — nenhuma referência a reset-total encontrada
- `app-curadoria/backend/config.py` — `ANTI_SPAM` global permanece como fallback válido

---

## Atualização pós-execução

Ao concluir:
1. Atualizar `status` deste arquivo: `PENDENTE` → `CONCLUÍDO`
2. Marcar no `RESUMO-DIAGNOSTICO-190326.md`: `✅ resolvido em SPEC-001` nos itens #1, BUG-C, BUG-D
3. Adicionar linha em `MEMORIA-VIVA.md`: data + referência a este SPEC
4. Atualizar `HISTORICO-ERROS-CORRECOES.md` com BUG-C e BUG-D
