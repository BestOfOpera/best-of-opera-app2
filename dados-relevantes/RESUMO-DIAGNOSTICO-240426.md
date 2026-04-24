# Resumo Diagnóstico — 24/04/2026

**Contexto:** Sessão de implementação da Fase 0 do pipeline BO V2 — fundações (migrations, config, loaders, feature flag) para o pipeline novo sem ativá-lo em produção.
**PRD de referência:** nenhum PRD interno (planejado via `BO_PLANO_V2.md` externo do operador)
**SPEC ativo:** `docs/SPEC-011-fase0-fundacoes-bo-v2.md`

---

## 1. O que foi feito nesta sessão

### ✅ SPEC-011 — Fase 0 BO Pipeline V2 (CONCLUÍDA na branch, aguardando auditoria)

- **Branch:** `f0/bo-v2-fundacoes` (derivada de `main`, 9 commits)
- **app-redator (`_run_migrations` v18):** 14 colunas novas em `projects` (pipeline_version, hook_escolhido_json, 5 dim_\*_detectada, video_duration_seconds, operator_notes, 4 timestamps \*_approved_at, youtube_tags_list) + 3 em `translations` (verificacoes_json, is_stale, stale_reason)
- **app-editor:** perfil `best-of-opera-v2` seed em `editor_perfis` (overlay 76/38, interval NULL)
- **Novos módulos:** `backend/services/bo/antipadroes_loader.py` (7 idiomas, cache module-level), `backend/services/bo/bo_ctas.py` (CTAs com validação em import-time), `backend/utils/timestamp.py` (parse_timestamp_to_seconds), `backend/config/BO_ANTIPADROES.json`
- **Feature flag:** `PIPELINE_V2_ENABLED` (default `false`) + `USE_ANTHROPIC_WEB_SEARCH` (default `true`) em `backend/config.py`. Validação 28s em `update_project` dispara apenas para BO v2.
- **Docs:** `docs/SPEC-011-fase0-fundacoes-bo-v2.md`, `docs/fase0-env-vars.md`, entrada em `arquivo/MEMORIA-VIVA.md`

---

## 2. Decisões arquiteturais

### Opção B no app-editor — perfil separado em vez de UPDATE in-place

BO v1 permanece intocado em `best-of-opera` (overlay 70/35/interval=10). Novo perfil `best-of-opera-v2` copiado via `INSERT ... SELECT` com 3 overrides. Rollback trivial (`DELETE`), zero risco para renders V1 em andamento. Lookup pelo slug efetivo fica para Fase 1+.

### Ramo A para web_search — tool nativa Anthropic

`scripts/verify_web_search.py` rodou OK em 24/04/2026 (`ServerToolUsage(web_search_requests=1)`). `USE_ANTHROPIC_WEB_SEARCH=true` na Railway. Fallback Google CSE (Ramo B) fica documentado mas sem código — ativação só se a tool for descontinuada.

---

## 3. Estado do pipeline BO

**BO V2 — Fase 0 implementada em `f0/bo-v2-fundacoes`. Aguardando auditoria independente antes de merge em `main`. Pipeline V1 em produção intocado. V2 dormindo atrás de `PIPELINE_V2_ENABLED=false` até Fase 5.3.**

---

## 4. Estado dos ciclos

| Ciclo | Status |
|---|---|
| PRD-005 (diagnóstico plataforma) | ✅ CONCLUÍDO (23/03/2026) — ver `RESUMO-DIAGNOSTICO-230326.md` |
| SPEC-010 (CTA fixo, idiomas, hooks) | EM EXECUÇÃO (BLOCO 1 concluído; BLOCOS 2-5 pendentes) — ver `docs/SPEC-010-*.md` |
| SPEC-011 (Fase 0 BO V2) | CONCLUÍDO na branch — aguardando audit + merge |

---

## 5. Commits desta sessão

| Commit | O que fez |
|---|---|
| `49a3cb2` | Migration v18 projects + validação duração mínima 28s |
| `ee76d07` | Seed perfil best-of-opera-v2 no app-editor (Opção B) |
| `0986a67` | Migration translations (is_stale + verificacoes_json) |
| `e8810b0` | BO_ANTIPADROES.json + loader multilíngue (7 idiomas) |
| `603bd44` | bo_ctas.py (CTAs fixos validados em import-time) |
| `d8b1598` | scripts/verify_web_search.py (Ramo A confirmado) |
| `30933ff` | Feature flag PIPELINE_V2_ENABLED + USE_ANTHROPIC_WEB_SEARCH |
| `6ac72bc` | docs/fase0-env-vars.md (declaração env vars Railway) |
| _commit 9 (docs update)_ | SPEC-011 + entrada MEMORIA-VIVA + este snapshot |

---

## 6. Pendências pré-merge (BLOCKER)

- ⚠️ Auditoria independente em sessão CC nova antes de abrir PR
- ⚠️ Declarar `PIPELINE_V2_ENABLED=false` e `USE_ANTHROPIC_WEB_SEARCH=true` no dashboard Railway do `app-redator` antes do próximo deploy (instrução completa em `docs/fase0-env-vars.md`)
- ⚠️ Push da branch `f0/bo-v2-fundacoes` pendente de aprovação explícita do operador (regra `CLAUDE.md`)

**Próxima fase:** Fase 1 (prompts v1 dormentes + bo_research_service) só inicia após auditoria aprovada + merge da Fase 0.
