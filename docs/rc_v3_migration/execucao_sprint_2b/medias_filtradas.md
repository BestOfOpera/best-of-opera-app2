# Filtragem BO das MÉDIAS — Sprint 2B

**Data:** 2026-04-23
**Base:** main @ 8c7dbe9 (pós-merge Sprint 2A)
**Branch:** `claude/execucao-sprint-2b-20260423-1537`

## Critérios aplicados (§1.3.3 + refinamento operador)

- Path contém `/bo/` OU função termina `_bo` → **BO-específico → transferir**
- Nome de função termina `_rc` OU path/diretório só é invocado por fluxo RC → **RC → incluir**
- Função compartilhada sem sufixo, usada por RC e BO → **infra → incluir**
- Função compartilhada sem sufixo, usada APENAS por BO/legacy → **BO semântico → transferir** (ou incluir com precedente documentado)
- UI do `app-portal/` (single frontend para todas marcas) → **infra compartilhada → incluir**
- `app-curadoria/` (não-BO por natureza) → **incluir**

## Tabela de classificação

| ID | Target (path:linha validada) | Suffix/Dir | Uso real (evidência) | Classificação | Include 2B? |
|---|---|---|---|---|---|
| R6 | `shared/storage_service.py:60-64` (função `sanitize_name`) | shared/ (sem suffix) | usada por `project_base()` (shared), que é consumida por todos pipelines (curadoria, editor, redator-BO, redator-RC) | **Shared infra** | ✅ **Incluir** |
| P1-UI1 | `app-portal/app/(app)/admin/marcas/nova/page.tsx:450-462` | app-portal (single frontend) | UI de criação de qualquer marca (RC + BO + outras) | **UI compartilhada** | ✅ **Incluir** |
| P1-UI2 | `app-portal/app/(app)/admin/marcas/[id]/page.tsx:618-630` | app-portal (single frontend) | UI de edição de qualquer marca | **UI compartilhada** | ✅ **Incluir** |
| P2-PathA-2 | `app-redator/backend/services/claude_service.py:545` (ATENÇÃO: deslocou de 483 para 545 pós-Sprint 2A) | generic (nested em `generate_overlay`) | `generate_overlay()` é chamada APENAS por `generation.py:118,155` (endpoints `/generate-all` e `/regenerate-overlay` genéricos); **zero callers RC** | **BO semântico** — ambíguo (B2) | ⚠️ **Decidir** (ver §B2 abaixo) |
| P4-008 | `app-redator/backend/prompts/rc_automation_prompt.py:60` (deslocou de 57 para 60 pós-Sprint 2A P4-001) | rc_automation (path contém `rc_`) | prompt de automação ManyChat específico do RC | **RC-específico** | ✅ **Incluir** |
| C1 | `app-curadoria/backend/services/download.py:114-117` (função `sanitize_filename`, não `sanitize_name`) | app-curadoria (não-BO) | download de vídeos na curadoria (todas marcas) | **Curadoria** | ✅ **Incluir** |
| T9-spam | `app-editor/backend/app/main.py:77` (schema `editor_perfis`, coluna `anti_spam_terms VARCHAR(500)`) | app-editor (infra shared) | schema usado por todas marcas/perfis | **Editor infra** | ✅ **Incluir** |

## B2 — P2-PathA-2 análise aprofundada

### Evidência coletada

**1. Função e linha:** `_calcular_duracao_leitura` é função interna de `generate_overlay` em `claude_service.py:487-507`. O clamp P2-PathA-2 está fora dela, na linha 545:

```python
# claude_service.py:540-547 (contexto)
if gap > 2:
    extra_per = gap / len(parsed)
    current_ts = 0.0
    for i, entry in enumerate(parsed):
        entry["timestamp"] = _secs_to_ts(int(round(current_ts)))
        duracao = _calcular_duracao_leitura(entry.get("text", "")) + extra_per
        duracao = min(12.0, duracao)  # cap para legibilidade  ← P2-PathA-2
        current_ts += duracao
```

**2. Callers de `generate_overlay()`:**
```
app-redator/backend/routers/generation.py:118   # endpoint /generate-all (genérico)
app-redator/backend/routers/generation.py:155   # endpoint /regenerate-overlay (genérico)
```
Zero callers `_rc`. RC usa `_process_overlay_rc` em claude_service.py (função separada, não compartilhada).

**3. Docstring interna (linhas 496-498):**
> "Sprint 2A P2-PathA-1: Path A (BO) usa range 5-8s, distinto do Path B (RC, 4-6s settled Sprint 1 R4/R5). Alinhamento 4-6 vira débito Sprint 2B+ (decisão editorial sobre cadência específica do BO pendente)."

**4. Precedente Sprint 2A:** P2-PathA-1 (`max(5.0, min(8.0, ...))` na linha 502-507 da mesma função `_calcular_duracao_leitura`) foi classificado como "redator-BO" na tabela PROMPT 8 mas **INCLUÍDO em Sprint 2A** (commit `f6b1da6`) com patch conservador (`[BO Clamp PathA]` logger.warning + manter clamp). Decisão 2 do operador no Sprint 2A explicita: "alinhamento 4-6 vira débito Sprint 2B+".

### Análise

- Classificação oficial na §4.2: "redator-**BO**"
- Função `generate_overlay` não tem suffix `_bo` (portanto §1.4 do PROMPT 10B não proíbe por letra)
- Semanticamente é pipeline BO/legacy — zero RC invoca
- Sprint 2A abriu precedente patchando P2-PathA-1 na mesma função, mesma natureza

### Duas trilhas possíveis

**Trilha A — Incluir no Sprint 2B (consistência com Sprint 2A)**

- Justificativa: P2-PathA-1 foi patcheada no Sprint 2A com decisão explícita "alinhamento 4-6 vira débito Sprint 2B+". P2-PathA-2 é o segundo clamp da mesma função editorial BO — patch paralelo conservador (`[BO Clamp PathA Redistribution]` logger.warning + manter `min(12.0, duracao)`). Fecha o conjunto.
- Risco: contradiz interpretação strict de §1.4 ("BO-específico" por semântica, ainda que sem sufixo `_bo`).
- Patch estimado: 4-6 LOC (logger.warning + retenção do clamp atual).

**Trilha B — Transferir para sessão paralela BO**

- Justificativa: aplicar filtragem rigorosa — `generate_overlay` é BO semântico, zero RC o invoca. Sessão paralela BO já vai refatorar `_enforce_line_breaks_bo` e código BO — P2-PathA-2 pode entrar naturalmente lá.
- Risco: P2-PathA-1 fica órfã como único patch BO no código RC+infra (inconsistência histórica, mas não regressão).
- Consequência: Sprint 2B perde 1 item; sessão paralela ganha 1.

### Recomendação

**Operador decide.** Trilha A tem consistência histórica, Trilha B tem filtragem limpa. Ambas são defensáveis. Pergunta é se §1.4 deve ser interpretado por letra (sufixo `_bo`) ou espírito (função semanticamente BO).

## B3 — R-audit-02 análise aprofundada (validação extra solicitada)

### Evidência coletada

**1. Função alvo:** `_sanitize_post` em `claude_service.py:636-652` — sem sufixo `_rc` nem `_bo`.

**2. Callers de `_sanitize_post`:** apenas `generate_post()` em `claude_service.py:669` (dentro da própria função `generate_post`).

**3. Callers de `generate_post()`:**
```
app-redator/backend/routers/generation.py:114   # endpoint /generate-all (genérico, dentro do handler generate_all)
app-redator/backend/routers/generation.py:299   # endpoint /regenerate-post (genérico)
```
Zero callers `_rc`. RC tem `generate_post_rc()` em `claude_service.py:1373` (função **separada**) que invoca `_sanitize_rc`, não `_sanitize_post`.

**4. Verificação de imports:**
```
grep -rn "from .*claude_service import" --include="*.py"
```
Apenas os 2 callers conhecidos em generation.py.

### Análise

- `_sanitize_post` é consumida exclusivamente por `generate_post()` (pipeline genérico/BO/legacy)
- RC tem path próprio (`generate_post_rc` → `_sanitize_rc`)
- `generate_post()` é invocada nos endpoints legacy `/generate-all` e `/regenerate-post`, que atendem marcas BO/outras (não RC)
- Zero sobreposição funcional com RC

### Recomendação — três opções

- **A — Transferir R-audit-02 para sessão paralela BO** (recomendada)
  - Justificativa: função é BO/legacy semanticamente, zero RC a invoca. Reescrita/refactor BO vai reavaliar essa função junto com outras limpezas. Patch paliativo aqui vira lixo técnico lá.
  - Patch esperado: `logger.warning([Sanitize Post Discard])` com contagem e pattern.
- **B — Incluir como infra compartilhada**
  - Justificativa: `generate_post()` e `_sanitize_post` *poderiam* ser reaproveitados por RC no futuro. §1.3.1 do PROMPT 10B afirmou "provavelmente é infra compartilhada RC+BO".
  - Riscos: investigação mostra zero uso RC; "poderiam no futuro" é especulativo.
- **C — Função órfã / ambíguo (operador decide)**
  - Ação dependente de diretriz do operador.

### Recomendação final do executor

**A — Transferir R-audit-02 para sessão paralela BO.** Evidência concreta mostra:
1. Zero callers RC (direto ou indireto)
2. RC tem pipeline próprio (`generate_post_rc` → `_sanitize_rc`)
3. `_sanitize_post` serve exclusivamente o path legacy/BO consumido por `/generate-all` e `/regenerate-post`

O pressuposto do PROMPT 10B §1.3.1 ("provavelmente é infra compartilhada RC+BO") revela-se incorreto após grep. Transferir é consistente com filtragem rigorosa e evita contaminação do escopo.

Se operador preferir incluir (Trilha B): logger neutro `logger` (linha 8 do módulo), prefix `[Sanitize Post Discard]`, com descrição de pattern que disparou + trecho da linha (50 chars) + diferenciação entre `_MARKDOWN_SEPARATORS` e `_ENGAGEMENT_BAIT_PATTERNS` (dois caminhos de descarte).

## Resumo final da filtragem

| ID | Decisão final (proposta) |
|---|---|
| R6 | ✅ Incluir (shared infra) |
| P1-UI1 | ✅ Incluir (UI portal) |
| P1-UI2 | ✅ Incluir (UI portal) |
| P2-PathA-2 | ⚠️ Operador decide — Trilha A (incluir, consistente com Sprint 2A) ou Trilha B (transferir, filtragem limpa) |
| P4-008 | ✅ Incluir (RC-específico, rc_automation_prompt) |
| C1 | ✅ Incluir (curadoria não-BO) |
| T9-spam | ✅ Incluir (editor infra) |

**CRÍTICOS:**
- R-audit-01 (`_sanitize_rc`): ✅ Incluir (RC-específico)
- R-audit-02 (`_sanitize_post`): ⚠️ Operador decide — recomendação executor é A (transferir); alternativa B (incluir como BO/legacy com patch conservador) existe se operador preferir

**Débito documental:**
- OB-1: ✅ Incluir (edição trivial linha 148 de `RELATORIO_EXECUCAO_SPRINT_2A.md`)

**P3-Prob (ALTA migrada):**
- 7 regras — reanálise em Fase 2 com default parcimônia (preferir JÁ RESOLVIDA/OBSOLETA salvo evidência concreta de valor)
