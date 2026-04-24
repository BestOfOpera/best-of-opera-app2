# SPEC-011 — Fase 0 Fundações BO Pipeline V2

**Data:** 24/04/2026
**Baseado em:** nenhum PRD interno (pipeline V2 BO foi planejado fora do fluxo PRD padrão; referências externas: `BO_PLANO_V2.md`, `BO_ANTIPADROES.json`, `bo_ctas.py` — documentos de planejamento externos mantidos pelo operador, entregues via ZIP `sessao_F0_implementacao.zip` e não republicados neste repo)
**Status:** CONCLUÍDO — aguardando auditoria independente antes de merge em `main`

---

## Contexto

A Fase 0 instala no repositório e nos dois bancos (app-redator + app-editor) toda a infra-estrutura que o pipeline BO V2 vai consumir nas fases seguintes. Nada nesta fase ativa V2 em produção — o pipeline novo fica dormindo atrás da feature flag `PIPELINE_V2_ENABLED=false` até a Fase 5.3. Pipeline V1 (BO e RC) em produção permanece intocado.

Este SPEC documenta o que foi instalado, os 8 commits da branch `f0/bo-v2-fundacoes`, e as 2 decisões arquiteturais tomadas durante a execução (Opção B no perfil do app-editor; Ramo A para web_search).

---

## Ordem de execução

```
T0.1 — Migration v18: 14 colunas novas em projects + validação 28s
T0.2 — Seed perfil best-of-opera-v2 no app-editor (Opção B)
T0.3 — Migration translations: is_stale + verificacoes_json + stale_reason
T0.4 — BO_ANTIPADROES.json + antipadroes_loader (7 idiomas)
T0.5 — bo_ctas.py (CTAs fixos validados em import-time)
T0.6 — scripts/verify_web_search.py + decisão Ramo A (tool nativa Anthropic)
T0.7 — Feature flag PIPELINE_V2_ENABLED + USE_ANTHROPIC_WEB_SEARCH
T0.8 — docs/fase0-env-vars.md (declaração das env vars para Railway)
```

---

## T0.1 — Migration v18 em `projects` + validação de duração

**Commit:** `49a3cb2` — `feat(db): migration v18 — colunas BO pipeline v2 em projects + validação duração mínima 28s`

**Arquivos:** `app-redator/backend/main.py` (`_run_migrations`), `app-redator/backend/models.py` (`Project`), `app-redator/backend/schemas.py` (`ProjectOut`, `ProjectUpdate`), `app-redator/backend/routers/projects.py` (`update_project`), `app-redator/backend/utils/timestamp.py` (novo), `app-redator/backend/utils/__init__.py` (novo).

**14 colunas novas em `projects`** (todas `NULL` por default; guarda `if "col" not in cols`):

`pipeline_version VARCHAR(10) NOT NULL DEFAULT 'v1'`, `hook_escolhido_json JSON`, `dim_1_detectada VARCHAR(50)`, `dim_2_detectada VARCHAR(50)`, `dim_2_subtipo_detectada VARCHAR(50)`, `dim_3_pai_detectada VARCHAR(50)`, `dim_3_sub_detectada VARCHAR(50)`, `video_duration_seconds REAL`, `operator_notes TEXT`, `research_approved_at TIMESTAMP`, `overlay_approved_at TIMESTAMP`, `post_approved_at TIMESTAMP`, `youtube_tags_list JSON`, `youtube_approved_at TIMESTAMP`.

Índice `ix_projects_pipeline_version` + backfill explícito `UPDATE projects SET pipeline_version='v1' WHERE NULL`.

**Crítico:** `update_project` agora calcula `video_duration_seconds` automaticamente quando `cut_start` ou `cut_end` mudam. Se `brand_slug='best-of-opera'` AND `pipeline_version='v2'` AND `duration < 28s` → HTTP 400 (achado V-I-07). RC e BO v1 não disparam validação — apenas backfill.

---

## T0.2 — Perfil `best-of-opera-v2` no app-editor (Opção B)

**Commit:** `ee76d07` — `feat(editor): seed perfil best-of-opera-v2 (overlay 76/38, interval dinâmico)`

**Arquivo:** `app-editor/backend/app/main.py` (bloco após seed BO existente).

**Decisão arquitetural: Opção B — perfil separado.** Criar `INSERT ... SELECT` a partir de `best-of-opera`, sobrescrevendo apenas 3 campos:
- `overlay_max_chars`: 70 → **76**
- `overlay_max_chars_linha`: 35 → **38**
- `overlay_interval_secs`: 10 → **NULL** (V2 usa intervalos narrativos 5-7s dinâmicos)

Opção A (UPDATE in-place no perfil BO existente) foi descartada — afetaria BO v1 em produção. Opção B herda todos os estilos do BO e isola 100% o V2. Consistente com padrão multi-perfil do projeto (BO + RC já coexistem).

**Lookup do perfil V2 NÃO é implementado nesta fase.** Cada callsite de `load_brand_config` precisa derivar `effective_slug = f"{brand_slug}-v2" if pipeline_version == 'v2' else brand_slug` — essa mudança fica para a Fase 1+ quando os serviços V2 forem ativados. Fase 0 apenas instala o perfil dormente.

**Rollback:** `DELETE FROM editor_perfis WHERE slug = 'best-of-opera-v2'`.

---

## T0.3 — Migration `translations`: detecção de stale

**Commit:** `0986a67` — `feat(db): migration translations — is_stale + verificacoes_json + stale_reason`

**Arquivos:** `app-redator/backend/main.py` (`_run_migrations`), `app-redator/backend/models.py` (`Translation`), `app-redator/backend/schemas.py` (`TranslationOut`).

**3 colunas novas em `translations`** (achado V-I-34):
- `verificacoes_json JSON` — persiste bloco `verificacoes` retornado pelo prompt v1 de tradução
- `is_stale BOOLEAN DEFAULT FALSE NOT NULL` — marca tradução defasada quando operador edita PT pós-tradução
- `stale_reason VARCHAR(200)` — razão textual da marcação

Índice parcial `WHERE is_stale = TRUE` em Postgres (produção); fallback para índice full em SQLite (dev local, não suporta `WHERE` em `CREATE INDEX`).

---

## T0.4 — `BO_ANTIPADROES.json` + loader

**Commit:** `e8810b0` — `feat(bo): BO_ANTIPADROES.json + loader multilíngue`

**Arquivos (novos):** `app-redator/backend/config/BO_ANTIPADROES.json`, `app-redator/backend/services/bo/__init__.py`, `app-redator/backend/services/bo/antipadroes_loader.py`.

Lista versionada de anti-padrões BO em 7 idiomas (pt=45, en=43, es=21, de=21, fr, it, pl). Alinhada com BO Bible v2.0. Loader com cache module-level (single-load) expõe:
- `load_antipadroes()` → dict completo
- `get_banned_terms(language)` → lista de termos
- `format_banned_terms_for_prompt(language)` → string formatada para injeção em prompt

**Fonte única** consumida em runtime pelos prompts v2 — jamais duplicar inline.

---

## T0.5 — `bo_ctas.py` (CTAs fixos)

**Commit:** `603bd44` — `feat(bo): bo_ctas.py — fonte única de CTAs 7 idiomas`

**Arquivo (novo):** `app-redator/backend/services/bo/bo_ctas.py`.

Módulo canônico com `BO_CTAS_OVERLAY` (tupla `(linha_1, linha_2)` por idioma) consumido por overlay, translation e runtime. **Validação em import-time (`_validate_ctas`):** se qualquer CTA ultrapassar 38 caracteres por linha, o import falha — fail-fast em CI/startup em vez de produzir overlay inválido.

API pública: `get_cta_overlay(lang) → (l1, l2)`, `get_cta_overlay_formatted(lang) → "l1\nl2"`.

---

## T0.6 — `verify_web_search.py` + Ramo A

**Commit:** `d8b1598` — `feat(bo): script de verificação web_search Anthropic (Tarefa 0.6)`

**Arquivo (novo):** `scripts/verify_web_search.py`.

**Decisão arquitetural: Ramo A — tool nativa Anthropic.** Script rodado em 24/04/2026 com output:
```
OK — web_search disponivel
Server tool use: ServerToolUsage(web_search_requests=1, web_fetch_requests=0)
```

A tool `web_search_20250305` funciona na conta Anthropic do projeto → `USE_ANTHROPIC_WEB_SEARCH=true` na Railway. Fallback Google CSE (Ramo B) fica dormindo — código não criado, documentado em `docs/fase0-env-vars.md` para ativação futura se a tool for descontinuada.

---

## T0.7 — Feature flag `PIPELINE_V2_ENABLED`

**Commit:** `30933ff` — `feat(bo): feature flag PIPELINE_V2_ENABLED + USE_ANTHROPIC_WEB_SEARCH`

**Arquivos:** `app-redator/backend/config.py`, `app-redator/backend/routers/projects.py` (`create_project`).

Duas env vars declaradas com defaults seguros:
- `PIPELINE_V2_ENABLED` → default `"false"`. Só BO (`brand_slug='best-of-opera'`) vira `v2` quando a flag é `"true"`. RC e demais brands sempre `v1`.
- `USE_ANTHROPIC_WEB_SEARCH` → default `"true"` (Ramo A).

`create_project` agora deriva `pipeline_version` via `_resolve_pipeline_version(brand_slug)`. Smoke test local confirma: flag OFF → BO=v1/RC=v1; flag ON → BO=v2/RC=v1.

---

## T0.8 — Declaração de env vars para Railway

**Commit:** `6ac72bc` — `docs: declara env vars da Fase 0 BO V2 para Railway (Ramo A)`

**Arquivo (novo):** `docs/fase0-env-vars.md`.

Lista exata das 2 env vars que o operador deve declarar no dashboard Railway antes do próximo deploy da branch. Inclui aviso contra flipar `PIPELINE_V2_ENABLED=true` antes da Fase 5.3 e procedimento de posteridade para Ramo B (Google CSE) caso `web_search_20250305` seja descontinuada.

---

## Checklist geral

| # | Tarefa | Commit | Status |
|---|---|---|---|
| T0.1 | Migration v18 projects + validação 28s | `49a3cb2` | ✅ Concluído |
| T0.2 | Seed perfil best-of-opera-v2 (Opção B) | `ee76d07` | ✅ Concluído |
| T0.3 | Migration translations (is_stale) | `0986a67` | ✅ Concluído |
| T0.4 | BO_ANTIPADROES.json + loader | `e8810b0` | ✅ Concluído |
| T0.5 | bo_ctas.py (7 idiomas) | `603bd44` | ✅ Concluído |
| T0.6 | verify_web_search.py (Ramo A) | `d8b1598` | ✅ Concluído |
| T0.7 | Feature flag PIPELINE_V2_ENABLED | `30933ff` | ✅ Concluído |
| T0.8 | docs env vars Railway | `6ac72bc` | ✅ Concluído |

**Próximo passo:** auditoria independente em sessão CC nova antes de merge em `main`. Fase 1 (prompts e serviços v1 dormentes) só começa após aprovação do audit + declaração manual das env vars na Railway.
