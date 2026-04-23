# Reanálise P3-Prob — 7 regras vs código atual (pós-R1-b)

**Data:** 2026-04-23
**Default operador:** parcimônia — preferir **JÁ RESOLVIDA** ou **OBSOLETA/DÉBITO** se a estrutura R1-b + MAX_CONTINUACOES atual já cobrir ou conflitar. **APLICAR apenas com evidência concreta de que agrega valor** ao código refatorado. Sprint 2B é remediação cirúrgica de cortes/truncamentos, **não expansão arquitetural**.

## Contexto pós-R1-b (Sprint 1)

Função `_enforce_line_breaks_rc` em [claude_service.py:891-982](app-redator/backend/services/claude_service.py:891) retorna `tuple[str, str]` = `(texto_cortado, resto)`:

- Linhas 911: fix pontuação colada
- Linhas 915-918: expansão idiom-aware (DE/PL +5, FR/IT/ES +3)
- Linhas 925-927: bailout se tudo já OK
- Linhas 932-965: greedy wrap com preferential break após `.;:,` (25+ chars)
- **Linhas 951-961: R1-b** — ao exceder `max_linhas`, captura `resto` + `_rc_logger.warning [RC LineBreak]` + devolve ao caller
- **Linhas 970-975: R2** — slice defensivo com `_rc_logger.warning [RC LineBreak]`

Caller principal `_process_overlay_rc` em [claude_service.py:1043-1085](app-redator/backend/services/claude_service.py:1043):
- Linhas 1074-1085: loop `MAX_CONTINUACOES=5` — preserva `resto` iterativamente criando legendas adicionais
- Se loop esgota com `pendente` não-vazio, loga `[RC LineBreak] MAX_CONTINUACOES atingido, resto final perdido`

Callsites de tradução/regeneração individual (4 sites: translation.py:189, generate.py:261, translate_service.py:558 e :1033) logam resto descartado como débito Sprint 2 (regeneração via LLM).

## Classificação regra-por-regra

### Regra 1 — Nunca truncar conteúdo

**Texto original (§3.5):** "Princípio Editorial 1. Se legenda excede capacidade em 3 linhas de 38 chars, levantar exceção ou emitir alerta visível no portal."

**Análise:**
- **Path principal (`_process_overlay_rc`):** R1-b + MAX_CONTINUACOES=5 preserva texto excedente criando legendas adicionais. Truncamento **não ocorre** — texto vira N legendas consecutivas. Princípio 1 atendido via preservação real.
- **Callsites de tradução:** logam descarte como warning explícito (não silencioso). Descarte é débito Sprint 2 (regeneração via LLM).
- **Parte "alerta visível no portal":** sobrepõe com Regra 6 (ver abaixo). Logs existem; flag estruturada para UI não.

**Decisão:** **ii — JÁ RESOLVIDA**

**Justificativa:** R1-b + MAX_CONTINUACOES eliminou truncamento silencioso no path principal RC. Espírito da Regra 1 atendido. Refinamento "alerta visual no portal" = Regra 6 (tratada separadamente).

---

### Regra 2 — Balanceamento

**Texto original:** "Após word-wrap greedy, avaliar razão max/min das linhas. Se > 2:1, tentar re-distribuir palavra-a-palavra."

**Análise:**
- Código atual tem zero heurística de balanceamento — algoritmo greedy empacota left-to-right.
- R1-b **não cobre** balanceamento (trata overflow, não desigualdade entre linhas sobreviventes).
- Exemplo: texto "a b c d e f g h i j" com max 38 chars pode virar linha 1 = "a b c d e f g" (14c) e linha 2 = "h i j" (5c) — desbalanceado 2.8:1.
- **Valor:** estético/legibilidade, não truncamento. Não há risco de perda de conteúdo.
- **Sprint 2B escopo:** "remediação cirúrgica de **cortes/truncamentos**", **não expansão de qualidade editorial**.

**Decisão:** **iii — OBSOLETA para Sprint 2B / DÉBITO para sprint futuro**

**Justificativa:** desbalanceamento não é truncamento. Sprint 2B não é o lugar para qualidade estética. Implementação requer ~30 LOC + lógica de re-distribuição potencialmente conflitante com Regras 3/4 — expansão arquitetural.

---

### Regra 3 — Evitar palavra isolada

**Texto original:** "Se linha N tem ≤ 2 palavras E N > 1, mover palavra final da linha N-1 para linha N (empurrar)."

**Análise:**
- Código atual não trata "palavras isoladas" após wrap.
- R1-b **não cobre**.
- **Valor:** estético (linhas com 1-2 palavras ficam "soltas").
- **Não corrige truncamento** — é refinamento visual.

**Decisão:** **iii — OBSOLETA para Sprint 2B / DÉBITO para sprint futuro**

**Justificativa:** idêntica à Regra 2 — qualidade estética, não cirurgia de truncamento.

---

### Regra 4 — Unidades sintáticas

**Texto original:** "Proibir quebra após artigo/preposição curta (a, o, de, em, no, na, do, da). Preferir quebra antes."

**Análise:**
- Código atual tem preferential break apenas após `.;:,` com 25+ chars (linhas 943-946).
- Não há lista de stop-words sintáticas.
- R1-b **não cobre**.
- **Valor:** qualidade editorial — quebra após "o" ou "de" parece erro gramatical.
- **Tangente a truncamento:** break point influencia onde o `resto` corta, mas indiretamente. Não é cirurgia de truncamento.

**Decisão:** **iii — OBSOLETA para Sprint 2B / DÉBITO para sprint futuro**

**Justificativa:** qualidade de quebra sintática ≠ remediação de corte. Implementação requer lista stop-words + lógica preferential extra — ~15 LOC + testes. Débito legítimo mas fora do escopo cirúrgico de Sprint 2B.

---

### Regra 5 — Split em 2 legendas quando excede

**Texto original:** "Se texto tem capacidade para 2 legendas (tempo_narrativo permite), gerar legenda extra em vez de truncar. Requer sinalização de re-distribuição de timestamps."

**Análise:**
- **R1-b + MAX_CONTINUACOES=5**: JÁ gera legendas extras automaticamente quando texto excede. Loop em `_process_overlay_rc:1074-1085` faz exatamente isso.
- Diferença sutil: Regra 5 pedia checagem "se tempo_narrativo permite" antes de criar. R1-b cria sempre (até 5x), delegando overflow de timeline para downstream em `_process_overlay_rc` (após loop).
- Consequência prática: legendas extras podem encavalar o CTA se timeline não tem espaço — mas isso é tratado por outras partes de `_process_overlay_rc` (cálculo de `cta_duracao` e `tempo_narrativo`).
- **Espírito da regra:** "não truncar, criar legenda extra" — **atendido**.
- **Letra da regra:** "checar tempo_narrativo antes" — **não atendido**, mas é micro-otimização.

**Decisão:** **ii — JÁ RESOLVIDA (resolvida diferentemente)**

**Justificativa:** R1-b + MAX_CONTINUACOES satisfaz o espírito de "gerar legenda extra em vez de truncar". Refinamento "checar tempo_narrativo" é micro-otimização com retorno marginal — se timeline não permite, downstream trata. Implementar esse refinamento introduziria lógica condicional que pode conflitar com MAX_CONTINUACOES existente.

---

### Regra 6 — Alerta visual no portal

**Texto original:** "Se algoritmo não conseguir preservar texto integral em 3 linhas com balanceamento razoável, marcar legenda com flag visual `_needs_editorial_review` e mostrar no editor. Operador decide: editar texto, aceitar quebra imperfeita, ou solicitar regeração."

**Análise:**
- Código atual: `_rc_logger.warning` em Railway logs quando R1-b/R2/MAX_CONTINUACOES triggar. Logs existem, portanto operador com acesso à observabilidade vê os casos.
- **Flag `_needs_editorial_review` não existe** no modelo/schema nem na UI.
- Implementação requer:
  - Python: adicionar campo ao retorno de `_process_overlay_rc` ou persistir em `project.overlay_audit` (já existe) com novo key
  - Next.js: renderizar flag na tela `/redator/projeto/[id]/overlay` (approve-overlay.tsx)
  - Potencialmente DB schema change se quiser persistir por legenda individualmente
- **Expansão arquitetural significativa.** Viola §7: "Zero criação de testes automatizados, Zero alteração de schema DB, Zero criação de constante global sem autorização".

**Decisão:** **iii — OBSOLETA para Sprint 2B / DÉBITO arquitetural para sprint futuro**

**Justificativa:** feature legítima e valiosa mas requer mudança cross-stack (Python + Next.js + possivelmente schema). Sprint 2B explicitamente proíbe infra nova. Logs existentes em Railway atendem o requisito defensivo mínimo hoje.

---

### Regra 7 — Zero truncamento silencioso

**Texto original:** "Remover o `break` + descarte em [claude_service.py:869-873] e o slice em [:880]. Substituir por raise ou retorno com flag de erro."

**Análise:**
- **Linhas 869-873 originais (pré-R1-b):** continha `break` seguido de descarte silencioso.
- **Sprint 1 R1-b (linhas atuais 951-961):** o `break` ainda existe, mas:
  1. Agora **captura `resto`** antes (linha 955)
  2. Loga `[RC LineBreak] Excedeu max_linhas... devolvendo X palavras em resto` (linhas 956-959)
  3. Retorna `resto` ao caller via tupla
- **Linha 880 original (slice):** preservada como slice defensivo, mas agora:
  1. Loga `[RC LineBreak] Slice defensivo cortando X linhas extras` (linhas 971-974) quando ativa
  2. Raramente executa no fluxo normal (loop já termina antes)
- **"raise ou flag de erro":** R1-b substituiu por **"retorno de tupla com semântica explícita"** — `(texto, resto)` onde `resto != ""` é o "flag de erro" estruturado.

**Decisão:** **ii — JÁ RESOLVIDA**

**Justificativa:** Sprint 1 R1-b + R2 transformaram os dois pontos de truncamento silencioso em operações explicitamente logadas e com retorno estruturado. O `break` e o slice ainda existem (por razões de defensibilidade), mas **nenhum é silencioso** — ambos logam via `_rc_logger.warning` e o primeiro preserva o conteúdo. Zero truncamento silencioso atual.

Implementar o `raise` literal da Regra 7 quebraria o caller `_process_overlay_rc` que depende da tupla para preservar conteúdo.

---

## Sumário

| Regra | Decisão | Contagem |
|---|---|---|
| 1 — Nunca truncar | **ii JÁ RESOLVIDA** | 1 |
| 2 — Balanceamento | **iii OBSOLETA/DÉBITO** | 1 |
| 3 — Palavra isolada | **iii OBSOLETA/DÉBITO** | 1 |
| 4 — Unidades sintáticas | **iii OBSOLETA/DÉBITO** | 1 |
| 5 — Split em legendas | **ii JÁ RESOLVIDA** | 1 |
| 6 — Alerta visual portal | **iii OBSOLETA/DÉBITO** | 1 |
| 7 — Zero truncamento silencioso | **ii JÁ RESOLVIDA** | 1 |

**Totais:**
- **(i) APLICAR:** **0**
- **(ii) JÁ RESOLVIDA:** **3** (Regras 1, 5, 7)
- **(iii) OBSOLETA/DÉBITO:** **4** (Regras 2, 3, 4, 6)

## Implicação para Fase 3

**Zero commits de P3-Prob em Fase 3.**

Sprint 2B aplica os 7 itens não-P3-Prob confirmados:
1. OB-1 (documental)
2. R-audit-01 (CRÍTICO)
3. R6, C1, P4-008, T9-spam, P1-UI1+P1-UI2 (6 MÉDIAS agrupadas em 5 commits)

**Total de commits fix em Fase 3:** 6-7 commits (2 docs + 1 crítico + 4-5 médias)

## Débitos P3-Prob registrados (para sprint futuro)

As 4 regras classificadas como iii (OBSOLETA/DÉBITO) são melhorias legítimas de qualidade editorial a considerar em sprint futuro:

1. **Regra 2 — Balanceamento:** pós-processador de ~30 LOC para re-distribuir palavras se razão max/min > 2:1
2. **Regra 3 — Palavra isolada:** heurística ~20 LOC para empurrar palavras se linha N tem ≤2 palavras
3. **Regra 4 — Stop-words sintáticas:** lista de artigos/preposições + lógica preferential break, ~15 LOC
4. **Regra 6 — Alerta visual portal:** feature cross-stack (Python + Next.js + possivelmente schema) — sprint dedicado

**Ordem sugerida pelo §3.5 original:** 3 → 2 → 4 → 6. Regra 5 redundante pós-R1-b.

## Justificativa global do default parcimônia

Sprint 2B é **remediação cirúrgica** de cortes/truncamentos em RC + infra compartilhada. As 7 regras P3-Prob são, em sua natureza, **expansões de qualidade editorial** que:
- Já foram total ou parcialmente resolvidas pelo Sprint 1 R1-b + R2 (regras 1, 5, 7)
- Ou são melhorias estéticas sem risco de perda de conteúdo (regras 2, 3, 4)
- Ou requerem expansão cross-stack proibida (regra 6)

Nenhuma regra justifica APLICAR sob o critério "agrega valor concreto ao código refatorado como remediação de truncamento silencioso". Todas as 7 são débitos corretamente registrados para ciclos futuros.

**Guardrail do operador:** "Se contagem total de commits aproximar-se ou exceder Sprint 2A (21 itens), reavaliar escopo."

Sprint 2B com default parcimônia: **~10 commits totais** (4 docs + 6-7 fix) — bem abaixo do limite. ✓
