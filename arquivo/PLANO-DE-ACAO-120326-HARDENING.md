# PLANO-DE-ACAO-120326-HARDENING

**Objetivo:** Hardening do sistema após BLAST Fase 2 — corrigir fragilidades sistêmicas confirmadas no código (backend + frontend) que causam bugs recorrentes, crashes silenciosos e perda de dados.

---

| # | Agente | Tarefa | Depende de | Status |
|---|--------|--------|------------|--------|
| 01 | CLAUDE CODE | Validar GEMINI_API_KEY no startup + health endpoint redator | — | [x] |
| 02 | CLAUDE CODE | Remover BackgroundTasks da curadoria → asyncio.Queue worker | — | [x] |
| 03 | CLAUDE CODE | Substituir 48 print() por logger na curadoria | 02 | [x] |
| 04 | CLAUDE CODE | Criar shared/retry.py — decorator async com backoff exponencial | — | [x] |
| 05 | CLAUDE CODE | Refatorar retry do gemini.py com decorator shared | 04 | [x] |
| 06 | CLAUDE CODE | Adicionar retry a operações R2 (upload/download) | 04 | [x] |
| 07 | ANTIGRAVITY | Fix usePolling crash silencioso + requestFormData ApiError | — | [x] |
| 08 | ANTIGRAVITY | Error Boundary global + fix JSON parse silencioso marcas | — | [x] |
| 09 | ANTIGRAVITY | extractErrorMessage utility + recovery marcas + loading guards | 07 | [x] |
| 10 | CLAUDE CODE | Connection pooling curadoria (psycopg_pool) | 02 | [x] |
| 11 | CLAUDE CODE | Deploy + teste E2E em produção | 01-09 | [x] DEFERIDO → deploy consolidado no MULTIBRAND |

---

## DETALHES

### 01 — CLAUDE CODE: Validação startup + health redator
**Contexto:** `GEMINI_API_KEY` aceita string vazia sem erro — falha só no meio do pipeline com mensagem críptica. Redator é o único backend sem `/health`.
**Arquivos:**
- `app-editor/backend/app/services/gemini.py` — `_get_client()` adicionar `if not GEMINI_API_KEY: raise RuntimeError`
- `app-editor/backend/app/config.py` — warning log se vazio
- `app-redator/backend/routers/health.py` — criar (padrão do editor)
- `app-redator/backend/main.py` — registrar router
**Entrega:** Startup falha com mensagem clara se chave vazia. `/health` responde 200 no redator.

### 02 — CLAUDE CODE: Remover BackgroundTasks da curadoria
**Contexto:** `BackgroundTasks` é PROIBIDO (ERR-057, CLAUDE.md armadilha #4). Curadoria usa em 4 endpoints (linhas 287-316). Sem recovery no crash, sem heartbeat, fire-and-forget.
**Arquivos:**
- `app-curadoria/backend/routes/curadoria.py` — remover `BackgroundTasks` das 4 rotas, usar queue
- `app-curadoria/backend/worker.py` — criar (padrão simplificado do editor)
- `app-curadoria/backend/main.py` — iniciar worker no lifespan
**Entrega:** Background tasks da curadoria sobrevivem a erros transientes, status rastreável.

### 03 — CLAUDE CODE: print() → logger na curadoria
**Contexto:** 48 chamadas `print()` em 7 arquivos. Editor já usa `logger` consistentemente (202 chamadas, zero print).
**Arquivos:** `database.py`(8), `config.py`(3), `main.py`(2), `routes/curadoria.py`(23), `services/download.py`(8), `services/scoring.py`(1), `services/youtube.py`(3) — todos em `app-curadoria/backend/`
**Entrega:** Logging estruturado em toda a curadoria.

### 04 — CLAUDE CODE: Criar shared/retry.py
**Contexto:** Cada API externa (Gemini, R2, Cobalt) tem retry ad-hoc com `for range(2)` + `sleep(5)`. Sem backoff exponencial, sem jitter, sem padronização.
**Arquivos:**
- `shared/retry.py` — novo, decorator `@async_retry(max_attempts=3, backoff_base=2, exceptions=...)` com jitter
**Entrega:** Utility reutilizável para todas as chamadas externas. Zero dependências novas (sem tenacity).

### 05 — CLAUDE CODE: Refatorar retry gemini.py
**Contexto:** 4 funções com loops manuais `for tentativa in range(2)`. `buscar_letra()` não tem retry NEM timeout.
**Arquivos:**
- `app-editor/backend/app/services/gemini.py` — 4 funções refatoradas com `@async_retry`
**Entrega:** Retry consistente com backoff em todas as chamadas Gemini.

### 06 — CLAUDE CODE: Retry R2 storage
**Contexto:** `exists()` retorna `False` tanto para "arquivo não existe" quanto para "erro de rede". Upload/download sem retry. Perda de dados silenciosa.
**Arquivos:**
- `shared/storage_service.py` — retry em upload/download, distinguir 404 vs erro de rede em exists()
**Entrega:** Operações R2 sobrevivem a erros transientes de rede.

### 07 — ANTIGRAVITY: Polling + ApiError
**Contexto:** `usePolling` callback sem try/catch — se API falha, polling para permanentemente, UI congela com dados stale. `requestFormData()` throws `Error` genérico enquanto `request()` throws `ApiError` — catch blocks downstream não funcionam.
**Arquivos:**
- `app-portal/lib/hooks/use-polling.ts:39` — wrap em try/catch, continuar scheduling
- `app-portal/lib/api/base.ts:122` — throw `ApiError` em vez de `Error`
**Entrega:** Polling sobrevive a erros. Erros de API consistentes em todo o app.

### 08 — ANTIGRAVITY: Error Boundary + JSON parse
**Contexto:** Sem Error Boundary — runtime React error = tela branca sem recovery. JSON parse no admin marcas tem catch vazio (`// Ignore err on fly`).
**Arquivos:**
- `app-portal/app/error.tsx` — criar (Next.js App Router error boundary)
- `app-portal/app/(app)/admin/marcas/[id]/page.tsx:114` — toast.warning no catch
**Entrega:** Erros runtime mostram UI de recovery. JSON inválido mostra feedback.

### 09 — ANTIGRAVITY: Error utility + recovery marcas + loading guards
**Contexto:** Erros extraídos com 4 padrões diferentes (`err.message`, `err?.message`, `err?.detail`, `(err as any)?.message`). Marcas faz hard redirect em falha de load. Botões destrutivos sem disable durante async.
**Arquivos:**
- `app-portal/lib/utils.ts` — `extractErrorMessage(err: unknown): string`
- `app-portal/app/(app)/admin/marcas/[id]/page.tsx:96` — inline error state com retry
- `app-portal/app/dashboard/reports/page.tsx` — disable em bulk delete
**Entrega:** Mensagens de erro consistentes. Falha de load não expulsa usuário.

### 10 — CLAUDE CODE: Connection pooling curadoria
**Contexto:** 24 funções criam conexão psycopg3 nova cada. Sob carga, exaure conexões PostgreSQL.
**Arquivos:**
- `app-curadoria/backend/database.py` — `psycopg_pool.ConnectionPool`
- `app-curadoria/backend/requirements.txt` — adicionar `psycopg_pool`
**Entrega:** Reuso de conexões, sem exaustão sob carga.

### 11 — CLAUDE CODE: Deploy + E2E
**Contexto:** Todas as correções precisam chegar a produção e serem verificadas.
**Arquivos:** git push + Railway auto-deploy
**Entrega:** Zero novas issues no Sentry em 24h. Checklist E2E passando.

---

## PARALELISMO SEGURO

```
Sessão 1:
  ┌─ Claude Code: 01 (gemini + redator health)
  │  + 02 (curadoria BackgroundTasks)     [arquivos distintos]
  └─ Antigravity: 07 + 08                [frontend, sem overlap]

Sessão 2:
  ┌─ Claude Code: 03 (logger curadoria) → 04 (shared/retry)  [sequencial]
  └─ Antigravity: 09                     [frontend]

Sessão 3:
  Claude Code: 05 (gemini retry) + 06 (R2 retry)  [arquivos distintos, paralelo]

Sessão 4:
  Claude Code: 10 (connection pool)

Sessão 5:
  Claude Code: 11 (deploy + E2E)
```

## PROMPTS ANTIGRAVITY

Os prompts para as tarefas 07, 08 e 09 serão gerados pelo Claude Code com contexto real do codebase ao iniciar cada tarefa (conforme regra de Despacho de Prompts do CLAUDE.md global).
