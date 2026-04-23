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

### R-audit-02 — `_sanitize_post` descarta linhas por bait patterns

- **Path:linha atual:** `app-redator/backend/services/claude_service.py:636-652` (função); descarte nas linhas 645-646; `_ENGAGEMENT_BAIT_PATTERNS` em 623-630
- **Problema:** `if any(p.search(line) for p in _ENGAGEMENT_BAIT_PATTERNS): continue` descarta linhas silenciosamente. Também descarta linhas `_MARKDOWN_SEPARATORS`.
- **Classificação:** **BO/legacy semântico** — função sem suffix `_rc`/`_bo`; único caller é `generate_post()` (linha 669) que é invocada apenas em `routers/generation.py:114,299` (endpoints `/generate-all` e `/regenerate-post` genéricos). Zero callers RC. RC tem `generate_post_rc` → `_sanitize_rc` em paths separados.
- **Decisão:** ⚠️ **Operador decide — PAUSA #1**
  - Recomendação executor: **A — Transferir para sessão paralela BO** (evidência concreta mostra zero sobreposição RC)
  - Alternativa: **B — Incluir com patch conservador** (`logger.warning` neutro, prefix `[Sanitize Post Discard]`, 2 patches separados para `_MARKDOWN_SEPARATORS` vs `_ENGAGEMENT_BAIT_PATTERNS`)
- **Princípio editorial:** 1 (nunca cortar silenciosamente)
- **Ver:** `medias_filtradas.md` §B3 para análise completa

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

### Ambígua (1)

| ID | Path:linha atual | Decisão pendente |
|---|---|---|
| P2-PathA-2 | `app-redator/backend/services/claude_service.py:545` (deslocou de :483) — `duracao = min(12.0, duracao)` dentro de `generate_overlay` | ⚠️ Operador decide PAUSA #1 — Trilha A (incluir consistente com P2-PathA-1 de Sprint 2A) ou Trilha B (transferir, filtragem limpa). Ver `medias_filtradas.md` §B2. |

## Débito documental (1)

### OB-1 — typo no relatório Sprint 2A

- **Path:linha atual:** `docs/rc_v3_migration/execucao_sprint_2a/RELATORIO_EXECUCAO_SPRINT_2A.md:148` — CONFIRMADO: contém "(decisão 4 operador)"
- **Correção:** trocar "(decisão 4 operador)" por "(decisão 7 operador)"
- **Justificativa:** Decisão 4 é P1-Doc ≡ D1; Decisão 7 é P1-Ed2 dead code (conforme §1.3.4 do PROMPT 10B). Typo confirmado pela tabela de decisões no próprio relatório (linhas 39-47 não têm decisão 7, o que indica que a tabela de decisões pode também precisar auditoria — **limitar OB-1 estritamente a linha 148** por escopo).
- **LOC:** 1 inserção / 1 remoção
- **Commit:** `docs(sprint-2b): OB-1 corrige referência decisão 4→7 em P1-Ed2`

## Resumo por categoria

| Categoria | Quantidade confirmada | Com pendência operador |
|---|---|---|
| CRÍTICOS | 1 (R-audit-01) | 1 (R-audit-02) |
| ALTA migrada | 0 patches ainda (reanálise Fase 2) | 7 regras P3-Prob (Fase 2) |
| MÉDIAS RC/infra | 6 (R6, P1-UI1, P1-UI2, P4-008, C1, T9-spam) | 1 (P2-PathA-2) |
| Documental | 1 (OB-1) | 0 |
| **Total Sprint 2B** | **8** itens confirmados | **9** itens aguardando decisão operador (regras + R-audit-02 + P2-PathA-2) |

## Transferidos (preliminar, aguarda confirmação)

Se operador aprovar recomendações:

| ID | Destino |
|---|---|
| R-audit-02 (se Trilha A aprovada) | Sessão paralela BO |
| P2-PathA-2 (se Trilha B aprovada) | Sessão paralela BO |

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
