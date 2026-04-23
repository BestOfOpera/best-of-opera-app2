# Inventário Sprint 2B

**Data:** 2026-04-23
**Branch:** `claude/execucao-sprint-2b-20260423-1537`
**Base:** `main @ 8c7dbe9` (merge Sprint 2A execution)
**Plano aprovado:** `C:\Users\jmanc\.claude\plans\prompt-10b-purrfect-marble.md`

## Fontes autoritativas consultadas

| Fonte | Estado |
|---|---|
| `docs/rc_v3_migration/RELATORIO_INVESTIGACAO_PROFUNDA.md` (59,996 bytes) | ✓ Lido §4.2 + P3-Prob |
| `docs/rc_v3_migration/auditoria_profunda/RELATORIO_AUDITORIA_INVESTIGACAO.md` (38,585 bytes) | ✓ Lido pelo executor prévio — R-audit-01/02 confirmados |
| `docs/rc_v3_migration/execucao_sprint_1/RECONCILIACAO_PATHS.md` | ✓ Disponível |
| `docs/rc_v3_migration/execucao_sprint_1/RELATORIO_EXECUCAO_SPRINT_1.md` | ✓ Lido R1-b e contexto |
| `docs/rc_v3_migration/auditoria_sprint_1/RELATORIO_AUDITORIA_SPRINT_1.md` | ✓ Disponível |
| `docs/rc_v3_migration/execucao_sprint_2a/RELATORIO_EXECUCAO_SPRINT_2A.md` | ✓ Lido — confirmado line 148 "(decisão 4 operador)" precisa virar "(decisão 7)" |
| `docs/rc_v3_migration/auditoria_sprint_2a/RELATORIO_AUDITORIA_SPRINT_2A.md` | ⚠️ Ausente em main; lido via `git show origin/claude/audit-execucao-sprint-2a-20260423-1433:...` → `/tmp/audit_sprint_2a_reference.md` (743 linhas) |

## CRÍTICOS (2)

### R-audit-01 — `_sanitize_rc` remove marcadores estruturais

- **Path:linha atual:** `app-redator/backend/services/claude_service.py:840-876` (função); regex destrutivo nas linhas 855-858
- **Problema:** `re.sub(r'\b(GANCHO|CORPO|CLÍMAX|FECHAMENTO|CTA|CONSTRUÇÃO|DESENVOLVIMENTO)\b\s*', '', texto, flags=re.IGNORECASE)` remove silenciosamente marcadores que podem ser palavras editorialmente legítimas no texto
- **Classificação:** **RC** (função `_sanitize_rc` com suffix `_rc`)
- **Decisão:** ✅ **Incluir no Sprint 2B**
- **Patch previsto:** `_rc_logger.warning` antes do `re.sub`, prefix `[Sanitize RC Strip]`, contagem + matches encontrados. Preservar comportamento do `re.sub`.
- **Princípio editorial:** 1 (nunca cortar silenciosamente)

### R-audit-02 — ❌ **TRANSFERIDO para sessão paralela BO** (decisão PAUSA #1)

- **Path:linha:** `app-redator/backend/services/claude_service.py:636-652` (função `_sanitize_post`)
- **Problema original:** descarte silencioso de linhas por `_ENGAGEMENT_BAIT_PATTERNS` e `_MARKDOWN_SEPARATORS`
- **Decisão do operador:** **Recomendação A confirmada — transferir para sessão paralela BO**
- **Justificativa:** investigação da cadeia completa de callers (resumo abaixo) confirmou que a função serve exclusivamente o fluxo BO + outras marcas não-RC. Frontend tem dispatch explícito:
  ```tsx
  // approve-post.tsx:30-45 e new-project.tsx:322-337
  if (isRC) {  // brand_slug === "reels-classics"
    await redatorApi.generatePostRC(projectId)     // ← RC usa endpoint dedicado
  } else {
    await redatorApi.regeneratePost(...)           // ← BO usa este, chama generate_post → _sanitize_post
  }
  ```
- **Nomenclatura "sem sufixo" é legado** — código é de facto BO (em produção, não órfão)
- **Registrar no relatório Fase 4** como "Findings transferidos"
- **Débito documental adicional registrado:** renomear `generate_post()` → `generate_post_bo()` e `_sanitize_post()` → `_sanitize_bo_post()` quando sessão paralela BO reestruturar. Nome atual é ambíguo e pode induzir futuros executores a erros de classificação similar.

## ALTA migrada (1, reanálise em Fase 2)

### P3-Prob — 7 regras propostas sobre `_enforce_line_breaks_rc`

- **Path:linha atual:** `app-redator/backend/services/claude_service.py` função refatorada pós-R1-b (Sprint 1) com assinatura `-> tuple[str, str]`
- **Caller:** `_process_overlay_rc` com loop `MAX_CONTINUACOES=5` preservando `resto`
- **Classificação:** **RC** (função `_enforce_line_breaks_rc` com suffix `_rc`)
- **Decisão:** ✅ **Reanálise completa em Fase 2** (Caminho B obrigatório — sem APLICAR às cegas)
- **Default parcimônia (refinamento operador):** preferir JÁ RESOLVIDA/OBSOLETA salvo evidência concreta de valor sobre R1-b. Se total de commits aproximar-se ou exceder Sprint 2A (21 itens), reavaliar escopo.
- **Artefato Fase 2:** `REANALISE_P3_PROB.md` com 7 regras classificadas (i)/(ii)/(iii) + justificativa

## MÉDIAS RC/infra (6 confirmadas + 1 ambígua)

### Incluídas (6)

| ID | Path:linha atual | Patch previsto |
|---|---|---|
| R6 | `shared/storage_service.py:60-64` (função `sanitize_name`) | `logger.warning` antes do slice `s[:200]` quando `len(s) > 200`, com trecho do nome. Prefix tentativo `[Shared Name Truncate]`. |
| P1-UI1 | `app-portal/app/(app)/admin/marcas/nova/page.tsx:450-462` | Remover defaults hardcoded (50/25/40/60) OU exibir fonte visual. Abordagem mínima: não inicializar com valores hardcoded, deixar `undefined` para o form indicar "não configurado". Ou `title/aria-label` para visibilidade. A decidir no patch. |
| P1-UI2 | `app-portal/app/(app)/admin/marcas/[id]/page.tsx:618-630` | Mesmo patch de P1-UI1 (agrupar em 1 commit). |
| P4-008 | `app-redator/backend/prompts/rc_automation_prompt.py:60` (deslocou de :57) | `logger.warning` antes de `overlay_temas[:5]` quando `len(overlay_temas) > 5`, com contagem. Prefix tentativo `[RC Automation Overlay Temas]`. |
| C1 | `app-curadoria/backend/services/download.py:114-117` (função `sanitize_filename`) | `logger.warning` antes do slice `s[:200]` quando `len(s) > 200`. Prefix tentativo `[Curadoria Filename Truncate]`. |
| T9-spam | `app-editor/backend/app/main.py:77` (schema `editor_perfis`) | **Sem alterar schema** (proibição §7). Patch em app layer: validação de tamanho em endpoint que persiste `anti_spam_terms` (se existir) com `logger.warning` quando > 500 chars. Se não houver endpoint de edição atual, marcar como observação no relatório. A investigar no patch. |

### Transferida para sessão paralela BO (1)

| ID | Path:linha | Decisão PAUSA #1 |
|---|---|---|
| P2-PathA-2 | `app-redator/backend/services/claude_service.py:545` — `duracao = min(12.0, duracao)` dentro de `generate_overlay` | **Trilha B — Transferir.** Filtragem limpa: `generate_overlay` é BO semântico, zero callers RC. |

**Nota arqueológica (registrar no relatório Fase 4):**
> Descoberta arqueológica — P2-PathA-1 (Sprint 2A commit `f6b1da6`) foi aplicado em `generate_overlay` que é código BO-específico (zero callers RC). Classificação errada do ciclo anterior. Sessão paralela BO deve reavaliar durante reestruturação (manter, alterar ou remover o warning `[BO Clamp PathA]`).

## Débito documental (1)

### OB-1 — typo no relatório Sprint 2A

- **Path:linha atual:** `docs/rc_v3_migration/execucao_sprint_2a/RELATORIO_EXECUCAO_SPRINT_2A.md:148` — CONFIRMADO: contém "(decisão 4 operador)"
- **Correção:** trocar "(decisão 4 operador)" por "(decisão 7 operador)"
- **Justificativa:** Decisão 4 é P1-Doc ≡ D1; Decisão 7 é P1-Ed2 dead code (conforme §1.3.4 do PROMPT 10B). Typo confirmado pela tabela de decisões no próprio relatório (linhas 39-47 não têm decisão 7, o que indica que a tabela de decisões pode também precisar auditoria — **limitar OB-1 estritamente a linha 148** por escopo).
- **LOC:** 1 inserção / 1 remoção
- **Commit:** `docs(sprint-2b): OB-1 corrige referência decisão 4→7 em P1-Ed2`

## Resumo por categoria (FINAL pós-PAUSA #1)

| Categoria | Quantidade | IDs |
|---|---|---|
| CRÍTICOS | 1 | R-audit-01 |
| MÉDIAS RC/infra | 6 | R6, P1-UI1, P1-UI2, P4-008, C1, T9-spam |
| Documental | 1 | OB-1 |
| **Total Sprint 2B (confirmado)** | **7 itens** | — |
| P3-Prob | Reanálise Fase 2 com default parcimônia | 7 regras (commits aplicáveis a decidir) |

## Transferidos para sessão paralela BO (2)

| ID | Path | Justificativa |
|---|---|---|
| R-audit-02 | `claude_service.py:636-652` (função `_sanitize_post`) | Investigação confirmou: endpoint `/generate` e `/regenerate-post` são chamados apenas no branch `else` do `if (isRC)` no frontend. `_sanitize_post` serve exclusivamente fluxo BO + outras marcas. Nomenclatura "sem sufixo" é legado. |
| P2-PathA-2 | `claude_service.py:545` (dentro de `generate_overlay`) | `generate_overlay` tem zero callers RC. Trilha B (filtragem limpa) escolhida. |

## Débitos documentais registrados neste sprint

1. **Renomear funções ambíguas** quando sessão paralela BO reestruturar:
   - `generate_post()` → `generate_post_bo()`
   - `_sanitize_post()` → `_sanitize_bo_post()`
   - Nome atual induz erros de classificação (prompt 10B §1.3.1 afirmou "provavelmente é infra compartilhada" baseado apenas na falta de sufixo — incorreto)
2. **Descoberta arqueológica P2-PathA-1** (Sprint 2A commit `f6b1da6`): aplicado em `generate_overlay` BO-específico. Sessão paralela BO deve reavaliar durante reestruturação.
3. **Audit report Sprint 2A arquivado em branch** `claude/audit-execucao-sprint-2a-20260423-1433` (não mergeado em main). Débito documental menor do ciclo anterior.

## Deslocamentos de path:linha detectados (referência)

Pós-Sprint 2A, algumas linhas deslocaram. Valores atuais em main:

| ID | PROMPT 8 original | Main atual | Causa |
|---|---|---|---|
| R-audit-01 regex | ~783-786 (PROMPT 10B §1.3.1) | 855-858 | Sprint 1 + 2A adicionaram linhas acima |
| R-audit-02 descarte | ~578-585 (PROMPT 10B §1.3.1) | 645-646 | idem |
| P2-PathA-2 clamp | 483 (§4.2) | 545 | Sprint 2A P2-PathA-1 adicionou logger na função vizinha |
| P4-008 slice | 57 (§4.2) | 60 | Sprint 2A P4-001 adicionou logger acima |

Validação path:linha final fica para Fase 2 (`RECONCILIACAO_SPRINT_2B.md`).

## Próximos passos

1. **PAUSA OBRIGATÓRIA #1** — apresentar este inventário + filtragem ao operador
2. Operador decide:
   - **B2 (P2-PathA-2):** Trilha A (incluir) ou Trilha B (transferir)
   - **B3 (R-audit-02):** Recomendação A (transferir) ou B (incluir)
3. Após aprovação, seguir para Fase 2 — reconciliação path:linha + reanálise P3-Prob regra-por-regra
