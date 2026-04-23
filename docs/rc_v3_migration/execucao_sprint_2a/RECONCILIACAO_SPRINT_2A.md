# Reconciliação path:linha — Sprint 2A

**Contexto:** 21 itens catalogados em `INVENTARIO_SPRINT_2A.md`. Esta reconciliação valida cada um em `main @ ac6b94a` via `sed`/`grep`/`Read`, mapeando deslocamentos pós-Sprint 1 e identificando callers que afetam o escopo real de cada patch.

**Base:** `main @ ac6b94a` via branch `claude/execucao-sprint-2a-20260423-0304`
**Leitura obrigatória feita:** [app-editor/CLAUDE.md](../../../app-editor/CLAUDE.md) (regras de task worker, checklist pré-commit, padrão de logger)

---

## Tabela consolidada

| Finding | Path:linha declarado | Path:linha atual | Status | Observações |
|---|---|---|---|---|
| Ed-MIG1 | `main.py:363-370` | 363-370 | **INTACTO** | Idempotente: `WHERE sigla='RC' AND overlay_max_chars=70`. |
| Ed-MIG2 | `main.py:737-740` | 737-740 | **INTACTO** | Idempotente: `WHERE sigla='RC' AND overlay_max_chars != 99`. |
| P1-Ed1 | `legendas.py:109` | 109 | **INTACTO** | `quebrar_texto_overlay` só **quebra** em 2 linhas (não trunca). 1 caller interno em 183. |
| P1-Ed2 | `legendas.py:134` | 134 | **INTACTO mas DEAD CODE** | `_formatar_texto_legenda` definida mas **zero callers** — grep global retorna apenas a definição. |
| P1-Ed3 | `legendas.py:169` | 169 | **INTACTO** | `_formatar_overlay` chama `_truncar_texto` em linhas 202, 235, 237. Path `pre_formatted=False` nunca exercido em produção (RC+BO têm flag `True` via Migration v10), mas vulnerável se flag desabilitado. |
| P1-Ed4 | `legendas.py:241-264` | 241-264 | **INTACTO** | `_truncar_texto` tem 5 callers em legendas.py (202, 235, 237, 653, 670). **"Remover função" é inviável.** |
| P1-Ed5 | `legendas.py:653` | 653 | **INTACTO + POST-HOC LOG** | Caller já tem `logger.warning(f"[legendas] Lyrics truncado: ...")` em linha 655. Log é POST-hoc (depois do truncamento). |
| P1-Ed6 | `legendas.py:670` | 670 | **INTACTO + POST-HOC LOG** | Caller já tem `logger.warning(f"[legendas] Tradução truncado: ...")` em linha 672. Mesma observação de P1-Ed5. |
| BO-001 | `overlay_prompt.py:45-77` | 45-78 | **INTACTO** | `_extract_narrative` tem 2 callers: 87 (default 500) e 125 (max_chars=300). Zero logger no módulo. |
| P1-Doc | `translate_service.py:533` | 533 | **INTACTO** | Docstring "RC: aplica re-wrap pós-tradução (≤33 chars/linha)". **= D1** (patch único). |
| P2-PathA-1 | `claude_service.py:434-445` | **498** | **DESLOCADO (+53 pós-Sprint 1)** | `_calcular_duracao_leitura` interno de Path A: `return max(5.0, min(8.0, duracao))`. Path B (RC, Sprint 1) = 4-6. |
| P4-001 | `rc_automation_prompt.py:64-66` | 64-68 | **INTACTO** | `if len(post_clean) > 500: post_summary = post_clean[:500].rstrip() + "..."`. Zero logger no módulo. |
| P4-005 | `hook_prompt.py:42` | 42 | **INTACTO** | Inline: `json.dumps(research_data, ensure_ascii=False)[:3000] if isinstance(research_data, dict) else str(research_data)[:3000]`. Zero logger no módulo. |
| P4-006a | `generation.py:203` | **200** | **DESLOCADO (−3)** | `research_str = _json.dumps(research_data, ensure_ascii=False)[:2000]`. |
| P4-006b | `generation.py:205` | **202** | **DESLOCADO (−3)** | `research_str = research_data[:2000]`. |
| P4-007a | `translate_service.py:740` | **746** | **DESLOCADO (+6)** | `{identity[:500] if identity else "..."}` inline em f-string. |
| P4-007b | `translate_service.py:743` | **749** | **DESLOCADO (+6)** | `{tom[:300] if tom else "..."}` inline em f-string. |
| P4-007c | `translate_service.py:752` | **758** | **DESLOCADO (+6)** | `{str(research_data)[:1500] if research_data else "..."}` inline em f-string. |
| D1 | `translate_service.py:533` | 533 | **INTACTO** | Mesmo alvo que P1-Doc → 1 commit único. |
| D2 | `RELATORIO_EXECUCAO_SPRINT_1.md` seção R5 (linha ~148) | INTACTO | **PENDENTE** | Adicionar seção "Teste manual descritivo" dedicada. |
| D3 | `RELATORIO_EXECUCAO_SPRINT_1.md:190` | 190 | **INTACTO** | Corrigir "21 matches" → "20 matches" + nota de decomposição. |

**Findings RESOLVIDOS (remover do Sprint 2A):** 0
**Findings NÃO ENCONTRADOS (investigar):** 0
**Findings TRANSFORMADOS materialmente:** 0 (BO-001 é mesmo pattern em linha única em vez de range)

---

## Observações críticas afetando escopo dos patches

### OB-1 — `_truncar_texto` é privada e interna (P1-Ed4)

`_truncar_texto` tem **5 callers** todos dentro de `legendas.py` (202, 235, 237, 653, 670). **Não é importada** por `pipeline.py`, `test_multi_brand.py`, nem outros módulos. `verify_fix.py` tem **cópia local** para teste (não usa a função de legendas.py).

**Implicação:** "remover função" (remediação PROMPT 8) romperia os 5 callers. **Reinterpretação conservadora:** adicionar `logger.warning` ANTES do truncamento dentro da função. Comportamento preservado (defense-in-depth, Princípio 4), mas todo corte fica observável.

Benefício cascata: P1-Ed5 e P1-Ed6 ficam resolvidos automaticamente — já têm warning post-hoc nos callers, agora terão também warning pré-hoc dentro da função. Observabilidade dupla é redundante mas aceitável.

### OB-2 — `_formatar_texto_legenda` é dead code (P1-Ed2)

Grep global confirma zero callers fora da própria definição em `legendas.py:134`. Função trunca em `linhas[:max_linhas]` (linha 164) sem log, mas **nunca é executada em produção**.

**Opção A conservadora:** adicionar `logger.warning` antes do slice, manter função (consistência com Sprint 1 R2). Zero impacto.
**Opção B agressiva:** remover função inteira (deletar linhas 134-166). Zero impacto funcional confirmado.

**Recomendação:** Opção A para consistência com padrão Sprint 1. Comentário apontando "função não usada atualmente; guard adicionado para segurança futura".

### OB-3 — `_formatar_overlay` pre_formatted guard (P1-Ed3)

Path `pre_formatted=True` (linhas 175-191) **já loga warnings** `[EDITOR FALLBACK]` e `[EDITOR WARN]` sem truncar. Este é o path usado em produção para RC e BO (Migration v10 força flag `true` em ambos).

Path `pre_formatted=False` (linhas 192-238) chama `_truncar_texto` em 202, 235, 237 sem log imediato. **Este path não é exercido em produção** atualmente, mas o código vulnerável persiste como débito estrutural.

**Remediação:** o fix de P1-Ed4 (warning dentro de `_truncar_texto`) cobre este path em cascata. Nada adicional a fazer em `_formatar_overlay`.

### OB-4 — `quebrar_texto_overlay` não trunca (P1-Ed1)

Função **apenas quebra** texto em 2 linhas com `\N`. Não há `[:N]` nem `"..."`. **Não viola Princípio 1** (nunca cortar silenciosamente). Violação discutível de Princípio 2 (editor analisa chars) — mas é safety net para inputs sem quebras.

**Remediação:** adicionar `logger.warning` no início quando `len(texto) > max_chars` (sinaliza que upstream não formatou corretamente). Manter função como fallback defensivo.

### OB-5 — Ed-MIG1/MIG2 em cadeia sequencial

Ed-MIG1 (linha 363-370) força `overlay_max_chars=66, overlay_max_chars_linha=33` SE valor atual é 70. Depois Ed-MIG2 (linha 737-740) força `overlay_max_chars=99` SE valor atual != 99. Na prática, em cold start com DB virgem, Ed-MIG1 pode sobrescrever valor consistente e então Ed-MIG2 corrige para 99.

**Produção atual:** valor em `editor_perfis.overlay_max_chars` para RC **deveria ser 99** após múltiplos deploys desde Ed-MIG2. Impossível confirmar sem acesso DB; vamos assumir 99 e remover ambas as migrations, documentando como débito a ser validado em produção no próximo deploy (check no log de startup esperado: sem mensagens `Migration: backfill overlay_max_chars RC = 66/33 OK` nem `Migration v8/v9 RC: ...`).

**Remediação:** remover os blocos `conn.execute(UPDATE ...)` mantendo `with engine.begin()` / `try` intactos. Adicionar comentário apontando para este sprint. Log informativo avisando que migration foi depreciada.

### OB-6 — Prompts redator sem logger

Arquivos `overlay_prompt.py`, `rc_automation_prompt.py`, `hook_prompt.py` **não importam `logging` nem definem `logger`**. Para patches conservadores (log + manter truncamento):
- Opção: adicionar `import logging; logger = logging.getLogger(__name__)` no topo de cada arquivo.
- Consistente com padrão `claude_service.py:8`.

### OB-7 — `_extract_narrative` tem 2 callers (BO-001)

Callers em `overlay_prompt.py:87` (default 500) e `:125` (max_chars=300). Fix dentro de `_extract_narrative` cobre ambos em cascata.

**Decisão para PAUSA #2:** conservador (log + manter truncamento) ou agressivo (remover truncamento, passar narrativa íntegra para prompt)?
- **Conservador** é consistente com decisão 3 do operador (P4-00x) e com padrão Sprint 1. Vou propor conservador; operador valida.

### OB-8 — P2-PathA-1 é Path BO, não RC

`_calcular_duracao_leitura` em `claude_service.py:498` serve ao Path A, usado pelo BO. Path B (RC, 4-6s pós-Sprint 1) tem faixa editorial distinta. Remediação declarada: "(a) alinhar com Path B (4-6) ou deprecar".

**Decisão para PAUSA #2:**
- **Conservador:** adicionar `logger.warning` quando duração raw cai fora de [5.0, 8.0], manter clamp 5.0-8.0 (sem mudança de comportamento). Propor alinhamento 4.0-6.0 como débito Sprint 2B.
- **Agressivo:** trocar para 4.0-6.0 imediatamente, seguindo padrão RC.

Vou **propor conservador**; operador valida.

---

## Agrupamentos propostos para commits atômicos

Ordem prescrita: débitos documentais → CRÍTICAS → ALTAS. Reagrupados por coerência semântica:

### Bloco 1 — Débitos documentais (2 commits)

**Commit 1:** `docs(sprint-2a): D1/P1-Doc atualiza docstring translate_service.py:533 (33→38)`
- Arquivo: `app-redator/backend/services/translate_service.py`
- Linha: 533
- Cobre: D1 e P1-Doc (mesmo alvo, decisão 4)

**Commit 2:** `docs(sprint-2a): D2 + D3 ajustes no RELATORIO_EXECUCAO_SPRINT_1.md`
- Arquivo: `docs/rc_v3_migration/execucao_sprint_1/RELATORIO_EXECUCAO_SPRINT_1.md`
- Cobre: D2 (seção R5 teste manual) + D3 (contagem 21→20)
- Justificativa de agrupamento: mesmo arquivo, mudanças independentes pequenas, natureza documental homogênea.

### Bloco 2 — CRÍTICAS em app-editor (3 commits)

**Commit 3:** `fix(sprint-2a): Ed-MIG1+Ed-MIG2 remove migrations idempotentes de overlay_max_chars`
- Arquivo: `app-editor/backend/app/main.py`
- Linhas: 363-370 e 737-740
- Cobre: Ed-MIG1 + Ed-MIG2 (correlatas, mesmo arquivo, mesma semântica)
- Adiciona comentário apontando débito de validação pós-deploy

**Commit 4:** `fix(sprint-2a): P1-Ed4 logger.warning em _truncar_texto (cobre P1-Ed5+P1-Ed6 em cascata)`
- Arquivo: `app-editor/backend/app/services/legendas.py`
- Linha: 241-264
- Cobre: P1-Ed4 primariamente; P1-Ed5/P1-Ed6 via cascata (callers já têm warning post-hoc)
- Log prefixo: `[EDITOR Truncate]`

**Commit 5:** `fix(sprint-2a): P1-Ed3+P1-Ed1+P1-Ed2 logger.warning em formatadores de legendas.py`
- Arquivo: `app-editor/backend/app/services/legendas.py`
- Linhas: 109 (quebrar_texto_overlay), 134 (_formatar_texto_legenda dead code), 169 (_formatar_overlay)
- Cobre: P1-Ed1 + P1-Ed2 (ALTAS) e P1-Ed3 (CRÍTICA por associação)
- Justificativa de agrupamento: todas funções de formatação no mesmo arquivo, warnings alinhados com padrão Sprint 1
- Log prefixos: `[EDITOR Overlay Quebra]`, `[EDITOR Legenda Slice]` para P1-Ed2 dead code

### Bloco 3 — BO-001 (1 commit isolado)

**Commit 6:** `fix(sprint-2a): BO-001 logger.warning em _extract_narrative (overlay_prompt.py)`
- Arquivo: `app-redator/backend/prompts/overlay_prompt.py`
- Linha: 77 (dentro de função que começa em 45)
- Adiciona `import logging; logger = logging.getLogger(__name__)` no topo
- Log prefixo: `[BO Narrative Truncate]`
- Abordagem conservadora (a confirmar com operador na PAUSA #2)

### Bloco 4 — ALTAS de prompts (4 commits)

**Commit 7:** `fix(sprint-2a): P4-001 logger.warning em rc_automation_prompt.py:66`
- Arquivo: `app-redator/backend/prompts/rc_automation_prompt.py`
- Adiciona logger no topo + warning antes do truncamento
- Log prefixo: `[RC Automation Post Truncate]`

**Commit 8:** `fix(sprint-2a): P4-005 logger.warning em hook_prompt.py:42`
- Arquivo: `app-redator/backend/prompts/hook_prompt.py`
- Adiciona logger no topo + extrai inline para variável + warning
- Log prefixo: `[Hook Research Truncate]`

**Commit 9:** `fix(sprint-2a): P4-006a+P4-006b logger.warning em generation.py`
- Arquivo: `app-redator/backend/routers/generation.py`
- Linhas: 200 e 202
- 2 truncamentos análogos no mesmo bloco → 1 commit
- Log prefixo: `[Regen Research Truncate]`

**Commit 10:** `fix(sprint-2a): P4-007a+b+c logger.warning em translate_service.py`
- Arquivo: `app-redator/backend/services/translate_service.py`
- Linhas: 746, 749, 758
- 3 truncamentos análogos no mesmo prompt → 1 commit
- Log prefixo: `[Translate Context Truncate]`

### Bloco 5 — P2-PathA-1 (1 commit isolado)

**Commit 11:** `fix(sprint-2a): P2-PathA-1 logger.warning em _calcular_duracao_leitura Path A`
- Arquivo: `app-redator/backend/services/claude_service.py`
- Linha: 498
- Abordagem conservadora: log warning se duração cai fora de [5.0, 8.0], manter clamp (a confirmar com operador PAUSA #2)
- Log prefixo: `[BO Clamp PathA]`

### Bloco 6 — Relatório final (1 commit)

**Commit 12:** `docs(sprint-2a): relatório de execução`
- Arquivo: `docs/rc_v3_migration/execucao_sprint_2a/RELATORIO_EXECUCAO_SPRINT_2A.md`

### Total de commits

- Extração do inventário (já feito): 1 (`7b65ca9`)
- Reconciliação (este): 1
- Patches: 10 (commits 3-11, exceto commit 12 do relatório, mais 1 de docs=commits 1-2 para débitos documentais)

Ajuste: commits 1-2 docs + commits 3-11 patches (9) + commit 12 relatório = **1 reconciliação + 1 inventário + 12 commits totais = 14 commits**. Estimativa batida com plano (~13-14).

---

## Perguntas para PAUSA #2

1. **BO-001:** abordagem conservadora (log + manter truncamento) ou agressiva (remover truncamento)?
2. **P2-PathA-1:** abordagem conservadora (log + manter 5-8s) ou agressiva (alinhar 4-6s com Path B)?
3. **Agrupamentos:** ok com 12 commits (1 reconciliação + 12 patches + relatório = 14 totais), ou operador prefere mais/menos granularidade?
4. **P1-Ed2 dead code:** Opção A (adicionar warning por consistência) ou Opção B (remover função)? Recomendo A.
5. **Log prefixos:** `[EDITOR Truncate]`, `[EDITOR Overlay Quebra]`, `[EDITOR Legenda Slice]`, `[BO Narrative Truncate]`, `[RC Automation Post Truncate]`, `[Hook Research Truncate]`, `[Regen Research Truncate]`, `[Translate Context Truncate]`, `[BO Clamp PathA]` — ok?

---

## Procedência (comandos executados nesta reconciliação)

```bash
# app-editor/CLAUDE.md lido
Read app-editor/CLAUDE.md (44 linhas)

# Ed-MIG1/MIG2 confirmados
sed -n '355,380p' app-editor/backend/app/main.py
sed -n '720,755p' app-editor/backend/app/main.py

# legendas.py funções e callers
sed -n '100,265p' app-editor/backend/app/services/legendas.py
sed -n '640,680p' app-editor/backend/app/services/legendas.py
sed -n '495,525p' app-editor/backend/app/services/legendas.py

# Callers globais
grep -rn "_truncar_texto\|quebrar_texto_overlay\|_formatar_texto_legenda\|_formatar_overlay" app-editor/ --include="*.py"
grep -rn "_formatar_texto_legenda\b" app-editor/ app-redator/ app-curadoria/ app-portal/ shared/ --include="*.py"
grep -rn "_extract_narrative\b" app-redator/ --include="*.py"
grep -rn "quebrar_texto_overlay\b" (all apps)

# pipeline.py import e test_multi_brand
sed -n '1748,1768p' app-editor/backend/app/routes/pipeline.py
sed -n '1,20p' app-editor/backend/tests/test_multi_brand.py

# BO-001 + callers
sed -n '40,90p' app-redator/backend/prompts/overlay_prompt.py

# Prompts sem logger
grep -n "^import\|^from\|logger\|logging" app-redator/backend/prompts/overlay_prompt.py
grep -n "^import\|^from\|logger\|logging" app-redator/backend/prompts/rc_automation_prompt.py
grep -n "^import\|^from\|logger\|logging" app-redator/backend/prompts/hook_prompt.py

# P2-PathA-1 pós-desloc
sed -n '490,515p' app-redator/backend/services/claude_service.py

# P4-001/P4-005/P4-006/P4-007 pós-desloc
sed -n '55,75p' app-redator/backend/prompts/rc_automation_prompt.py
sed -n '35,50p' app-redator/backend/prompts/hook_prompt.py
sed -n '195,210p' app-redator/backend/routers/generation.py
sed -n '735,765p' app-redator/backend/services/translate_service.py

# P1-Doc/D1 pós-desloc
sed -n '528,538p' app-redator/backend/services/translate_service.py
```
