# Inventário Sprint 2A

**Data de extração:** 2026-04-23T06:05Z
**Base:** `main @ ac6b94a` (merge Sprint 1 execution + auditoria independente APROVADO)
**Branch de execução:** `claude/execucao-sprint-2a-20260423-0304`
**Fonte:** tabela §4.2 de [RELATORIO_INVESTIGACAO_PROFUNDA.md](../RELATORIO_INVESTIGACAO_PROFUNDA.md) + auditoria [RELATORIO_AUDITORIA_SPRINT_1.md](../auditoria_sprint_1/RELATORIO_AUDITORIA_SPRINT_1.md) (débitos D1/D2/D3)

## Decisões do operador (PROMPT 10B-A aprovado)

1. **Ed-MIG1/MIG2 autorizado no Sprint 2A.** UPDATE em dados não viola §2.2 do prompt (schema = estrutura, não conteúdo). Confirmar em runtime que valores produção já batem com destino antes de remover migration.
2. **P3-Prob migra para Sprint 2B.** Toca `_enforce_line_breaks_rc` que Sprint 1 refatorou; 7 regras de balanceamento exigem análise que não cabe no Sprint 2A.
3. **P4-00x abordagem conservadora.** Adicionar `logger.warning` quando conteúdo excede limite; manter truncamento como defesa última (Princípio 4). Zero mudança de comportamento LLM.
4. **P1-Doc ≡ D1 = 1 commit único.** Inventário declara 22, executa **21 alvos distintos** (20 únicos + 1 sobreposição).

**BO-001 = patch mais arriscado** (muda prompt LLM). Validação pós-deploy na próxima publicação RC antes de declarar Sprint 2A estável.

**Leitura obrigatória antes do primeiro patch em editor:** `app-editor/CLAUDE.md` (agendado para Fase 2).

---

## CRÍTICAS remanescentes (esperado 7, obtido 7 ✓)

| ID | App | Path:linha declarado | Descrição | Remediação declarada |
|---|---|---|---|---|
| Ed-MIG1 | editor | [main.py:363-370](../../../app-editor/backend/app/main.py) | UPDATE perfil RC overlay_max_chars=66, overlay_max_chars_linha=33 WHERE sigla='RC' AND overlay_max_chars=70 (startup) | (a) remover migration ou versionar |
| Ed-MIG2 | editor | [main.py:737-740](../../../app-editor/backend/app/main.py) | UPDATE perfil RC overlay_max_chars=99 WHERE sigla='RC' AND overlay_max_chars != 99 (startup duplicada) | idem |
| P1-Ed3 | editor | [legendas.py:169](../../../app-editor/backend/app/services/legendas.py) | `_formatar_overlay` usa `_truncar_texto` | (a) remover + desabilitar callsite em render |
| P1-Ed4 | editor | [legendas.py:241-264](../../../app-editor/backend/app/services/legendas.py) | `_truncar_texto` função central | (a) remover função |
| P1-Ed5 | editor | [legendas.py:653](../../../app-editor/backend/app/services/legendas.py) | `_truncar_texto(texto, lyrics_max)` lyrics | (a) remover; lyrics já vêm pré-formatadas |
| P1-Ed6 | editor | [legendas.py:670](../../../app-editor/backend/app/services/legendas.py) | `_truncar_texto(texto_trad, traducao_max)` tradução | (a) remover |
| BO-001 | redator-BO | [overlay_prompt.py:45-77](../../../app-redator/backend/prompts/overlay_prompt.py) | `narrative[:max_chars] + "..."` narrativa fonte | (a) preservar e pedir LLM para reformular |

## ALTAS remanescentes (esperado 11 pós-decisão 2, obtido 11 ✓)

*Originalmente 12; P3-Prob migrou para Sprint 2B.*

| ID | App | Path:linha declarado | Descrição | Remediação |
|---|---|---|---|---|
| P1-Doc | redator-RC | [translate_service.py:533](../../../app-redator/backend/services/translate_service.py) | Docstring "≤33 chars/linha" desatualizado | (a) atualizar para 38 |
| P1-Ed1 | editor | [legendas.py:109](../../../app-editor/backend/app/services/legendas.py) | `quebrar_texto_overlay` executada em render | (a) remover função + callsites |
| P1-Ed2 | editor | [legendas.py:134](../../../app-editor/backend/app/services/legendas.py) | `_formatar_texto_legenda` | (a) idem |
| P2-PathA-1 | redator-BO | [claude_service.py:434-445](../../../app-redator/backend/services/claude_service.py) | `max(5.0, min(8.0, duracao))` Path A | (a) alinhar com Path B (4-6) ou deprecar |
| P4-001 | redator-RC | [rc_automation_prompt.py:64-66](../../../app-redator/backend/prompts/rc_automation_prompt.py) | `post_clean[:500] + "..."` | (b) regenerar ou reduzir — **conservador (dec. 3)**: log warning + manter truncamento |
| P4-005 | redator-RC/BO | [hook_prompt.py:42](../../../app-redator/backend/prompts/hook_prompt.py) | `json.dumps(...)[:3000]` | idem conservador |
| P4-006a | redator-RC | [generation.py:203](../../../app-redator/backend/routers/generation.py) | `json.dumps(...)[:2000]` | idem conservador |
| P4-006b | redator-RC | [generation.py:205](../../../app-redator/backend/routers/generation.py) | `research_data[:2000]` | idem conservador |
| P4-007a | redator-ambas | [translate_service.py:740](../../../app-redator/backend/services/translate_service.py) | `identity[:500]` | idem conservador |
| P4-007b | redator-ambas | [translate_service.py:743](../../../app-redator/backend/services/translate_service.py) | `tom[:300]` | idem conservador |
| P4-007c | redator-ambas | [translate_service.py:752](../../../app-redator/backend/services/translate_service.py) | `str(research_data)[:1500]` | idem conservador |

## Débitos documentais da auditoria Sprint 1 (3)

| ID | Alvo | Ação |
|---|---|---|
| D1 | [translate_service.py:533](../../../app-redator/backend/services/translate_service.py) (**mesmo alvo que P1-Doc**) | Atualizar docstring "≤33 chars/linha" → "≤38 chars/linha" |
| D2 | [RELATORIO_EXECUCAO_SPRINT_1.md](../execucao_sprint_1/RELATORIO_EXECUCAO_SPRINT_1.md) seção R5 (linha 148) | Adicionar seção "Teste manual descritivo" dedicada (cenário compressão temporal fora de 4-6s) |
| D3 | [RELATORIO_EXECUCAO_SPRINT_1.md:190](../execucao_sprint_1/RELATORIO_EXECUCAO_SPRINT_1.md) | Corrigir "21 matches" → "20 matches" + nota de decomposição (2 docstring + 6 checks + 6 warnings + 6 raises) |

## Total inventariado

- CRÍTICAS remanescentes: 7
- ALTAS remanescentes: 11 (12 tabela − 1 P3-Prob → Sprint 2B)
- Débitos documentais: 3

**Soma bruta: 21 itens**
**Alvos distintos: 20** (P1-Doc ≡ D1 = mesmo patch em mesma linha)
**Estimativa de commits atômicos: ~13** (com agrupamentos da §3.2 do plano)

## Validação pós-extração

- Esperado (prompt §1.2 original): 7 + 12 + 3 = 22 itens
- Esperado (pós-decisão 2 P3-Prob → 2B): 7 + 11 + 3 = 21 itens
- Obtido: 21 itens
- Variação vs expectativa ajustada: **0** (match exato)
- Divergências internas: **1 sobreposição** (P1-Doc ≡ D1, tratada como 1 commit conforme decisão 4)

## Reconciliação preliminar de path:linha (pré-validada durante Plan mode)

| ID | Path:linha declarado | Path:linha atual | Status |
|---|---|---|---|
| Ed-MIG1 | main.py:363-370 | 363-370 | INTACTO |
| Ed-MIG2 | main.py:737-740 | 737-740 | INTACTO |
| P1-Ed1 | legendas.py:109 | 109 | INTACTO |
| P1-Ed2 | legendas.py:134 | 134 | INTACTO |
| P1-Ed3 | legendas.py:169 | 169 | INTACTO |
| P1-Ed4 | legendas.py:241-264 | 241-264 | INTACTO |
| P1-Ed5 | legendas.py:653 | 653 | INTACTO |
| P1-Ed6 | legendas.py:670 | 670 | INTACTO |
| BO-001 | overlay_prompt.py:45-77 | 77 (pattern consolidado em linha única) | TRANSFORMADO (mesmo arquivo, linha única) |
| P1-Doc | translate_service.py:533 | 533 | INTACTO |
| P2-PathA-1 | claude_service.py:434-445 | 498 | DESLOCADO (+53 pós-Sprint 1) |
| P4-001 | rc_automation_prompt.py:64-66 | 66 (post_clean[:500] em linha única) | INTACTO |
| P4-005 | hook_prompt.py:42 | 42 | INTACTO |
| P4-006a | generation.py:203 | 200 | DESLOCADO (−3) |
| P4-006b | generation.py:205 | 202 | DESLOCADO (−3) |
| P4-007a | translate_service.py:740 | 746 | DESLOCADO (+6) |
| P4-007b | translate_service.py:743 | 749 | DESLOCADO (+6) |
| P4-007c | translate_service.py:752 | 758 | DESLOCADO (+6) |

**Reconciliação formal da Fase 2 precisa completar:**
- Confirmar caller-side de `_truncar_texto` / `quebrar_texto_overlay` / `_formatar_texto_legenda` (pipeline.py:1753, test_multi_brand.py:5) antes de "remover função"
- Ler `app-editor/CLAUDE.md` antes do primeiro patch em editor
- Confirmar que valores produção em `editor_perfis` já batem com destino (Ed-MIG idempotente)
- Validar BO-001 pattern exato e contexto de `max_chars` antes de alterar prompt
