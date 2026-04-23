# Relatório de Execução — Sprint 2A (PROMPT 10B-A)

**Data:** 2026-04-23
**Branch:** `claude/execucao-sprint-2a-20260423-0304`
**Base:** `main @ ac6b94a` (merge Sprint 1 execution + auditoria APROVADO)
**HEAD final (antes deste commit de relatório):** `f6b1da6`
**Commits:** 13 até agora (1 inventário + 1 reconciliação + 2 docs + 9 fix) + 1 deste relatório = **14 totais**
**Fontes autoritativas:**
- [RELATORIO_INVESTIGACAO_PROFUNDA.md §4.2](../RELATORIO_INVESTIGACAO_PROFUNDA.md)
- [RELATORIO_AUDITORIA_INVESTIGACAO.md](../auditoria_profunda/RELATORIO_AUDITORIA_INVESTIGACAO.md) (contagens 33/12/14/7)
- [RECONCILIACAO_PATHS.md](../execucao_sprint_1/RECONCILIACAO_PATHS.md) (pós-refactor sentinel)
- [RELATORIO_EXECUCAO_SPRINT_1.md](../execucao_sprint_1/RELATORIO_EXECUCAO_SPRINT_1.md) (7 findings resolvidos: R1-b, R2, R3, R4, R5, R7, P1-Trans)
- [RELATORIO_AUDITORIA_SPRINT_1.md](../auditoria_sprint_1/RELATORIO_AUDITORIA_SPRINT_1.md) (APROVADO + 3 débitos D1/D2/D3)
- [INVENTARIO_SPRINT_2A.md](INVENTARIO_SPRINT_2A.md)
- [RECONCILIACAO_SPRINT_2A.md](RECONCILIACAO_SPRINT_2A.md)

---

## Resumo executivo

Executados **7 CRÍTICAS remanescentes + 11 ALTAS remanescentes + 3 débitos documentais** do Sprint 2A. Total declarado: 21 itens. Total de **alvos distintos de código/doc: 20** (P1-Doc ≡ D1 resolvido em commit único por decisão 4 do operador).

**Decisão de escopo na Fase 1:** P3-Prob (ALTA, algoritmo greedy wrap em claude_service.py:819-887) migrou para **Sprint 2B** por tocar função `_enforce_line_breaks_rc` que Sprint 1 refatorou. Análise das 7 regras de balanceamento exige escopo e decisão editorial fora do Sprint 2A.

**7 CRÍTICAS patcheadas:** Ed-MIG1, Ed-MIG2, P1-Ed3 (cascade), P1-Ed4, P1-Ed5 (cascade), P1-Ed6 (cascade), BO-001.
**11 ALTAS patcheadas:** P1-Doc, P1-Ed1, P1-Ed2, P2-PathA-1, P4-001, P4-005, P4-006a, P4-006b, P4-007a, P4-007b, P4-007c.
**3 débitos documentais:** D1 (=P1-Doc, 1 commit), D2 (R5 teste manual), D3 (contagem 21→20).

**AST parse OK** em todos os 8 arquivos Python tocados após cada commit.

**Sprint 2B intocado:** `_sanitize_rc` e `_sanitize_post` (R-audit-01/02 MÉDIAS), hardcodes 35 BO em `translation.py:199` e `translate_service.py:1042` (deslocou de 1015 por este sprint adicionar linhas acima), 7 MÉDIAS (R6, P1-UI1/2, P2-PathA-2, P4-008, C1, T9-spam), P3-Prob. **Zero hunks em funções ou linhas fora do escopo aprovado.**

**Zero arquivos fora de `app-editor/`, `app-redator/` e `docs/`** (curadoria, portal, shared preservados).

---

## Decisões do operador aplicadas

| # | Decisão | Aplicação |
|---|---|---|
| 1 | BO-001 conservador (log + manter truncamento) | Commit `6804d49`: `[BO Narrative Truncate]` antes de `narrative[:max_chars]` |
| 2 | P2-PathA-1 conservador (log + manter 5-8s) | Commit `f6b1da6`: `[BO Clamp PathA]` antes de `max(5.0, min(8.0, ...))`; alinhamento 4-6 vira débito Sprint 2B+ |
| 3 | P4-00x conservador (log + manter truncamento) | Commits `1b95fd2` (P4-001), `28cd1a6` (P4-005), `52c5437` (P4-006a/b), `a2da8bc` (P4-007a/b/c) |
| 4 | P1-Doc ≡ D1 = 1 commit único | Commit `49274a6`: docstring `translate_service.py:533` 33→38 |
| 5 | Prefixo `[EDITOR OverlayBreak]` (en_US) | Aplicado em commit `e27c5bd` — consistente com demais 8 prefixos |
| **extra** | **Ed-MIG1/MIG2: substituir valores pelos corretos em vez de remover** | Commit `e74a8ef`: INSERT RC 66/33→114/38, Ed-MIG1 força 38 chars/linha, Ed-MIG2 força 114 chars total |
| **extra** | **OB-3 como débito Sprint 3+** | Registrado em commit `f200274` e na seção "Débitos identificados" abaixo |

---

## Por finding

### Débitos documentais (3)

#### D1/P1-Doc — docstring translate_service.py:533 (33→38)

- **Commit:** `49274a6`
- **Path:linha:** `app-redator/backend/services/translate_service.py:533` (INTACTO)
- **Patch:** docstring "RC: aplica re-wrap pós-tradução (≤33 chars/linha)" → "(≤38 chars/linha; idiomas verbosos ganham margem via lang)"
- **LOC:** 1 inserção / 1 remoção
- **Princípio honrado:** 4 (limite editorial documentado)
- **Sobreposição:** P1-Doc (tabela §4.2, ALTA) ≡ D1 (auditoria Sprint 1, débito). Resolvido em commit único (decisão 4).
- **Teste manual descritivo:** leitura direta da docstring em IDE — bate com realidade pós-Sprint 1 P1-Trans (`routers/translation.py:189`).

#### D2 — seção teste manual dedicada R5

- **Commit:** `c4e73ba`
- **Path:** `docs/rc_v3_migration/execucao_sprint_1/RELATORIO_EXECUCAO_SPRINT_1.md` seção R5
- **Patch:** adicionada seção "Teste manual descritivo (D2, Sprint 2A)" entre linhas 161 e 163 (antes do separador `---`). Descreve cenário específico de compressão temporal: 3 legendas + vídeo 25s → `dur_por_legenda_raw` ≈ 8.33s, esperado warning `[RC Clamp TempComp] ...` e clamp para 6.0s. Distingue de R4 (geração individual de cada legenda).
- **LOC:** ~8 inserções
- **Princípio honrado:** 4 (documentação da observabilidade R5)

#### D3 — contagem stop_reason 21→20

- **Commit:** `c4e73ba` (mesmo que D2, arquivo comum)
- **Path:** `docs/rc_v3_migration/execucao_sprint_1/RELATORIO_EXECUCAO_SPRINT_1.md:190`
- **Patch:** "21 matches (vs 0 antes)" → "20 matches (vs 0 antes) — decomposição: 2 docstring + 6 checks + 6 warnings + 6 raises. Nota D3 (Sprint 2A): declaração original de 21 era imprecisa por ±1; auditoria Sprint 1 confirmou contagem real = 20."
- **LOC:** 1 inserção / 1 remoção
- **Princípio honrado:** 4 (factualidade da observabilidade)

### CRÍTICAS (7)

#### Ed-MIG1 + Ed-MIG2 — substituição de valores forçados

- **Commit:** `e74a8ef`
- **Paths:**
  - `app-editor/backend/app/main.py:333` (INSERT RC)
  - `app-editor/backend/app/main.py:363-372` (Ed-MIG1)
  - `app-editor/backend/app/main.py:737-744` (Ed-MIG2)
- **Patch:**
  - INSERT RC: `66, 33` → `114, 38` (perfis novos nascem corretos)
  - Ed-MIG1: cuida apenas de `overlay_max_chars_linha = 38` com guard idempotente `WHERE overlay_max_chars_linha != 38` (cobre RC em 33 prod atual)
  - Ed-MIG2: `overlay_max_chars = 99` → `114` com guard `WHERE overlay_max_chars != 114`
  - **Separação clara de responsabilidade:** Ed-MIG1 = chars/linha; Ed-MIG2 = total. Zero sobreposição.
  - Comentários atualizados apontando Sprint 1 P1-Trans + Sprint 2A.
- **LOC:** 13 inserções / 9 remoções
- **Princípio honrado:** 4 (limites editoriais corretos + observabilidade em startup)
- **Valores editoriais justificados:**
  - RC chars/linha = **38** (Sprint 1 P1-Trans, `routers/translation.py:189`, `_enforce_line_breaks_rc` default)
  - RC total = **3 linhas × 38 = 114**
  - BO total = 2 linhas × 35 = 70 (INSERT `:166`, inalterado)
- **Teste manual descritivo:**
  - Após deploy do editor, logs esperados no startup: `Migration: backfill overlay_max_chars_linha RC = 38 OK (Sprint 2A Ed-MIG1)` e `Migration: backfill overlay_max_chars RC = 114 OK (Sprint 2A Ed-MIG2)`. 
  - Query em produção pós-deploy: `SELECT sigla, overlay_max_chars, overlay_max_chars_linha FROM editor_perfis WHERE sigla IN ('RC', 'BO');` — esperado RC=114/38, BO=70/35.

#### P1-Ed4 — logger.warning em _truncar_texto (cascata P1-Ed5 + P1-Ed6)

- **Commit:** `f200274`
- **Path:** `app-editor/backend/app/services/legendas.py:241-264`
- **Patch:** adicionado `logger.warning(f"[EDITOR Truncate] Texto excede max_chars...")` no início da função (após early-return se `len <= max_chars`). Comportamento preservado.
- **LOC:** 17 inserções / 6 remoções (inclui reformat de docstring)
- **Princípio honrado:** 1 (nunca cortar silenciosamente) + 4 (observabilidade)
- **Cascata:**
  - P1-Ed5 (`legendas.py:653`, lyrics — CRÍTICA) resolvido via warning interno. Caller já tinha warning post-hoc (`[legendas] Lyrics truncado`).
  - P1-Ed6 (`legendas.py:670`, tradução — CRÍTICA) resolvido via warning interno. Caller já tinha warning post-hoc (`[legendas] Tradução truncado`).
  - P1-Ed3 (`legendas.py:169`, `_formatar_overlay` — CRÍTICA) resolvido em cascade — os 3 callsites internos (linhas 202, 235, 237) agora têm warning pré-hoc.
- **Teste manual descritivo:** render de preview com lyrics longas (>lyrics_max = 43 chars). Log esperado: `[EDITOR Truncate] Texto excede max_chars=43 (XX chars): '...'`. Observar também `[legendas] Lyrics truncado` subsequente. Observabilidade dupla é intencional.
- **Inviabilidade de "remover função" (remediação PROMPT 8 original):** `_truncar_texto` tem 5 callers internos em legendas.py. Remoção romperia `_formatar_overlay:202/235/237`, lyrics @:653, tradução @:670. Reinterpretação conservadora: warning + manter comportamento.

#### BO-001 — logger.warning em _extract_narrative (overlay_prompt.py)

- **Commit:** `6804d49`
- **Path:** `app-redator/backend/prompts/overlay_prompt.py:77` (função `_extract_narrative` @:45-78)
- **Patch:**
  - Adicionado `import logging; logger = logging.getLogger(__name__)` no topo (módulo não tinha).
  - Warning `[BO Narrative Truncate]` antes de `narrative[:max_chars].rsplit(" ", 1)[0] + "..."`.
- **LOC:** 11 inserções
- **Princípio honrado:** 1 (observabilidade) + 4 (defense-in-depth)
- **Callers cobertos em cascade:** `overlay_prompt.py:90` (default max_chars=500) e `:128` (max_chars=300).
- **⚠️ Patch mais arriscado do Sprint 2A** (toca prompt LLM, afeta geração de overlay BO). Validação pós-deploy obrigatória.
- **Teste manual descritivo:** publicar próximo RC/BO com post_text > 500 chars. Log esperado: `[BO Narrative Truncate] Narrativa fonte excede max_chars=500 (XXX chars): ...`. Verificar que overlay gerado mantém qualidade narrativa (comparável ao estado pré-Sprint 2A).

### ALTAS (11)

#### P1-Ed1 — logger.warning em quebrar_texto_overlay

- **Commit:** `e27c5bd`
- **Path:** `app-editor/backend/app/services/legendas.py:109`
- **Patch:** warning `[EDITOR OverlayBreak]` quando `len(texto) > max_chars`. Função não trunca (só quebra em 2 linhas com `\N`); warning sinaliza upstream que não formatou.
- **LOC:** 10 inserções (inclui reformat de docstring)
- **Princípio honrado:** 4 (observabilidade defensiva)
- **Teste manual descritivo:** render de edição com texto vindo sem quebra ASS (`\N`) do redator. Log esperado: `[EDITOR OverlayBreak] Texto sem quebras com XX chars ...`. Confirmar que overlay final tem 2 linhas balanceadas.

#### P1-Ed2 — logger.warning em _formatar_texto_legenda (dead code)

- **Commit:** `e27c5bd`
- **Path:** `app-editor/backend/app/services/legendas.py:134`
- **Patch:** warning `[EDITOR Legenda Slice]` antes do slice silencioso `linhas = linhas[:max_linhas]`. Opção A aprovada (decisão 4 operador).
- **LOC:** 12 inserções
- **Observação:** função é **dead code** (grep global confirma zero callers externos/internos). Warning é guard defense-in-depth para uso futuro eventual.
- **Princípio honrado:** 1 + 4

#### P1-Doc — docstring 33→38

Ver D1 acima (mesmo commit, cobre P1-Doc simultaneamente).

#### P2-PathA-1 — logger.warning em _calcular_duracao_leitura

- **Commit:** `f6b1da6`
- **Path:** `app-redator/backend/services/claude_service.py:498` (deslocado de 434-445 declarado)
- **Patch:** warning `[BO Clamp PathA]` quando duração raw cai fora do range [5.0, 8.0]. Clamp 5-8 preservado (distinto do Path B RC 4-6).
- **LOC:** 9 inserções
- **Princípio honrado:** 4
- **Débito Sprint 2B+:** alinhamento Path A → 4-6 pendente de decisão editorial sobre cadência específica do BO.
- **Teste manual descritivo:** gerar projeto BO com legenda de 12+ palavras (duração raw ~8.2s). Log esperado: `[BO Clamp PathA] Duração 8.20s fora do range editorial 5-8s`. Overlay final deve usar 8.0s (clamp aplicado).

#### P4-001 — rc_automation_prompt.py

- **Commit:** `1b95fd2`
- **Path:** `app-redator/backend/prompts/rc_automation_prompt.py:66`
- **Patch:** `import logging` + logger no topo + warning `[RC Automation Post Truncate]` antes de `post_clean[:500]`.
- **LOC:** 11 inserções
- **Princípio honrado:** 1 + 4

#### P4-005 — hook_prompt.py

- **Commit:** `28cd1a6`
- **Path:** `app-redator/backend/prompts/hook_prompt.py:42`
- **Patch:** `import logging` + logger no topo + refactor de inline ternário em blocos separados + warning `[Hook Research Truncate]`.
- **LOC:** 16 inserções / 1 remoção
- **Princípio honrado:** 1 + 4

#### P4-006a + P4-006b — generation.py

- **Commit:** `52c5437`
- **Paths:** `app-redator/backend/routers/generation.py:200` (dict path), `:202` (str path) — deslocado de 203/205
- **Patch:** warning `[Regen Research Truncate]` em ambos paths antes de `[:2000]`. Reutiliza `logger = logging.getLogger("rc_pipeline")` existente em `:10`.
- **LOC:** 14 inserções / 1 remoção
- **Princípio honrado:** 1 + 4

#### P4-007a + P4-007b + P4-007c — translate_service.py

- **Commit:** `a2da8bc`
- **Paths:** `app-redator/backend/services/translate_service.py:746, 749, 758` — deslocado de 740/743/752
- **Patch:** refactor de 3 truncamentos inline em f-string → extração em variáveis `identity_str`, `tom_str`, `research_str` antes da f-string. 3 warnings `[Translate Context Truncate]` com campo específico. Reutiliza `_translate_logger`.
- **LOC:** 30 inserções / 3 remoções
- **Princípio honrado:** 1 + 4

---

## Agrupamentos em commits (13 totais antes deste + 1 relatório = 14)

| # | SHA | Mensagem | Escopo |
|---|---|---|---|
| 1 | `7b65ca9` | `docs(sprint-2a): inventário + extração tabela §4.2` | Fase 1 |
| 2 | `c6d4822` | `docs(sprint-2a): reconciliação path:linha pós-Sprint 1` | Fase 2 |
| 3 | `49274a6` | `docs(sprint-2a): D1/P1-Doc atualiza docstring translate_service.py:533 (33→38)` | D1 ≡ P1-Doc |
| 4 | `c4e73ba` | `docs(sprint-2a): D2 + D3 ajustes no RELATORIO_EXECUCAO_SPRINT_1.md` | D2 + D3 |
| 5 | `e74a8ef` | `fix(sprint-2a): Ed-MIG1+Ed-MIG2 substitui valores forçados pelos corretos` | Ed-MIG1 + Ed-MIG2 + INSERT RC |
| 6 | `f200274` | `fix(sprint-2a): P1-Ed4 logger.warning em _truncar_texto (cascata P1-Ed5+P1-Ed6)` | P1-Ed4, P1-Ed3, P1-Ed5, P1-Ed6 |
| 7 | `e27c5bd` | `fix(sprint-2a): P1-Ed1+P1-Ed2 logger.warning em formatadores de legendas.py` | P1-Ed1, P1-Ed2 |
| 8 | `6804d49` | `fix(sprint-2a): BO-001 logger.warning em _extract_narrative (overlay_prompt.py)` | BO-001 |
| 9 | `1b95fd2` | `fix(sprint-2a): P4-001 logger.warning em rc_automation_prompt.py:66` | P4-001 |
| 10 | `28cd1a6` | `fix(sprint-2a): P4-005 logger.warning em hook_prompt.py:42` | P4-005 |
| 11 | `52c5437` | `fix(sprint-2a): P4-006a+P4-006b logger.warning em generation.py` | P4-006a + P4-006b |
| 12 | `a2da8bc` | `fix(sprint-2a): P4-007a+b+c logger.warning em translate_service.py` | P4-007a + P4-007b + P4-007c |
| 13 | `f6b1da6` | `fix(sprint-2a): P2-PathA-1 logger.warning em _calcular_duracao_leitura Path A` | P2-PathA-1 |
| 14 | (este) | `docs(sprint-2a): relatório de execução` | Fase 4 |

**Volume total:** 15 arquivos alterados, ~570 insertions / ~25 deletions.

---

## Débitos identificados (Sprint 2B ou além)

| # | Débito | Origem | Recomendação |
|---|---|---|---|
| 1 | **P3-Prob** — algoritmo greedy wrap sem balanceamento (7 regras §3.5) | Decisão operador Fase 1 (migrar para Sprint 2B) | Análise das 7 regras vs função `_enforce_line_breaks_rc` pós-Sprint 1 antes de tocar |
| 2 | **OB-3** — `_formatar_overlay` path `pre_formatted=True` não exercita `_truncar_texto` em produção RC/BO (flag ativo via Migration v10) | Descoberta Fase 2 | Sprint 3+: arquitetura — remover branch `pre_formatted=False` ou remover `_truncar_texto` em cascata. Exige autorização editorial |
| 3 | **Alinhamento P2-PathA** — Path A (BO) 5-8s vs Path B (RC) 4-6s | Decisão operador 2 (conservador) | Sprint 2B+: decisão editorial sobre cadência BO |
| 4 | **Preservação editorial BO-001** | Decisão operador 1 (conservador) | Sprint 2B+: preservar narrativa íntegra no prompt (remediação PROMPT 8 "(a) LLM reformular"). Exige teste de prompt e impacto em geração |
| 5 | **Revisão dos limites de contexto LLM** (P4-00x) | Padrão G1 §4.4 | Sprint 2B+: Claude Opus 4.7 suporta 1M tokens; limites atuais 500-3000 chars são conservadores demais. Decidir: preservar íntegro vs sumarizar via LLM |
| 6 | **Validação DB produção** Ed-MIG1/MIG2 | OB-5 da reconciliação | Pós-deploy: `SELECT sigla, overlay_max_chars, overlay_max_chars_linha FROM editor_perfis WHERE sigla IN ('RC','BO');` — confirmar 114/38 e 70/35 |
| 7 | **7 MÉDIAS da tabela §4.2** | Escopo Sprint 2B | R6 (shared storage), P1-UI1/2 (portal defaults), P2-PathA-2 (clamp BO Path A redistribuição), P4-008 (overlay_temas[:5]), C1 (curadoria download filename), T9-spam (editor VARCHAR) |
| 8 | **R-audit-01 + R-audit-02** | Auditoria PROMPT 9 Frente D | Sprint 2B: `_sanitize_rc` regex + `_sanitize_post` _ENGAGEMENT_BAIT_PATTERNS |
| 9 | **Ausência de testes automatizados** | Nota PROMPT 10A §2.2 | Sprint futuro com infra: testes de fumaça para os ~23 pontos de warning totais adicionados (Sprint 1 + Sprint 2A) |
| 10 | **Correção da documentação** do conflito nominal `_call_claude_json` vs `_call_claude_api_with_retry` | Sprint 1 descoberta | Sprint 2B: atualizar PROMPT 10A e reconciliação |

---

## Verificação final

### AST parse — 8 arquivos Python

| Arquivo | Status |
|---|---|
| `app-redator/backend/services/translate_service.py` | OK |
| `app-redator/backend/services/claude_service.py` | OK |
| `app-redator/backend/routers/generation.py` | OK |
| `app-redator/backend/prompts/overlay_prompt.py` | OK |
| `app-redator/backend/prompts/rc_automation_prompt.py` | OK |
| `app-redator/backend/prompts/hook_prompt.py` | OK |
| `app-editor/backend/app/main.py` | OK |
| `app-editor/backend/app/services/legendas.py` | OK |

### Grep de regressão

- **Prefixos novos Sprint 2A:** 12 matches de `[EDITOR Truncate]`, `[EDITOR OverlayBreak]`, `[EDITOR Legenda Slice]`, `[BO Narrative Truncate]`, `[RC Automation Post Truncate]`, `[Hook Research Truncate]`, `[Regen Research Truncate]`, `[Translate Context Truncate]`, `[BO Clamp PathA]` (alguns prefixos aparecem mais de 1 vez)
- **Sprint 2B intocado:**
  - `_sanitize_rc` em `claude_service.py`: intocada (zero hunks no diff)
  - `_sanitize_post` em `claude_service.py`: intocada (zero hunks no diff)
  - Hardcode 35 BO em `translation.py:199`: intacto
  - Hardcode 35 BO em `translate_service.py:1042` (deslocou de 1015 por este sprint adicionar linhas no mesmo arquivo): intacto
  - Zero arquivos em `app-curadoria/`, `app-portal/`, `shared/`
  - Zero arquivos `test_*`, `*.sql`, `/migrations/`, `/alembic/`
  - Zero modificações em `docs/rc_v3_migration/auditoria_sprint_1/`

### Escopo Sprint 2A respeitado

| Critério | Status |
|---|---|
| 7/7 CRÍTICAS remanescentes patcheadas | ✅ |
| 11/11 ALTAS remanescentes patcheadas (12 − P3-Prob para Sprint 2B) | ✅ |
| 3/3 débitos documentais resolvidos | ✅ |
| P1-Doc ≡ D1 em 1 commit único (decisão 4) | ✅ |
| Zero toque em Sprint 2B (MÉDIAS, R-audit-01/02, P3-Prob) | ✅ |
| Zero re-patch de R1-R7/P1-Trans | ✅ |
| Zero merge em main | ✅ |
| Zero push sem autorização | ⏸️ pendente |
| Zero teste automatizado criado | ✅ (débito registrado) |
| Zero alteração de schema DB (apenas dados via migrations data-only) | ✅ |
| Zero constante global nova | ✅ |
| Zero modificação em `auditoria_sprint_1/` | ✅ |
| 4 princípios editoriais honrados | ✅ (Princípios 1 e 4 invocados explicitamente) |

### Reutilização de padrões Sprint 1

| Padrão | Reutilizado em |
|---|---|
| `logger = logging.getLogger(__name__)` | overlay_prompt.py, rc_automation_prompt.py, hook_prompt.py (3 arquivos novos) |
| `_translate_logger` existente | translate_service.py (P4-007) |
| `_rc_logger` / `logger` existente | generation.py (P4-006), claude_service.py (P2-PathA-1), legendas.py (P1-Ed1/2/4) |
| Prefixos `[COMPONENTE ...]` padronizados | 9 novos prefixos criados (decisão 5 operador: `[EDITOR OverlayBreak]` confirmado com consistência en_US) |
| Warning ANTES do corte | P1-Ed4 (início da função antes da lógica), P1-Ed2 (antes do slice), P2-PathA-1 (antes do return clamp), BO-001 (antes da reatribuição), P4-* (antes de `[:N]`) |
| Guard idempotente em UPDATE SQL | Ed-MIG1 (`WHERE overlay_max_chars_linha != 38`), Ed-MIG2 (`WHERE overlay_max_chars != 114`) |

---

## Riscos pós-deploy

1. **BO-001** (patch mais arriscado): muda prompt LLM de overlay BO. Validação obrigatória na próxima publicação RC/BO. Log esperado: `[BO Narrative Truncate] ...` quando post_text excede limites (500 ou 300 chars).
2. **Ed-MIG1/MIG2:** valores DB em produção devem migrar de `overlay_max_chars=99, overlay_max_chars_linha=33` para `114, 38` no primeiro startup do editor pós-deploy. Logs esperados:
   - `Migration: backfill overlay_max_chars_linha RC = 38 OK (Sprint 2A Ed-MIG1)`
   - `Migration: backfill overlay_max_chars RC = 114 OK (Sprint 2A Ed-MIG2)`
   - Se DB já estava em 114/38 (dev local sincronizado), migrations não disparam (idempotência via guard). Silêncio é sinal de estado correto.
3. **P1-Ed4 cascata:** warnings duplos em `[legendas] Lyrics/Tradução truncado` + `[EDITOR Truncate]`. Observabilidade redundante pré+post-hoc. Aceitável; pode ser consolidado em Sprint 3.
4. **P4-00x:** todos com abordagem conservadora. Sem mudança de comportamento LLM — apenas observabilidade. Risco próximo de zero.

---

## Conformidade com PROMPT 10B-A

| Requisito | Status |
|---|---|
| Ler 5 artefatos autoritativos antes de edits | ✅ (§1.7 validado Fase 1) |
| Validar path:linha via `sed`/`grep`/`Read` antes de cada patch | ✅ (Fase 2 reconciliação + validações inline) |
| Aplicar patches em ordem D1/D2/D3 → CRÍTICAS → ALTAS | ✅ |
| Commit atômico por finding ou grupo coerente (12 patches) | ✅ |
| Respeitar os 4 princípios editoriais | ✅ (1, 4 invocados explicitamente) |
| `logger.warning` onde antes era silencioso | ✅ (12+ pontos novos) |
| Inventário (Fase 1) | ✅ (`7b65ca9`) |
| Reconciliação (Fase 2) | ✅ (`c6d4822`) |
| Relatório de execução (Fase 4) | ✅ (este arquivo) |
| PAUSA #1 (aguardar "prossiga") | ✅ |
| PAUSA #2 (aguardar "prossiga" + decisões) | ✅ |
| Decisões operador aplicadas (5 + 2 extras) | ✅ |
| PAUSA #3 (autorização push) | ⏸️ pendente (próximo passo) |
| Nenhum finding fora do Sprint 2A tocado | ✅ |
| Nenhum merge em main | ✅ |
| Nenhum push sem autorização | ✅ (aguardando) |
| Nenhum teste automatizado criado | ✅ |
| Nenhuma alteração de schema DB | ✅ (apenas dados via UPDATE em migrations existentes) |
| Nenhuma constante global sem autorização | ✅ |
| Nenhuma modificação em auditoria Sprint 1 | ✅ |

---

## Próximo passo

**PROMPT 10B-A_AUDIT** — auditoria independente da execução antes de merge em `main`.

Critérios de auditoria esperados:
- Cada um dos 21 itens (20 alvos únicos) foi patcheado no path:linha correto?
- Nenhum finding de Sprint 2B foi tocado?
- Princípios editoriais respeitados?
- Padrões do Sprint 1 reutilizados corretamente?
- Relatório de execução factual?
- Commits atômicos respeitados?
- Decisões do operador (5 + 2 extras) aplicadas fielmente?
- Ed-MIG1/MIG2 substituição foi coerente com arquitetura atual (separação chars/linha vs total)?

Se **APROVADO:** merge em `main` + deploy Railway + 48h de estabilização + Sprint 2B.
Se **REPROVADO:** operador decide refinamento ou rollback.
