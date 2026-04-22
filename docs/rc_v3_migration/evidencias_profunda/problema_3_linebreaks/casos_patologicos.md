# Casos patológicos — 5 cenários simulados em `_enforce_line_breaks_rc`

Simulações feitas por leitura estática de [claude_service.py:819-887](app-redator/backend/services/claude_service.py:819), sem execução runtime. Parâmetros assumidos: `tipo="corpo"` (max_linhas=3), `max_chars_linha=38`, `lang="pt"` (sem expansão).

## Caso A — 50 chars em uma frase sem pontuação

**Texto:** `"pavarotti redefiniu a opera italiana no exterior"` (48 chars, 7 palavras)

**Trace:**
| Iteração | Palavra | `linha_atual` após | `len` | Cabe? | Ação |
|----------|---------|---------------------|-------|-------|------|
| 1 | pavarotti | "pavarotti" | 9 | sim | continua |
| 2 | redefiniu | "pavarotti redefiniu" | 19 | sim | continua |
| 3 | a | "pavarotti redefiniu a" | 21 | sim | continua |
| 4 | opera | "pavarotti redefiniu a opera" | 27 | sim | continua |
| 5 | italiana | "pavarotti redefiniu a opera italiana" | 36 | sim | continua |
| 6 | no | "pavarotti redefiniu a opera italiana no" | 39 | **não** (>38) | append "...italiana" (36), linha_atual="no" |
| 7 | exterior | "no exterior" | 11 | sim | continua |

**Saída:**
- Linha 1: `"pavarotti redefiniu a opera italiana"` (36 chars)
- Linha 2: `"no exterior"` (11 chars)

**Avaliação:** desbalanceamento severo **36:11** (3.3:1). Linha 2 tem apenas 2 palavras. **ANTI-PADRÃO** descrito pelo operador ("linha com 1 palavra e outra com muitas"). Quebra editorialmente superior: `"pavarotti redefiniu a opera\nitaliana no exterior"` (27:20, razão 1.35:1).

## Caso B — 3 frases curtas, pontuação early-break ativo

**Texto:** `"o tenor chorou. a plateia aplaudiu. a música tocou mais uma vez suave."` (~71 chars, 3 frases)

**Trace:** com early-break ativo ([claude_service.py:860-864](app-redator/backend/services/claude_service.py:860)): `if len(linha_atual) >= 25 and linha_atual[-1] in ",.;:" and len(novas_linhas) < max_linhas - 1`:
- Build até "o tenor chorou. a plateia aplaudiu." (35) — tem `.`, len ≥ 25, novas_linhas (0) < 2 → **early-break**
- Linha 1 = "o tenor chorou. a plateia aplaudiu."
- Build até "a música tocou mais uma vez suave." (34) — tem `.`, len ≥ 25, novas_linhas (1) < 2 → early-break
- Linha 2 = "a música tocou mais uma vez suave."

**Saída:** 2 linhas balanceadas (35:34).

**Avaliação:** código funcionou razoavelmente aqui — o early-break no ponto final ajuda. **Mas editorialmente é questionável**: 3 frases completas em uma única legenda. Pelo princípio editorial "Uma ideia por legenda" ([rc_overlay_prompt.py:411](app-redator/backend/prompts/rc_overlay_prompt.py:411) "vírgula entre dois fatos = duas legendas"), este texto deveria virar 2 ou 3 legendas, não uma só de 2 linhas. **O algoritmo não tem como decidir "dividir em legendas separadas" — só funciona dentro de uma legenda.**

## Caso C — frase 29 chars + palavra curta isolada

**Texto:** `"aquele momento foi inesquecível pra ele"` (39 chars, 6 palavras)

**Trace:**
- Build "aquele momento foi inesquecível pra" (35) → cabe
- "aquele momento foi inesquecível pra ele" (39) → não cabe (>38)
  - append "aquele momento foi inesquecível pra" (35)
  - linha_atual = "ele"
- Fim → append "ele"

**Saída:**
- Linha 1: `"aquele momento foi inesquecível pra"` (35 chars)
- Linha 2: `"ele"` (3 chars)

**Avaliação:** **ANTI-PADRÃO EXATO** descrito pelo operador — linha 2 com 1 palavra isolada (3 chars vs 35). Quebra editorialmente superior: `"aquele momento foi\ninesquecível pra ele"` (18:20).

## Caso D — Gancho de 50 chars (max_linhas=2)

**Texto:** `"a noite em que Pavarotti quase perdeu a voz no meio"` (~51 chars, 11 palavras, tipo="gancho" → max_linhas=2)

**Trace:**
- Build até "a noite em que Pavarotti quase perdeu" (37) — cabe
- "a noite em que Pavarotti quase perdeu a" (39) → não cabe
  - append (37)
  - linha_atual = "a"
- Build "a voz no meio" (13) — cabe, fim
- append → 2 linhas

**Saída:**
- Linha 1: `"a noite em que Pavarotti quase perdeu"` (37)
- Linha 2: `"a voz no meio"` (13)

**Avaliação:** 37:13 (razão 2.8:1). Quebra editorialmente melhor: `"a noite em que Pavarotti\nquase perdeu a voz no meio"` (25:26).

## Caso E — Reconstituição do bug `[RC LineBreak] Texto truncado: sobrou 'esquece....'`

**Hipótese reversa**: o log emite `resto[:50]` em [claude_service.py:871](app-redator/backend/services/claude_service.py:871), onde `resto = " ".join(palavras[idx:])`. Para log começar em "esquece", a palavra `palavras[idx] = "esquece"` precisa ser aquela em que `len(novas_linhas) >= max_linhas` é disparado (linha 869).

**Texto candidato (reconstituição):** 
`"a cada nota o tenor parecia invocar uma memória diferente fazia com que você esquece do tempo lá fora enquanto ele canta"` (~120 chars, 22 palavras)

**Trace (simplificado):**
- Linha 1 construída até ~36 chars ("a cada nota o tenor parecia invocar")
- Linha 2 construída até ~36 chars ("uma memória diferente fazia com")
- Linha 3 construída até ~30 chars ("que você")
- Ao tentar adicionar próxima palavra: `teste` > 38 → fluxo entra no `else` da linha 865
  - `novas_linhas.append(linha_atual)` → 3 linhas ✓
  - Check `if len(novas_linhas) >= max_linhas:` → 3 >= 3 → TRUE
  - `resto = " ".join(palavras[idx:])` → `"esquece do tempo lá fora enquanto ele canta"`
  - Log: `[RC LineBreak] Texto truncado: sobrou 'esquece do tempo lá fora enquanto ele c...'`
  - `truncado=True; break`
- Fim: `novas_linhas[:max_linhas]` → 3 linhas
- **7 palavras de conteúdo editorial DESCARTADAS.**

**Mecanismo de falha confirmado.** Evidência:
- Linha 869: condição `len(novas_linhas) >= max_linhas` ativa a trilha de truncamento
- Linha 870: `resto` é capturado
- Linha 871: `resto[:50]` é logado
- Linha 872: `truncado=True`
- Linha 873: `break` interrompe o loop, palavras restantes são **descartadas**

**Comportamento correto editorialmente:** quando o texto excede 3 linhas × 38 chars, a função deveria (a) retornar o texto original intacto e alertar operador, (b) solicitar re-geração ao LLM, ou (c) dividir em DUAS legendas. Nunca descartar conteúdo.

## Ausência de lógica de qualidade — confirmada

### Balanceamento
- Código não calcula diferença de tamanho entre linhas. Greedy puro: `if len(teste) <= max_chars_linha: linha_atual = teste; else: flush`.
- Grep em app-redator por `balanc` retorna **apenas uma menção**, e é no prompt LLM ([generation.py:215](app-redator/backend/routers/generation.py:215): "divida em 2 linhas balanceadas com \\n"). Instrução declarativa ao LLM, não enforcer no código.

### Unidades sintáticas
- Parcial. Há early-break em pontuação (`,.;:`) quando `len(linha_atual) >= 25` ([claude_service.py:860-864](app-redator/backend/services/claude_service.py:860)). Ajuda em textos com frases curtas, mas não ajuda em frases longas (que é o caso patológico).
- Não há detecção de preposições isoladas (proibir quebra entre "a" + "voz"), artigos+substantivos, etc.

### Split em múltiplas legendas
- **Código não divide uma legenda em 2 quando excede tamanho.** Grep por `split_into_multiple|dividir|extra_legenda` em app-redator retorna **apenas menção em prompt LLM** ([rc_overlay_prompt.py:385](app-redator/backend/prompts/rc_overlay_prompt.py:385): "Se alguma dura >6s: dividir em duas ou encurtar texto"). Instrução para o LLM, não operação do código.
- Quando LLM gera legenda longa que o código não consegue wrap em 3 linhas, o código trunca (R1, R2) em vez de gerar 2 legendas.

## Algoritmo em palavras

`_enforce_line_breaks_rc` é um word-wrapper greedy com 2 comportamentos especiais:
1. **Early-break em pontuação** ([claude_service.py:860-864](app-redator/backend/services/claude_service.py:860)) se `len ≥ 25` e char final `∈ {,.;:}`
2. **Truncamento silencioso** ([claude_service.py:869-873](app-redator/backend/services/claude_service.py:869)) quando excede `max_linhas`, com log warning mas descarte de resto

Não há:
- Análise de balanceamento inter-linha
- Preferência por unidades sintáticas maiores que pontuação final
- Split da legenda em 2 quando excede
- Rejeição+regeração da legenda inteira
- Alerta em UI para operador editar manualmente
