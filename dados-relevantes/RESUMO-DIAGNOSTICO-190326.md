# Resumo Diagnóstico — 19/03/2026
**Contexto:** Sessão de onboarding do parceiro Filip. Análise completa do projeto antes de iniciar desenvolvimento.

---

## 1. O que foi feito nesta sessão

- Repositório clonado localmente em `c:\Users\filip\Dev\Airas\best-of-opera-app2`
- Leitura completa de todos os documentos: `CLAUDE.md`, `app-editor/CLAUDE.md`, `MEMORIA-VIVA.md` (inteiro), `HISTORICO-ERROS-CORRECOES.md` (inteiro), `DECISIONS.md`, `dados-relevantes/` (todos)
- Movido `PLANO-DE-ACAO-120326-MULTIBRAND.md` → `arquivo/` (plano 100% concluído)
- Movido `dados-relevantes/CONTEXTO-MULTIBRAND-PARA-CLAUDE.md` → `arquivo/` (snapshot desatualizado)
- `MEMORIA-VIVA.md` atualizado com sessão 24

---

## 2. Estado atual do sistema (produção)

Todos os 4 serviços Railway estão ativos e deployados:
- `portal` — SUCCESS
- `editor-backend` — ativo
- `curadoria-backend` — SUCCESS (deploy confirmado 13/03)
- `app` (redator) — ativo

Último deploy relevante: 13/03/2026 — correção de `YOU_TUBECOOKIES` (typo crítico que impedia todos os downloads via yt-dlp).

---

## 3. Bugs confirmados (lidos no código, verificados)

### ✅ BUG-C — `"opera live"` hardcoded na busca da curadoria — resolvido em SPEC-001
- **Arquivo:** `app-curadoria/backend/routes/curadoria.py` linha 94
- **Fix aplicado (19/03/2026):** `"opera live"` removido; `config` carregado antes de montar a query; `ANTI_SPAM` substituído por `config.get("anti_spam") or ANTI_SPAM`

### ✅ BUG-D — `ANTI_SPAM` global não respeita configuração da marca — resolvido em SPEC-001
- **Arquivo:** `app-curadoria/backend/routes/curadoria.py` linhas 40, 94, 133, 157
- **Fix aplicado (19/03/2026):** Todas as ocorrências usam `anti_spam = config.get("anti_spam") or ANTI_SPAM` com fallback seguro
- **✅ Verificado (19/03/2026):** RC tem `anti_spam_terms` preenchido. BO tem NULL → usa fallback global corretamente. Preenchimento do BO é opcional e pode ser feito pela UI de Admin quando conveniente.

### ✅ BUG-E — `cached_videos` sem coluna `brand_slug` — resolvido em SPEC-003 (19/03/2026)
- **Arquivo:** `app-curadoria/backend/database.py`
- **Fix aplicado (19/03/2026):** `brand_slug` adicionado ao schema + migration block no `init_db()` + `save_cached_videos()` e `get_cached_videos()` filtram por marca + callers em `curadoria.py` passam `brand_slug`.
- **⚠️ DEPLOY PENDENTE:** `curadoria-backend` + migration no banco antes do deploy.

---

## 4. Falsos alarmes (analisados e descartados)

| Bug original | Veredicto | Motivo |
|---|---|---|
| `except Exception` nas tasks | ❌ Não é bug | Tasks usam `except BaseException`. Os `except Exception` são catches internos intencionais. |
| Sessão BD aberta durante I/O | ❌ Não é bug | Todas as tasks fecham a sessão antes de I/O — comentado explicitamente no código. |
| `JWT_EXPIRY_HOURS` não usado | ❌ Não é bug | Usado em `middleware/auth.py:20`. |
| Deploy curadoria pendente | ❌ Resolvido | Deploy confirmado 13/03 às 21:12. |
| Import `quote` não usado | ❌ Não é bug | Usado na linha 484 de `curadoria.py`. |
| Caminho hardcoded redator `FRONTEND_DIST` | ❌ Não é bug ativo | Protegido por `if FRONTEND_DIST.exists()` — diretório não existe, bloco nunca executa. Código morto. |

---

## 5. Pendências técnicas herdadas (encontradas na MEMORIA-VIVA)

### ✅ Endpoint `admin/reset-total` — verificado em SPEC-001, não existe
- **Verificação (19/03/2026):** grep em todo `app-editor/` retornou zero matches — endpoint não existe no código atual. Referências apenas em documentação de arquivo. Nenhuma ação necessária.

### ✅ Relogin 401 — resolvido em SPEC-002 (19/03/2026)
- **Sintoma:** Relogin falha com 401 a menos que o browser limpe localStorage.
- **Bate com ponto 1 da reunião** (validação de login/sessão).
- **Causa raiz 1 — Email case-sensitive no backend** (`app-editor/backend/app/routes/auth.py` linha 88):
  `Usuario.email == body.email` — PostgreSQL compara VARCHAR com case-sensitive. Se o usuário foi cadastrado com maiúscula e tenta logar com minúscula → 401. Fix: `func.lower(Usuario.email) == body.email.lower()`.
- **Causa raiz 2 — `loadUser()` apaga token em qualquer erro** (`app-portal/lib/auth-context.tsx` linha 56):
  O bloco `catch` remove `bo_auth_token` do localStorage em QUALQUER falha do `getMe()` (rede, timeout, 401). Token válido pode ser apagado por erro transitório, deslogando o usuário sem motivo.
- **Por que limpar o localStorage resolve:** quebra o ciclo onde token expirado → 401 → token removido → novo login → `loadUser()` falha por erro transitório → novo token também apagado.
- **Fix aplicado (19/03/2026):** Task 01 — `func.lower()` em `auth.py`. Task 02 — catch seletivo em `auth-context.tsx`. Task 03 — banco verificado: 0/8 emails com uppercase.
- ⚠️ **DEPLOY PENDENTE — `editor-backend`:** ativar fix case-insensitive em `auth.py`
- ⚠️ **DEPLOY PENDENTE — `portal`:** ativar catch seletivo em `auth-context.tsx`

### ✅ Brand config NULL no banco — verificado em 19/03/2026, campos preenchidos
- **BO:** `identity_prompt_redator`, `tom_de_voz_redator`, `escopo_conteudo` preenchidos. Hashtags: `#BestOfOpera, #Opera, #ClassicalMusic`.
- **RC:** todos os três blocos preenchidos com conteúdo detalhado de identidade, tom de voz e escopo.
- **✅ CONFIRMADO (19/03/2026):** post gerado para RC saiu com identidade correta — hashtags `#musicaclassica`, tom educativo/acessível, sem referência a BO. Funcionando end-to-end.

### ✅ 3 tarefas do HARDENING — verificadas e concluídas (19/03/2026)
- `[x]` Tarefa 05 — `gemini.py` já usa `shared/retry.py` em todas as funções. Nenhuma ação necessária.
- `[x]` Tarefa 06 — Retry adicionado a `get_presigned_url`, `delete` e `list_files` em `shared/storage_service.py`. Upload/download já tinham retry.
- `[x]` Tarefa 10 — Connection pooling já implementado na curadoria (`min=2, max=10`). Nenhuma ação necessária.
- **⚠️ DEPLOY PENDENTE:** `editor-backend` (storage_service é shared — impacta apenas se deployado junto)

### 🟠 7 decisões editoriais da Reels Classics pendentes com o sócio
- **Sessão 12:** 7 pontos sobre conteúdo da RC (estrutura de post, CTA overlay, hooks com referência a ópera, hashtags, etc.) aguardando decisão do Bolivar.
- **Nunca respondidos nas sessões seguintes.**
- **Bate com pontos 4 e 9 da reunião.**

### ✅ BUG-G — Projetos Reels Classics gerados com prompts/identidade do Best of Opera — resolvido em SPEC-005b (22/03/2026)
- **Causa raiz:** múltiplos fallbacks hardcoded `or "best-of-opera"` em `generation.py` (4 endpoints), `config.py` (config hardcoded no except) e `schemas.py` (default no ProjectCreate). Frontend não bloqueava submit sem marca selecionada.
- **Fix aplicado (22/03/2026):**
  - `app-redator/backend/routers/generation.py`: 4 fallbacks substituídos por HTTPException 400
  - `app-redator/backend/config.py`: bloco hardcoded com dados do BO removido; except levanta HTTPException 503
  - `app-redator/backend/schemas.py`: `brand_slug: str = "best-of-opera"` → `brand_slug: str` (campo obrigatório no schema)
  - `app-portal/components/redator/new-project.tsx`: `canSubmit` exige `!!selectedBrand`; `handleSubmit` bloqueia com erro explícito se marca ausente
- **⚠️ BLOCKER pré-deploy:** Rodar `SELECT brand_slug, COUNT(*) FROM projects GROUP BY brand_slug` no banco — se existirem projetos com `brand_slug NULL`, não fazer NOT NULL migration sem populate primeiro.
- **⚠️ DEPLOY PENDENTE:** `app` (redator-backend) + `portal`.

### 🟡 Falha em teste pré-existente
- `test_seed_best_of_opera_valores_corretos` falha: `fontsize` é `63` em `legendas.py` mas `40` no seed de `admin_perfil.py`. Nota original: "não afeta produção".

### ✅ MEMORIA-VIVA.md — movida para `arquivo/` (19/03/2026)
- Arquivo movido para `arquivo/MEMORIA-VIVA.md`. Substituída pelo sistema PRD/SPEC + RESUMO-DIAGNOSTICO.

### 🟡 Credenciais de produção expostas no MEMORIA-VIVA.md
- Senha do PostgreSQL (`bestofopera2024`) e Railway token em texto plano.
- Risco se repositório for público ou acessado sem controle.

### ✅ BUG-F — Projeto exibe marca errada — resolvido em SPEC-003 (19/03/2026)
- **Arquivo:** `app-editor/backend/app/routes/edicoes.py` linhas 18–32
- **Causa raiz:** `perfil_id` era `Optional` no endpoint `GET /edicoes`. Quando o frontend não enviava o parâmetro, o backend retornava todas as edições de todas as marcas.
- **Fix aplicado (19/03/2026):** Guard `if perfil_id is None: return []` — sem `perfil_id`, retorna lista vazia.
- **⚠️ DEPLOY PENDENTE:** `editor-backend` no Railway.

---

## 6. Tarefas da reunião × diagnóstico técnico

| # | Tarefa da reunião | Bugs/pendências relacionados | Status |
|---|---|---|---|
| 1 | Validação e-mail + login por marca | ✅ Relogin 401 resolvido em SPEC-002: case-insensitive em auth.py + catch seletivo em auth-context.tsx. Pendente: deploy. | 🟡 Deploy pendente |
| 2 | Estabilidade editor (travamentos, render) | Tasks com padrão correto de BaseException e sessão fechada — estabilidade OK no código. Timeouts já corrigidos nas sessões 7/9. | 🟡 Monitorar |
| 3 | Download e fluxo de importação | YOUTUBE_COOKIES typo corrigido 13/03. Cascata de download funcional. | ✅ Resolvido |
| 4 | Prompts por marca (curadoria/redator) | ✅ BUG-C e BUG-D resolvidos em SPEC-001. ✅ Brand config preenchido (BO e RC). 7 decisões editoriais RC: verificar se ainda pendentes. | 🟢 Resolvido (verificar 7 decisões) |
| 5 | Tradução multilingue | Retry automático implementado. Language leak corrigido. | 🟡 Testar |
| 6 | Legendas / timing / limite de chars | Limite atual: overlay=70, lyrics=43. Reunião sugere 73. Edição manual de tempos: não existe ainda. | 🔴 Pendente |
| 7 | Ferramentas de correção mid-pipeline | Re-renderizar/re-traduzir por idioma individual já existem. UX de "onde voltar" ausente. | 🟡 Parcial |
| 8 | Reorganizar MEMORIA-VIVA | ✅ Movida para `arquivo/` (19/03/2026). | ✅ Resolvido |
| 9 | Bugs específicos detectados em testes | ✅ BUG-C/D resolvidos. ✅ BUG-F resolvido em SPEC-003. ✅ Brand config preenchido. ✅ Relogin 401 resolvido em SPEC-002. Pendente: deploy. | 🟡 Deploy pendente |

---

## 7. O que ainda não foi lido/verificado no código

Os itens abaixo foram identificados como pendência mas **não foram verificados diretamente no código-fonte** (só na documentação):

1. ✅ **`admin/reset-total`** — verificado em 19/03, não existe no código.
2. ✅ **`auth.py`** — verificado em 19/03: NÃO há validação case-insensitive. Causa raiz confirmada do relogin 401.
3. ✅ **Brand config no banco** — verificado em 19/03: campos preenchidos para BO e RC.
4. ✅ **Plano HARDENING tarefas 05/06/10** — verificado em 19/03: 05 e 10 já implementados; 06 completado em SPEC-003.

---

## 8. Estrutura do projeto (referência rápida)

```
app-editor/backend/     → Pipeline de vídeo (FastAPI + SQLAlchemy)
app-curadoria/backend/  → Curadoria YouTube (FastAPI + psycopg3 direto)
app-redator/backend/    → Geração de conteúdo Claude (FastAPI + SQLAlchemy)
app-portal/             → Frontend Next.js (único frontend)
shared/                 → storage_service.py + retry.py
dados-relevantes/       → Credenciais, configs ativas, este documento
arquivo/                → Planos concluídos e docs superados
```

**Regras de escopo obrigatórias:**
- Frontend = apenas `app-portal/`
- Backend = `app-*/backend/`
- Push = SOMENTE com aprovação explícita ("pode fazer o push")
- Commits = em português
- Tasks do worker = sempre `except BaseException`, imports dentro do try, sessão fechada antes de I/O

---

## 9. Prioridade sugerida para próximas sessões

1. ✅ `admin/reset-total` — verificado, não existe
2. ✅ Corrigir relogin 401 — resolvido em SPEC-002
3. ✅ BUG-C: `"opera live"` removido — SPEC-001
4. ✅ BUG-D: ANTI_SPAM dinâmico por marca — SPEC-001
5. ✅ Verificar brand config NULL no banco — verificado em 19/03, campos preenchidos para BO e RC
6. ✅ Reorganizar MEMORIA-VIVA.md — movida para `arquivo/` (19/03/2026)
7. Fechar 7 decisões editoriais da RC com Bolivar
8. ✅ Tarefas HARDENING 05/06/10 — verificadas e concluídas (19/03/2026)
