# PLANO-DE-ACAO-120326-E2E — Fix dos 14 Testes E2E Falhando

**Objetivo:** Corrigir os 3 bugs identificados na validação E2E de produção (Mixed Content, Instabilidade de Sessão, Timeouts) para levar os 14 testes falhando a PASS.

**Prioridade:** CRÍTICA — Admin de Marcas, Editor Pipeline e Brand Selector bloqueados em prod.

---

## DIAGNÓSTICO

### Bug 1: Mixed Content (CRÍTICO) — Bloqueia Blocos 3, 7, 9, 10
**Causa raiz:** O `base.ts` já tem URLs HTTPS corretas, mas usa detecção em runtime via `window.location.hostname`. Duas falhas possíveis:
- O deploy mais recente (com fixes do Antigravity em 11/03) **pode não ter chegado ao Railway** — git status mostra arquivos modificados não comitados
- Durante SSR do Next.js, `window` é `undefined` → `isProduction()` retorna `false` → URLs localhost vazam

**Evidência:** MEMORIA-VIVA diz "URLs em base.ts já estão HTTPS" mas E2E em prod ainda vê `http://`

### Bug 2: Instabilidade de Sessão (ALTO) — Bloco 1
**Causa raiz:** Race conditions no auth-context.tsx:
- `loadUser()` dispara em cada navegação (`useEffect [pathname]`) sem cancelar a anterior
- `login()` chama `loadUser()` mas não aguarda — `router.push` executa antes do user carregar
- `logout()` remove token mas requests em voo já capturaram o header Authorization
- Nenhum handler de 401 no `base.ts` — erros de auth são silenciosos

### Bug 3: Timeouts/Loading Infinito (MÉDIO) — Blocos 5, 6, 7
**Causa raiz:** `request()` em `base.ts` usa `fetch()` sem timeout nem AbortController:
- Requests podem pendurar indefinidamente (Railway ephemeral = containers reiniciam)
- `BrandSelector` falha silenciosamente (console.error) → mostra "0 Marcas" sem retry
- `Promise.all` nas páginas do Editor — se 1 call trava, tudo trava

---

## PLANO DE EXECUÇÃO

| # | Agente | Tarefa | Depende de | Status |
|---|--------|--------|------------|--------|
| 01 | CLAUDE CODE | Verificar status do deploy no Railway + confirmar se código atual está em prod | — | [x] |
| 02 | CLAUDE CODE | Tornar URLs de API robustas contra SSR (NEXT_PUBLIC env vars) | — | [x] |
| 03 | CLAUDE CODE | Adicionar timeout global + AbortController em `base.ts` | — | [x] |
| 04 | CLAUDE CODE | Adicionar interceptor de 401 em `base.ts` (auto-logout) | — | [x] |
| 05 | CLAUDE CODE | Corrigir race conditions no `auth-context.tsx` | 04 | [x] |
| 06 | ANTIGRAVITY | Adicionar retry + estado de erro no `BrandSelector` | 03 | [x] |
| 07 | CLAUDE CODE | Push + deploy + revalidar E2E em produção | 01-05 | [x] DEFERIDO → deploy consolidado no MULTIBRAND |

---

## DETALHES

### 01 — CLAUDE CODE: Verificar deploy no Railway
**Contexto:** Git status mostra arquivos modificados não comitados (fixes do Antigravity em 11/03). O código local pode estar à frente do que está em prod.
**Ação:**
- Verificar último deploy no Railway (GraphQL API)
- Comparar commit deployado vs commit local
- Se divergiu: commitar + push após fixes
**Entrega:** Confirmação de que o código em prod está sincronizado ou identificação do delta

### 02 — CLAUDE CODE: URLs de API robustas contra SSR
**Contexto:** `isProduction()` em `base.ts:1-3` depende de `window` que é undefined durante SSR do Next.js.
**Arquivos:** `app-portal/lib/api/base.ts`
**Ação:**
- Substituir detecção por hostname por `NEXT_PUBLIC_API_EDITOR`, `NEXT_PUBLIC_API_CURADORIA`, `NEXT_PUBLIC_API_REDATOR`
- Manter fallback para localhost se env var não definida (dev)
- Configurar as env vars no Railway para os 3 backends (HTTPS)
**Entrega:** API URLs vêm de env vars em prod, fallback localhost em dev. Zero risco de Mixed Content.

### 03 — CLAUDE CODE: Timeout global + AbortController
**Contexto:** `request()` e `requestFormData()` em `base.ts` não têm timeout. Requests podem pendurar indefinidamente.
**Arquivos:** `app-portal/lib/api/base.ts`
**Ação:**
- Criar AbortController com timeout de 15s (padrão) em ambas as funções
- Aceitar timeout customizável via options
- Lançar erro específico (ex: `TimeoutError`) distinguível de erros de rede
**Entrega:** Nenhum request pendura mais de 15s. Componentes podem tratar timeout vs erro de rede.

### 04 — CLAUDE CODE: Interceptor de 401 em `base.ts`
**Contexto:** Quando o token expira ou é inválido, `base.ts` lança `ApiError(401)` genérico. Nenhum componente trata isso de forma centralizada.
**Arquivos:** `app-portal/lib/api/base.ts`
**Ação:**
- Após receber 401, limpar `bo_auth_token` do localStorage automaticamente
- Disparar evento custom (`window.dispatchEvent`) para o auth-context reagir
- Não redirecionar diretamente (responsabilidade do auth-context)
**Entrega:** 401 = token limpo + evento disparado. Auth-context escuta e redireciona para /login.

### 05 — CLAUDE CODE: Corrigir race conditions no `auth-context.tsx`
**Contexto:** `loadUser()` dispara a cada navegação, `login()` não aguarda, e logout não cancela requests em voo.
**Arquivos:** `app-portal/lib/auth-context.tsx`
**Ação:**
- Usar `useRef` com AbortController para cancelar `loadUser()` anterior ao navegar
- `login()`: tornar async, aguardar `loadUser()` antes de retornar
- `logout()`: abortar qualquer `loadUser()` em andamento antes de limpar estado
- Escutar evento de 401 do `base.ts` (da tarefa 04) para auto-logout
- Remover re-check em cada `pathname` (desnecessário — manter apenas no mount e login)
**Entrega:** Zero race conditions. Login aguarda user carregado. Logout cancela requests.

### 06 — ANTIGRAVITY: Retry + erro no BrandSelector
**Contexto:** `brand-selector.tsx` falha silenciosamente e mostra "0 Marcas" sem opção de retry.
**Arquivos:** `app-portal/components/brand-selector.tsx`
**Ação:**
- Adicionar estado `error` separado de `loading`
- Em caso de erro: mostrar botão "Tentar novamente" em vez de "0 Marcas"
- Retry automático após 5s na primeira falha
- Usar o timeout do `base.ts` (tarefa 03) para evitar loading infinito
**Entrega:** BrandSelector mostra feedback útil em caso de erro e permite retry.

### 07 — CLAUDE CODE: Push + deploy + revalidar
**Contexto:** Após todas as correções, fazer push e confirmar que os 14 testes passam.
**Ação:**
- Commitar todas as mudanças (tarefas 02-05)
- Push para Railway
- Configurar env vars NEXT_PUBLIC_API_* no Railway via GraphQL
- Re-executar checklist E2E nos blocos 1, 3, 7, 9, 10
**Entrega:** 14 testes verdes. Mixed Content eliminado. Auth estável. Timeouts tratados.
