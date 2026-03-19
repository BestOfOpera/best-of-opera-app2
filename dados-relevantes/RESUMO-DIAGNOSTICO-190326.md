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

### 🟡 BUG-E — `cached_videos` sem coluna `brand_slug`
- **Arquivo:** `app-curadoria/backend/database.py`
- **Impacto atual:** Nenhum — marcas usam nomes de categorias diferentes. **Risco futuro:** conflito silencioso de cache se nova marca usar mesma categoria.
- **Fix:** Adicionar `brand_slug` + migration + filtrar queries por marca.

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

### 🔴 Relogin 401 (bug ativo, causa raiz identificada em 19/03/2026)
- **Sintoma:** Relogin falha com 401 a menos que o browser limpe localStorage.
- **Bate com ponto 1 da reunião** (validação de login/sessão).
- **Causa raiz 1 — Email case-sensitive no backend** (`app-editor/backend/app/routes/auth.py` linha 88):
  `Usuario.email == body.email` — PostgreSQL compara VARCHAR com case-sensitive. Se o usuário foi cadastrado com maiúscula e tenta logar com minúscula → 401. Fix: `func.lower(Usuario.email) == body.email.lower()`.
- **Causa raiz 2 — `loadUser()` apaga token em qualquer erro** (`app-portal/lib/auth-context.tsx` linha 56):
  O bloco `catch` remove `bo_auth_token` do localStorage em QUALQUER falha do `getMe()` (rede, timeout, 401). Token válido pode ser apagado por erro transitório, deslogando o usuário sem motivo.
- **Por que limpar o localStorage resolve:** quebra o ciclo onde token expirado → 401 → token removido → novo login → `loadUser()` falha por erro transitório → novo token também apagado.
- **Próximo passo:** criar PRD-002-relogin com essas causas raiz e gerar SPEC para correção.

### ✅ Brand config NULL no banco — verificado em 19/03/2026, campos preenchidos
- **BO:** `identity_prompt_redator`, `tom_de_voz_redator`, `escopo_conteudo` preenchidos. Hashtags: `#BestOfOpera, #Opera, #ClassicalMusic`.
- **RC:** todos os três blocos preenchidos com conteúdo detalhado de identidade, tom de voz e escopo.
- **✅ CONFIRMADO (19/03/2026):** post gerado para RC saiu com identidade correta — hashtags `#musicaclassica`, tom educativo/acessível, sem referência a BO. Funcionando end-to-end.

### 🟠 3 tarefas do HARDENING nunca implementadas
O plano `PLANO-DE-ACAO-120326-HARDENING.md` foi movido para `arquivo/` com 3 tarefas incompletas:
- `[ ]` Tarefa 05 — Refatorar retry de `gemini.py` para usar `shared/retry.py`
- `[ ]` Tarefa 06 — Retry no R2 storage
- `[ ]` Tarefa 10 — Connection pooling na curadoria

### 🟠 7 decisões editoriais da Reels Classics pendentes com o sócio
- **Sessão 12:** 7 pontos sobre conteúdo da RC (estrutura de post, CTA overlay, hooks com referência a ópera, hashtags, etc.) aguardando decisão do Bolivar.
- **Nunca respondidos nas sessões seguintes.**
- **Bate com pontos 4 e 9 da reunião.**

### 🟡 Falha em teste pré-existente
- `test_seed_best_of_opera_valores_corretos` falha: `fontsize` é `63` em `legendas.py` mas `40` no seed de `admin_perfil.py`. Nota original: "não afeta produção".

### ✅ MEMORIA-VIVA.md — substituída pelo sistema PRD/SPEC + RESUMO-DIAGNOSTICO
- O novo fluxo de desenvolvimento por sessões torna o MEMORIA-VIVA redundante.
- Arquivo pode ser movido para `arquivo/` quando conveniente.

### 🟡 Credenciais de produção expostas no MEMORIA-VIVA.md
- Senha do PostgreSQL (`bestofopera2024`) e Railway token em texto plano.
- Risco se repositório for público ou acessado sem controle.

### ⬜ BUG-F — Projeto exibe marca errada (pendente de investigação)
- **Sintoma:** Tela exibe dados de outra marca (ex.: Best of Opera aparecendo em projeto da Reels Classics).
- **Fonte:** ponto 9 da reunião — nunca investigado no código.
- **Causa raiz:** desconhecida. Investigar após resolução do relogin 401.

---

## 6. Tarefas da reunião × diagnóstico técnico

| # | Tarefa da reunião | Bugs/pendências relacionados | Status |
|---|---|---|---|
| 1 | Validação e-mail + login por marca | Relogin 401 — causa raiz identificada (email case-sensitive + loadUser apaga token). PRD-002 a criar. | 🔴 Pendente |
| 2 | Estabilidade editor (travamentos, render) | Tasks com padrão correto de BaseException e sessão fechada — estabilidade OK no código. Timeouts já corrigidos nas sessões 7/9. | 🟡 Monitorar |
| 3 | Download e fluxo de importação | YOUTUBE_COOKIES typo corrigido 13/03. Cascata de download funcional. | ✅ Resolvido |
| 4 | Prompts por marca (curadoria/redator) | ✅ BUG-C e BUG-D resolvidos em SPEC-001. ✅ Brand config preenchido (BO e RC). 7 decisões editoriais RC: verificar se ainda pendentes. | 🟢 Resolvido (verificar 7 decisões) |
| 5 | Tradução multilingue | Retry automático implementado. Language leak corrigido. | 🟡 Testar |
| 6 | Legendas / timing / limite de chars | Limite atual: overlay=70, lyrics=43. Reunião sugere 73. Edição manual de tempos: não existe ainda. | 🔴 Pendente |
| 7 | Ferramentas de correção mid-pipeline | Re-renderizar/re-traduzir por idioma individual já existem. UX de "onde voltar" ausente. | 🟡 Parcial |
| 8 | Reorganizar MEMORIA-VIVA | Arquivo com 27k tokens, viola regra do projeto | 🔴 Pendente |
| 9 | Bugs específicos detectados em testes | ✅ BUG-C/D resolvidos. ✅ Brand config preenchido. Relogin 401: causa raiz identificada, correção pendente (PRD-002). | 🟡 Parcial |

---

## 7. O que ainda não foi lido/verificado no código

Os itens abaixo foram identificados como pendência mas **não foram verificados diretamente no código-fonte** (só na documentação):

1. ✅ **`admin/reset-total`** — verificado em 19/03, não existe no código.
2. ✅ **`auth.py`** — verificado em 19/03: NÃO há validação case-insensitive. Causa raiz confirmada do relogin 401.
3. ✅ **Brand config no banco** — verificado em 19/03: campos preenchidos para BO e RC.
4. **Plano HARDENING tarefas 05/06/10** — verificar no código se `gemini.py` e `storage_service.py` têm retry implementado ou não

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
2. Corrigir relogin 401 (bug ativo, impacta todos os usuários)
3. ✅ BUG-C: `"opera live"` removido — SPEC-001
4. ✅ BUG-D: ANTI_SPAM dinâmico por marca — SPEC-001
5. Verificar brand config NULL no banco e preencher se necessário
6. Reorganizar MEMORIA-VIVA.md (reduzir tamanho)
7. Fechar 7 decisões editoriais da RC com Bolivar
8. Tarefas HARDENING 05/06/10 (gemini retry, R2 retry, connection pooling)
