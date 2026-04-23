# Relatório de Execução — Sprint 2B (PROMPT 10B)

**Data:** 2026-04-23
**Branch:** `claude/execucao-sprint-2b-20260423-1537`
**Base:** `main @ 8c7dbe9` (merge Sprint 2A execution)
**HEAD antes deste relatório:** `53bfe88`
**Total commits:** 9 (2 docs Fase 1/2 + 7 patches Fase 3) + 1 este relatório = **10 commits totais**

**Fontes autoritativas consultadas:**
- [RELATORIO_INVESTIGACAO_PROFUNDA.md §4.2 + §3.5](../RELATORIO_INVESTIGACAO_PROFUNDA.md)
- [RELATORIO_AUDITORIA_INVESTIGACAO.md](../auditoria_profunda/RELATORIO_AUDITORIA_INVESTIGACAO.md) (R-audit-01/02)
- [RELATORIO_EXECUCAO_SPRINT_1.md](../execucao_sprint_1/RELATORIO_EXECUCAO_SPRINT_1.md) (R1-b + MAX_CONTINUACOES base)
- [RELATORIO_AUDITORIA_SPRINT_1.md](../auditoria_sprint_1/RELATORIO_AUDITORIA_SPRINT_1.md)
- [RELATORIO_EXECUCAO_SPRINT_2A.md](../execucao_sprint_2a/RELATORIO_EXECUCAO_SPRINT_2A.md)
- Audit Sprint 2A: lido via `git show origin/claude/audit-execucao-sprint-2a-20260423-1433:...` (débito: arquivo não em main — ver seção Débitos)
- [INVENTARIO_SPRINT_2B.md](INVENTARIO_SPRINT_2B.md)
- [RECONCILIACAO_SPRINT_2B.md](RECONCILIACAO_SPRINT_2B.md)
- [REANALISE_P3_PROB.md](REANALISE_P3_PROB.md)

---

## Resumo executivo

Executados **1 CRÍTICO + 6 MÉDIAS + 1 débito documental = 7 itens patcheados**, **2 itens transferidos** para sessão paralela BO (R-audit-02 e P2-PathA-2), e **reanálise P3-Prob com default parcimônia** resultando em **zero commits de P3-Prob** (3 regras JÁ RESOLVIDAS pelo Sprint 1 R1-b + MAX_CONTINUACOES, 4 OBSOLETAS/DÉBITO por serem expansão arquitetural fora do escopo cirúrgico).

**Sprint 2B fecha a etapa "cortes/truncamentos RC + infra compartilhada"** iniciada em Sprint 1 e continuada em Sprint 2A. Sessão paralela BO continua trabalho independente em pipeline BO.

**AST parse OK** em todos os 5 arquivos Python tocados após cada commit. Grep de regressão confirmou que patches Sprint 1/2A preservados.

**Filtragem BO rigorosa:** `git diff main..HEAD` não contém hunks em nomes `_bo`, paths `bo/` ou variantes (`_bo_`). Verificação executada automaticamente.

**Zero infra nova** — nenhum teste automatizado criado, nenhum schema DB alterado, nenhuma constante global introduzida.

**Zero retoque em findings resolvidos** nos Sprints 1 e 2A (verificado via diff).

---

## Decisões do operador aplicadas

| # | Decisão | Aplicação |
|---|---|---|
| 1 (PAUSA #1 B1) | Audit Sprint 2A lido via `git show` sem materializar | Via pipe para `/tmp/audit_sprint_2a_reference.md` fora da working tree. Zero risco de commit acidental. |
| 2 (PAUSA #1 B2) | P2-PathA-2 → Trilha B (transferir para sessão paralela BO) | Registrado em INVENTARIO + débito arqueológico sobre P2-PathA-1 do Sprint 2A |
| 3 (PAUSA #1 B3) | R-audit-02 → Recomendação A (transferir para sessão paralela BO) após investigação extra | Evidência concreta: frontend faz dispatch `if (isRC)` → endpoints dedicados RC, `else` → `/generate` e `/regenerate-post` (BO/legacy ativo). Zero callers RC. |
| 4 (PAUSA #2) | Aprovação dos agrupamentos 1-6; T9-spam investigação inline em Fase 3 | Investigação identificou **Cenário α** (endpoint + UI inputs existem) → patch em `_validar_campos` com `logger.warning [T9 AntiSpam Overflow]` |
| 5 (PAUSA #2) | P3-Prob default parcimônia | 0 APLICAR, 3 JÁ RESOLVIDAS, 4 OBSOLETAS/DÉBITO |

---

## Filtragem BO aplicada

### Incluídos no Sprint 2B (7)

| ID | Classificação | Justificativa |
|---|---|---|
| OB-1 | Documental | Typo em relatório Sprint 2A — zero toque em código |
| R-audit-01 | RC-específico | Função `_sanitize_rc` com sufixo `_rc` |
| R6 | Shared infra | `sanitize_name` em `shared/storage_service.py` — usada por todos os pipelines |
| P1-UI1 | UI compartilhada | `app-portal` é frontend único para todas as marcas |
| P1-UI2 | UI compartilhada | idem |
| P4-008 | RC-específico | `rc_automation_prompt.py` — path contém `rc_` |
| C1 | Curadoria (não-BO) | `app-curadoria/` |
| T9-spam | Editor infra | Schema `editor_perfis` — usado por todas as marcas |

### Transferidos para sessão paralela BO (2)

| ID | Path | Justificativa |
|---|---|---|
| R-audit-02 | `claude_service.py:636-652` (função `_sanitize_post`) | Investigação extra Fase 1 confirmou: endpoints `/api/projects/{id}/generate` e `/regenerate-post` são chamados apenas no branch `else` do `if (isRC)` em `approve-post.tsx:42` e `new-project.tsx:328`. Zero callers RC. RC tem `generate_post_rc` + `_sanitize_rc` em paths dedicados. Nomenclatura "sem sufixo" é legado — código é de facto BO ativo em produção. |
| P2-PathA-2 | `claude_service.py:545` (dentro de `generate_overlay`) | `generate_overlay` tem zero callers RC (só chamada por `generation.py:118,155` genéricos). Trilha B (filtragem limpa) escolhida. |

---

## Reanálise P3-Prob

**Detalhes completos:** [REANALISE_P3_PROB.md](REANALISE_P3_PROB.md)

| Regra | Decisão | Justificativa |
|---|---|---|
| 1 — Nunca truncar conteúdo | **ii JÁ RESOLVIDA** | R1-b + MAX_CONTINUACOES=5 preserva via legendas extras |
| 2 — Balanceamento | **iii OBSOLETA/DÉBITO** | Qualidade estética, não cirurgia de truncamento |
| 3 — Palavra isolada | **iii OBSOLETA/DÉBITO** | idem |
| 4 — Unidades sintáticas | **iii OBSOLETA/DÉBITO** | idem |
| 5 — Split em legendas | **ii JÁ RESOLVIDA** | MAX_CONTINUACOES faz split automático |
| 6 — Alerta visual portal | **iii OBSOLETA/DÉBITO** | Requer UI + schema — expansão arquitetural proibida |
| 7 — Zero truncamento silencioso | **ii JÁ RESOLVIDA** | Sprint 1 R1-b/R2 transformou em retorno explícito + log |

**Contagens:** 0 APLICAR (i), 3 JÁ RESOLVIDAS (ii), 4 OBSOLETAS/DÉBITO (iii). **Zero commits P3-Prob em Fase 3.**

---

## Por finding

### OB-1 — Typo decisão 4→7 em P1-Ed2

- **Commit:** `e48fcef`
- **Path:** `docs/rc_v3_migration/execucao_sprint_2a/RELATORIO_EXECUCAO_SPRINT_2A.md:148`
- **Status reconciliação:** INTACTO
- **Patch:** `"(decisão 4 operador)"` → `"(decisão 7 operador)"`. Decisão 4 = P1-Doc ≡ D1, Decisão 7 = P1-Ed2 dead code.
- **LOC:** 1 inserção / 1 remoção
- **Princípio honrado:** consistência documental
- **Log adicionado:** N/A (documental)
- **Teste manual descritivo:** abrir RELATORIO_EXECUCAO_SPRINT_2A.md seção "P1-Ed2" — linha 148 agora referencia Decisão 7 corretamente.

### R-audit-01 — `_sanitize_rc` remove marcadores silenciosamente (CRÍTICO)

- **Commit:** `539a9b0`
- **Path:linha atual:** `app-redator/backend/services/claude_service.py:855-866` (função `_sanitize_rc`)
- **Status reconciliação:** DESLOCADO (+72 linhas pós-Sprint 1/2A)
- **Patch:** `re.findall` com mesmos flags do `re.sub` captura os marcadores antes da remoção. Se > 0, `_rc_logger.warning [Sanitize RC Strip]` loga quantidade + lista + trecho do texto. `re.sub` original preservado inalterado.
- **LOC:** 10 inserções
- **Princípio honrado:** 1 (nunca cortar silenciosamente)
- **Log adicionado:** `[Sanitize RC Strip]`
- **Logger:** `_rc_logger` (já disponível, linha 718)
- **Teste manual descritivo:** texto editorial RC contendo palavras como "gancho" ou "clímax" (legítimas no contexto, ex: "o gancho da peça" ou "clímax dramático") dispara warning com contagem + tokens + trecho inicial. Operador em Railway logs vê quando sanitização removeu conteúdo editorialmente legítimo.

### R6 — `sanitize_name` truncamento silencioso

- **Commit:** `679a433`
- **Path:linha atual:** `shared/storage_service.py:60-67` (função `sanitize_name`)
- **Status reconciliação:** INTACTO
- **Patch:** `if len(s) > 200` antes do `return s[:200]`, com `logger.warning [Shared Name Truncate]` incluindo contagem de chars e trecho. Slice preservado (truncamento conservador permanece).
- **LOC:** 5 inserções
- **Princípio honrado:** 1 (nunca cortar silenciosamente)
- **Log adicionado:** `[Shared Name Truncate]`
- **Logger:** `logger` módulo-level (linha 43, já disponível)
- **Teste manual descritivo:** projeto com nome de artista/obra combinado excedendo 200 chars após `project_base()` format dispara warning, permitindo auditoria de limites de chave R2.

### C1 — `sanitize_filename` truncamento silencioso (curadoria)

- **Commit:** `79e5907`
- **Path:linha atual:** `app-curadoria/backend/services/download.py:114-121` (função `sanitize_filename`)
- **Status reconciliação:** INTACTO
- **Patch:** mesmo padrão de R6, adaptado. `logger.warning [Curadoria Filename Truncate]`.
- **LOC:** 5 inserções
- **Princípio honrado:** 1
- **Log adicionado:** `[Curadoria Filename Truncate]`
- **Logger:** `logger` módulo-level (linha 5, já disponível)
- **Teste manual descritivo:** filename muito longo do YouTube (títulos com 250+ chars acontecem) dispara warning no worker de curadoria.
- **Observação:** duplicação deliberada com `shared/storage_service.py.sanitize_name` mantida. Consolidação = possível refactor futuro (fora de Sprint 2B para menor blast radius).

### P4-008 — `overlay_temas[:5]` slice silencioso (RC automation)

- **Commit:** `0367fec`
- **Path:linha atual:** `app-redator/backend/prompts/rc_automation_prompt.py:60-67` (função `build_rc_automation_prompt`)
- **Status reconciliação:** DESLOCADO (+3 linhas por Sprint 2A P4-001)
- **Patch:** `if len(overlay_temas) > 5` antes do `overlay_resumo = " | ".join(overlay_temas[:5])`. `logger.warning [RC Automation Overlay Temas]` inclui contagem + lista dos temas descartados.
- **LOC:** 6 inserções
- **Princípio honrado:** 1
- **Log adicionado:** `[RC Automation Overlay Temas]`
- **Logger:** `logger` módulo-level (linha 15, já disponível; Sprint 2A P4-001 adicionou)
- **Teste manual descritivo:** overlay RC com 6+ temas não-CTA (narrativas longas que viraram N legendas via MAX_CONTINUACOES=5) dispara warning no log do endpoint `/generate-automation-rc`.
- **Regressão check:** warning `[RC Automation Post Truncate]` de Sprint 2A P4-001 preservado (linha 73-76).

### P1-UI1 + P1-UI2 — Defaults UI hardcoded (agrupados)

- **Commit:** `80730b4`
- **Paths:linha atuais:**
  - `app-portal/app/(app)/admin/marcas/nova/page.tsx:450,454,458,462`
  - `app-portal/app/(app)/admin/marcas/[id]/page.tsx:618,622,626,630`
- **Status reconciliação:** INTACTO (ambos)
- **Patch:** atributo `title` condicional adicionado aos 4 `Input` de cada arquivo. Quando `formData.X` está vazio e cai para o default hardcoded (50/25/40/60), tooltip mostra "Padrão UI: X (não persistido no backend)". Quando há valor configurado, `title={undefined}` (UX limpa).
- **LOC:** 8 inserções (4 por arquivo) / 8 remoções (substituição inline)
- **Princípio honrado:** 4 (UX inconsistente → visibilidade)
- **Log adicionado:** N/A (frontend)
- **Teste manual descritivo:** abrir tela `/admin/marcas/nova` ou `/admin/marcas/[id]` (tela de edição). Deixar campo "Overlay Max" vazio ou não preenchido → hover sobre input mostra tooltip "Padrão UI: 50 (não persistido no backend)". Preencher com valor (ex: 70) → hover não mostra tooltip (campo tem valor real).
- **Decisão de escopo:** fix mínimo sem criar endpoint backend de defaults. Operador sabe quando o campo mostra um padrão hardcoded vs um valor persistido.

### T9-spam — `anti_spam_terms` VARCHAR(500) overflow

- **Commit:** `53bfe88`
- **Path:linha atual:** `app-editor/backend/app/routes/admin_perfil.py:208-221` (função `_validar_campos`)
- **Status reconciliação:** patch em caminho diferente — schema `app-editor/backend/app/main.py:77` INTACTO (proibição §7). Correção app-level em `_validar_campos`.
- **Cenário identificado:** **α** (endpoint FastAPI + 2 telas UI que aceitam input operador).
- **Investigação completa:**
  - Schema: `main.py:77` (CREATE TABLE) + `:922` (migration) + `models/perfil.py:56` (SQLAlchemy)
  - Endpoint: `admin_perfil.py:152` (Pydantic `Optional[str]`)
  - UI: `admin/marcas/nova/page.tsx:264` + `admin/marcas/[id]/page.tsx:384` (Input campos editáveis)
  - Service: `perfil_service.py:24` (leitura)
  - Testes: `test_perfil_unificado.py` (4 refs)
- **Patch:** `if len(anti_spam_terms) > 500` em `_validar_campos` com `logger.warning [T9 AntiSpam Overflow]`. Warning ocorre antes de DB tentar commit. Schema preservado (proibição §7).
- **LOC:** 8 inserções
- **Princípio honrado:** 4 (limite DB → alerta antes da tentativa)
- **Log adicionado:** `[T9 AntiSpam Overflow]`
- **Logger:** `logger` módulo-level (linha 22, já disponível)
- **Teste manual descritivo:** operador cola lista muito longa de anti-spam terms (>500 chars) no admin panel → warning dispara no log antes de DB rejeitar/truncar conforme configuração PostgreSQL.

---

## Agrupamentos em commits

| # | Commit SHA | Finding | Arquivo principal | LOC |
|---|---|---|---|---|
| Fase 1 | `edf1ec4` | inventário + filtragem BO + validação R-audit-02 | docs | 290 ins |
| Fase 2 | `25fe412` | reconciliação path:linha + reanálise P3-Prob | docs | 446 ins / 26 rem |
| 1 | `e48fcef` | OB-1 | RELATORIO_EXECUCAO_SPRINT_2A.md | 1 / 1 |
| 2 | `539a9b0` | R-audit-01 | claude_service.py | 10 ins |
| 3 | `679a433` | R6 | shared/storage_service.py | 5 ins |
| 4 | `79e5907` | C1 | app-curadoria/backend/services/download.py | 5 ins |
| 5 | `0367fec` | P4-008 | rc_automation_prompt.py | 6 ins |
| 6 | `80730b4` | P1-UI1 + P1-UI2 | 2 page.tsx | 8 ins / 8 rem (2 files) |
| 7 | `53bfe88` | T9-spam | admin_perfil.py | 8 ins |
| Fase 4 | (este) | relatório de execução | docs | N/A |

**Totais código (sem docs):**
- 7 commits fix
- 5 arquivos Python + 2 arquivos TSX tocados
- ~42 LOC de novo código (logs + validações)
- Zero quebra de compatibilidade (nenhuma assinatura de função mudou)

---

## Findings transferidos (registro obrigatório)

### R-audit-02

`app-redator/backend/services/claude_service.py:636-652` (função `_sanitize_post`)

Descarte silencioso de linhas por `_ENGAGEMENT_BAIT_PATTERNS` (5 regex) e `_MARKDOWN_SEPARATORS`. Transferido para sessão paralela BO após investigação da cadeia de callers confirmar que a função só serve fluxo BO + outras marcas (dispatch explícito no frontend em `if (isRC) { RC dedicado } else { genérico }`). A nomenclatura "sem sufixo" é legado — código é de facto BO ativo em produção (chamado por `generate_all` e `regenerate_post` em `routers/generation.py`, via `redatorApi.generate()` e `redatorApi.regeneratePost()` do frontend).

### P2-PathA-2

`app-redator/backend/services/claude_service.py:545` — `duracao = min(12.0, duracao)` dentro de `generate_overlay`

Clamp silencioso de duração de legenda na redistribuição do Path A editorial. Transferido em Trilha B (filtragem limpa) porque `generate_overlay` tem zero callers RC (só invocada pelos endpoints genéricos `generation.py:118,155` que atendem não-RC).

**Descoberta arqueológica (registrar):** P2-PathA-1 (Sprint 2A commit `f6b1da6`) foi aplicado em `generate_overlay` que é código BO-específico (zero callers RC). Classificação errada do ciclo anterior. Sessão paralela BO deve reavaliar durante reestruturação (manter, alterar ou remover o warning `[BO Clamp PathA]` existente).

---

## Débitos identificados

### Débito 1: Audit report Sprint 2A arquivado (documental menor)

`docs/rc_v3_migration/auditoria_sprint_2a/RELATORIO_AUDITORIA_SPRINT_2A.md` existe **apenas** na branch `origin/claude/audit-execucao-sprint-2a-20260423-1433`, não em main. Decisão do operador no PAUSA #1: não bloqueia Sprint 2B. Lido via `git show` sem materializar na working tree (para evitar commit acidental).

**Ação sugerida futura:** se houver valor em ter o audit no histórico principal, merge da branch em main via PR; caso contrário, branch permanece arquivada.

### Débito 2: Renomeação de funções ambíguas

- `generate_post()` → `generate_post_bo()`
- `_sanitize_post()` → `_sanitize_bo_post()`

Nome atual é ambíguo e pode induzir outros executores a erros de classificação similares ao que aconteceu em PROMPT 10B §1.3.1 ("provavelmente é infra compartilhada RC+BO" — incorreto). Renomear durante reestruturação BO evita recorrência.

### Débito 3: Descoberta arqueológica P2-PathA-1

Ver "Findings transferidos" acima. Sessão paralela BO deve reavaliar o warning `[BO Clamp PathA]` adicionado no Sprint 2A em função semânticamente BO.

### Débito 4: P3-Prob regras iii (melhorias de qualidade editorial)

Quatro regras classificadas como **OBSOLETA/DÉBITO** são melhorias legítimas para sprint futuro dedicado a qualidade editorial (não cirurgia de truncamento):

1. **Regra 2 — Balanceamento** (~30 LOC pós-processador)
2. **Regra 3 — Palavra isolada** (~20 LOC heurística)
3. **Regra 4 — Stop-words sintáticas** (~15 LOC lista)
4. **Regra 6 — Alerta visual portal** (feature cross-stack: Python + Next.js + possivelmente schema)

Ordem sugerida pelo §3.5 original: 3 → 2 → 4 → 6.

### Débito 5: T9-spam comportamento DB

Warning foi adicionado antes da tentativa de persistência, mas não há garantia de como PostgreSQL lida com VARCHAR(500) overflow (rejeita com erro ou trunca silenciosamente depende da configuração). Validação explícita (raise HTTPException 422) poderia ser adicionada se operador quiser rejeitar em vez de deixar DB decidir. Registrado como débito para avaliação futura.

### Débito 6: Consolidação sanitize_name/sanitize_filename

Duas funções quase idênticas em locations separados (`shared/storage_service.py` e `app-curadoria/backend/services/download.py`). Sprint 2B manteve duplicação deliberadamente (menor blast radius). Consolidação em shared/ possível refactor futuro.

### Débito 7: Sem suite de testes automatizados

Sprint 2B não criou testes (proibição §2.2). Validação baseada em `python -c "import ast; ast.parse(...)"` + grep de regressão + teste manual descritivo no Railway logs. Débito técnico conhecido; suite automatizada é sprint dedicado.

---

## Contagem acumulada e guardrail

| Sprint | Commits | Observação |
|---|---|---|
| Sprint 1 | 7 findings patcheados + docs | APROVADO, em produção |
| Sprint 2A | 21 itens patcheados + docs | APROVADO, em produção |
| **Sprint 2B** | **9 commits (2 docs + 7 fix) + este relatório = 10 totais** | **abaixo do guardrail 21 commits do Sprint 2A ✓** |

**Total LOC Sprint 2B:** 753 inserções / 9 remoções distribuídas em:
- 5 arquivos Python (código): ~42 LOC novos
- 2 arquivos TSX (código UI): 16 LOC totais (8 ins + 8 rem)
- 1 arquivo documento existente (OB-1): 1 LOC (substituição)
- 5 arquivos docs novos (Sprint 2B artifacts): ~700 LOC

**Validações globais:**
- ✓ AST parse OK em todos os 5 arquivos Python tocados
- ✓ Grep positivo: todos os 6 novos log prefixes aparecem ≥1 vez
- ✓ Grep negativo: patches Sprint 1/2A preservados (sem regressão em `_rc_logger.warning` pré-existentes, em `[RC LineBreak]`, `[RC Automation Post Truncate]`, etc)
- ✓ Filtragem BO: `git diff main..HEAD` sem hunks `_bo`, `bo/`, `_bo_`
- ✓ Zero modificação em arquivos Sprint 1/2A (exceto OB-1 típico)
- ✓ Zero schema DB alterado
- ✓ Zero assinatura de função mudou
- ✓ Contagem total Sprint 2B (10 commits) bem abaixo do guardrail Sprint 2A (21 commits)

---

## Novos log prefixes introduzidos (para observabilidade Railway)

| Prefix | Finding | Localização |
|---|---|---|
| `[Sanitize RC Strip]` | R-audit-01 | `claude_service.py:_sanitize_rc` |
| `[Shared Name Truncate]` | R6 | `shared/storage_service.py:sanitize_name` |
| `[Curadoria Filename Truncate]` | C1 | `download.py:sanitize_filename` (app-curadoria) |
| `[RC Automation Overlay Temas]` | P4-008 | `rc_automation_prompt.py:build_rc_automation_prompt` |
| `[T9 AntiSpam Overflow]` | T9-spam | `admin_perfil.py:_validar_campos` |

**Total prefixes ativos em produção após Sprint 2B merged:**
- Sprint 1: 3 prefixes
- Sprint 2A: 9 prefixes
- **Sprint 2B: 5 prefixes novos**
- **Total acumulado: 17 prefixes** auditáveis no Railway

(P1-UI1+UI2 não introduzem log prefix — patch é UI-only com `title` attribute.)

---

## Próximos passos

1. **Auditoria Sprint 2B** via PROMPT 10B_AUDIT (branch `claude/execucao-sprint-2b-20260423-1537` aguarda em origin após push autorizado)
2. Se **APROVADO**:
   - Merge em main
   - Deploy Railway (automático)
   - 48h estabilização
   - **Etapa cortes/truncamentos RC + infra compartilhada FECHADA** ✓
3. Se **REPROVADO**: operador decide refinamento ou rollback
4. **Sessão paralela BO continua independente** trabalhando no pipeline BO (migração editor_perfis 70/35→76/38, refactor `_enforce_line_breaks_bo`, R-audit-02, P2-PathA-2, descoberta arqueológica P2-PathA-1, e renomeação `generate_post` → `generate_post_bo`)

---

## Regra absoluta (§5 PROMPT 10B) — checklist final

- [x] Cada finding tem path:linha validado via grep/sed + verificação de contexto semântico
- [x] Cada patch tem grep de regressão passando (0 regressões em Sprint 1/2A)
- [x] Cada truncamento silencioso novo tem log com prefix padronizado (`[Sanitize RC Strip]`, `[Shared Name Truncate]`, etc)
- [x] Cada princípio editorial invocado é verificável (Princípio 1 para R-audit-01/R6/C1/P4-008; Princípio 4 para P1-UI1+UI2/T9-spam)
- [x] Reanálise P3-Prob teve justificativa clara para (ii) e (iii) em `REANALISE_P3_PROB.md`
- [x] Aplicação de regras P3-Prob seguiu default parcimônia (zero APLICAR)
- [x] Filtragem BO rigorosa (zero hunks `_bo`, `bo/`)
- [x] Audit Sprint 2A lido via `git show` (nunca materializado)
- [x] Contagem total (10 commits) bem abaixo do guardrail (21)
- [x] Débitos técnicos novos registrados (7 débitos documentados)
- [x] Zero código tocado fora do Sprint 2B

Sprint 2B pronto para auditoria independente.
