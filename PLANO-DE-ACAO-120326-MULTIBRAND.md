# PLANO-DE-ACAO-120326-MULTIBRAND
**Objetivo:** Corrigir bug crítico — sistema ignora perfil selecionado. O `selectedBrand` do frontend NUNCA é passado para os backends, fazendo tudo cair no default "best-of-opera".

**Escopo:** Backend (3 serviços) + Frontend (API layer do app-portal)

| # | Agente | Tarefa | Depende de | Status |
|---|--------|--------|------------|--------|
| 01 | CLAUDE CODE | Backend Editor: filtrar por `perfil_id` em todos os endpoints de edições | — | [x] |
| 02 | CLAUDE CODE | Backend Redator: filtrar por `brand_slug` em todos os endpoints de projetos | — | [x] |
| 03 | CLAUDE CODE | Backend Curadoria: aceitar `brand_slug` dinâmico por request (não startup) | — | [x] |
| 04 | ANTIGRAVITY | Frontend: injetar `perfil_id` / `brand_slug` em TODAS as chamadas de API | 01, 02, 03 | [x] |
| 05 | CLAUDE CODE | Deploy dos 3 backends + teste E2E multi-brand | 01, 02, 03, 04 | [ ] |

---

## DETALHES

### 01 — CLAUDE CODE: Backend Editor (`perfil_id`)
**Contexto:** O endpoint `GET /edicoes` retorna TODAS as edições de todas as marcas. O endpoint `POST /edicoes` não aceita `perfil_id`. Nenhum endpoint filtra por marca.

**Arquivos:**
- `app-editor/backend/app/routes/edicoes.py` — adicionar `perfil_id: Optional[int] = Query(None)` aos endpoints GET e injetar no POST/PATCH
- `app-editor/backend/app/schemas.py` — adicionar `perfil_id: Optional[int] = None` ao `EdicaoCreate`
- `app-editor/backend/app/routes/dashboard.py` (se existir) — filtrar dashboard por perfil_id
- `app-editor/backend/app/routes/reports.py` (se existir) — filtrar reports por perfil_id

**O que fazer:**
1. `GET /edicoes` → adicionar `perfil_id: Optional[int] = Query(None)`. Se fornecido, filtrar `.filter(Edicao.perfil_id == perfil_id)`. Se None, retornar tudo (retrocompatível).
2. `POST /edicoes` → aceitar `perfil_id` no body via schema. Setar no objeto criado.
3. `GET /dashboard/visao-geral` → aceitar `perfil_id` query param e filtrar contagens.
4. `GET /reports` e `POST /reports` → mesma lógica.
5. NÃO quebrar chamadas existentes sem perfil_id (default None = sem filtro).

**Entrega:** Endpoints do editor filtram por perfil_id quando fornecido. Sem perfil_id = comportamento antigo (retrocompatível).

---

### 02 — CLAUDE CODE: Backend Redator (`brand_slug`)
**Contexto:** O endpoint `GET /projects` retorna TODOS os projetos. O `POST /projects` não seta `brand_slug`. O campo existe no model Project mas nunca é populado corretamente.

**Arquivos:**
- `app-redator/backend/routers/projects.py` — filtrar listagem e setar brand_slug na criação
- `app-redator/backend/models.py` — verificar que `brand_slug` está no model
- `app-redator/backend/routers/generation.py` — verificar que generation já usa brand_slug (parece OK)

**O que fazer:**
1. `GET /projects` → adicionar `brand_slug: Optional[str] = Query(None)`. Se fornecido, filtrar `.filter(Project.brand_slug == brand_slug)`.
2. `POST /projects` → aceitar `brand_slug` no schema `ProjectCreate`. Se não fornecido, usar default "best-of-opera".
3. `GET /projects/r2-available` → aceitar `brand_slug` e filtrar projetos existentes por marca.
4. Verificar `generate_all` — já lê brand_slug do project, OK.

**Entrega:** Projetos do redator filtrados por brand_slug quando fornecido.

---

### 03 — CLAUDE CODE: Backend Curadoria (config dinâmica)
**Contexto:** `load_brand_config()` é chamada com `BRAND_SLUG` do env (hardcoded "best-of-opera"). A config é carregada 1x no startup em `BRAND_CONFIG = load_brand_config()`. Endpoints não aceitam brand_slug como parâmetro.

**Arquivos:**
- `app-curadoria/backend/config.py` — manter `BRAND_CONFIG` como cache mas permitir override por request
- `app-curadoria/backend/routes/curadoria.py` — adicionar `brand_slug: Optional[str] = Query(None)` a endpoints de busca/categorias/ranking

**O que fazer:**
1. Em `config.py`: adicionar cache dict `_brand_configs: dict[str, dict]` para múltiplas marcas. `load_brand_config(slug)` primeiro checa cache, depois faz request ao editor API.
2. Em `curadoria.py`: endpoints de search, category, ranking, categories → aceitar `brand_slug` query param. Se fornecido, chamar `load_brand_config(brand_slug)` em vez de usar `BRAND_CONFIG` global.
3. Endpoints de playlist/download → aceitar `brand_slug` para isolamento futuro (por enquanto apenas propagar config).
4. Manter retrocompatível: sem brand_slug = usa default do env.

**Entrega:** Curadoria carrega config da marca selecionada por request, não mais 1x no startup.

---

### 04 — ANTIGRAVITY: Frontend API Layer
**Contexto:** O `selectedBrand` está no contexto React (`useBrand()`) mas NENHUMA chamada de API passa `perfil_id` ou `brand_slug`. Isso é o elo quebrado da cadeia.

**Arquivos:**
- `app-portal/lib/api/editor.ts` — injetar `perfil_id` do `selectedBrand` em: `listarEdicoes`, `criarEdicao`, `dashboardVisaoGeral`, `listarReports`, `criarReport`
- `app-portal/lib/api/redator.ts` — injetar `brand_slug` do `selectedBrand` em: `listProjects`, `createProject`, `listR2Available`
- `app-portal/lib/api/curadoria.ts` — injetar `brand_slug` em: `search`, `searchCategory`, `ranking`, `categories`
- Componentes que chamam essas APIs — atualizar para passar o brand do contexto

**O que fazer:**
1. Cada função de API que lista/cria dados deve receber `perfil_id` (editor) ou `brand_slug` (redator/curadoria) como parâmetro.
2. Os componentes que chamam essas funções devem ler `selectedBrand` do `useBrand()` e passar o ID/slug.
3. Se `selectedBrand` é null → não filtrar (mostrar tudo = admin view).

**Entrega:** Todas as chamadas de API enviam o contexto da marca selecionada. Dados são isolados por marca no UI.

---

### 05 — CLAUDE CODE: Deploy + E2E
**Contexto:** Após backends e frontend atualizados, deploy nos 3 serviços Railway + validação.

**Entrega:**
- 3 backends deployed com novos parâmetros
- Frontend deployed passando perfil_id/brand_slug
- Teste: selecionar "Reels Classics" → ver apenas dados dessa marca
- Teste: selecionar "Best of Opera" → ver apenas dados dessa marca
