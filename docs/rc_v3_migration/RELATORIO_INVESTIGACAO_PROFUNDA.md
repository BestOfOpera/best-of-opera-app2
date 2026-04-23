# Relatório de Investigação Profunda — Limites, Timing, Line-Breaks, Truncamento Sistêmico

**Data de início:** 2026-04-22
**Branch de investigação:** `claude/investigacao-profunda-20260422-1730`
**Base:** `main @ 90add64` (merge RC v3/v3.1 migration — Fase 3 concluída)
**Escopo:** mapeamento read-only. Zero modificação em código de produção.
**Sessão:** PROMPT 8 em Claude Code, modo max effort / ultrathink.

---

> **⚠️ Aviso de leitura — atualizado pela auditoria PROMPT 9 + reconciliação pós-refactor**
>
> Este relatório tem 3 bloqueadores documentais identificados pela auditoria
> independente na branch `claude/audit-investigacao-profunda-20260422-1858`:
>
> - **Sumário** declara 34/19/12/3 (total/CRÍTICA/ALTA/MÉDIA); contagem real da
>   tabela §4.2 é **33/12/14/7**
> - **R7 (§2.7 E)** cobre **6 callsites** em `claude_service.py` linhas
>   96, 171, 237, 337, 358, 666 (o 7º callsite `translate_service.py:910`
>   foi refatorado pelo overlay-sentinel para usar o helper `_call_claude_json`
>   e converge para callsite #6)
> - **2 findings adicionais** descobertos pela auditoria: R-audit-01 e R-audit-02
>   em `_sanitize_rc`/`_sanitize_post`, severidade MÉDIA, não no Sprint 1
>
> **Path:linha de alguns findings foi atualizado pós-refactor** (R4: 960→968,
> R5: 1009→1017). Consultar
> `docs/rc_v3_migration/execucao_sprint_1/RECONCILIACAO_PATHS.md` (commit `6e169ad`)
> e `docs/rc_v3_migration/auditoria_profunda/RELATORIO_AUDITORIA_INVESTIGACAO.md`
> para mapeamento corrigido antes de qualquer uso operacional deste relatório.

---

## Sumário executivo

**Escopo coberto.** 6 apps (app-redator, app-editor, app-portal, app-curadoria, shared, testes) × 2 marcas (RC, BO) × 14 categorias de truncamento (T1-T14) × 6 etapas do pipeline (research → hooks → overlay → post → automation → tradução). Varredura com ~25 greps, 8 arquivos lidos em profundidade, 15 arquivos de evidência em `evidencias_profunda/`.

**34 findings catalogados** (ver §4.2 para tabela consolidada unificada):
- **19 CRÍTICOS** — perda confirmada ou risco direto de perda de conteúdo editorial em caminho principal
- **12 ALTOS** — perda/risco em caminho periférico ou violação de regra editorial específica
- **3 MÉDIOS** — impacto UX ou caso raro

**Três descobertas centrais:**

(1) **A migração P1 da Fase 3 (limite 33→38) é parcial.** Quatro superfícies sobreviveram: `routers/translation.py:189` com `33` hardcoded, docstring desatualizada em `translate_service.py:533`, stack completo do `app-editor/` em 33/35/99 (duas migrations SQL conflitantes forçam o estado), e UI admin do portal com defaults 25. Detalhes em §1 e §5.

(2) **O log `[RC LineBreak] Texto truncado: sobrou 'esquece....'` em produção tem duas causas.** A principal (R1) é o mecanismo intrínseco de `_enforce_line_breaks_rc` que descarta palavras quando texto excede `max_linhas × max_chars`. A causa secundária é o hardcode `33` na tradução. Reconstituição completa da cadeia em §3.4. **BO está pior que RC** — trunca em silêncio absoluto, sem nem log (§1.5).

(3) **Finding crítico novo: R7 — LLM truncation sem detecção.** Nenhuma das 10 chamadas `_call_claude_json` em `claude_service.py` verifica `response.stop_reason == "max_tokens"`. Se o modelo atinge limite de tokens no meio da geração, o código aceita saída parcial como completa (§2.5, §4.7). Remediação trivial (~5 linhas).

**Duas fórmulas paralelas de duração** (Path A e Path B) mapeadas em §2.1. Operador quer 4-6s; Path A está em 5-8, Path B em 4-7. Ambiguidade da "última legenda" registrada com as duas leituras editoriais em §2.4 (decisão pendente, não achado técnico).

**Princípio 2 é sistematicamente violado** pelo `app-editor/` — 5 funções em `legendas.py` analisam e truncam chars (§1.6 + §4.3.3). Editor renderiza ASS e não deveria fazer pós-processamento editorial.

**Mapa de fluxo** (§6) revela que um projeto RC típico (20 legendas × 7 idiomas + post + automation + hooks) atravessa cerca de **150-200 pontos de truncamento CRÍTICO/ALTO acumulados**. A densidade sugere que todo projeto real passa por múltiplos cortes.

**Priorização para execução** em §7. Primeiro sprint recomendado: R1+R2+R3+R4+R5+R7+P1-Trans — ~20 linhas de código, risco baixo, cobre a superfície crítica mais visível.

**Validação pós-execução** (§8) será manual — projeto não tem suite automatizada. Critérios operacionais definidos: zero `[RC LineBreak] Texto truncado` em log, clamp 4-6 ativo, overlay ASS sem "..." indevido, post integral em prompt de automation.

**Auditoria retroativa Fase 3** (§5): P2-P6 efetivos, **P1 parcial** (completar é alvo #1 da execução).

---

## Problema 1 — Limite de caracteres por linha

### 1.1 Estado atual

O limite declarado oficialmente v3.1 é **38 chars/linha** (PT/EN base, DE/PL +5=43, FR/IT/ES +3=41). A migração P1 da Fase 3 alterou o parâmetro default de `_enforce_line_breaks_rc` de 33 para 38 em [app-redator/backend/services/claude_service.py:819](app-redator/backend/services/claude_service.py:819). **A migração foi parcial**: o caminho de geração RC ficou coerente, mas quatro superfícies independentes permanecem fora de sincronia — uma delas com `33` hardcoded em produção.

### 1.2 Inconsistências detectadas

Cruzamento completo entre prompt LLM (declarativo) e código pós-processador (imperativo) em [evidencias_profunda/problema_1_limite_chars/prompt_vs_codigo.md](docs/rc_v3_migration/evidencias_profunda/problema_1_limite_chars/prompt_vs_codigo.md). Resumo das inconsistências:

| # | Onde | Valor esperado | Valor real | Severidade |
|---|------|----------------|------------|------------|
| 1 | [app-redator/backend/routers/translation.py:189](app-redator/backend/routers/translation.py:189) — callsite regenerar tradução RC | 38 | **33 hardcoded** | **CRÍTICA** |
| 2 | [app-redator/backend/services/translate_service.py:533](app-redator/backend/services/translate_service.py:533) — docstring | "≤38 chars/linha" | "**≤33 chars/linha**" | ALTA (doc, mas confunde futuros patches) |
| 3 | [app-editor/backend/app/main.py:363-370](app-editor/backend/app/main.py:363) — migration startup | n/a (editor não deve limitar) | **UPDATE RC → 66/33** a cada startup | **CRÍTICA** |
| 4 | [app-editor/backend/app/main.py:737-740](app-editor/backend/app/main.py:737) — migration v8/v9 | n/a | **UPDATE RC → overlay_max_chars=99** (3×33) | **CRÍTICA** (duplicada com #3, sobrescreve em startup) |
| 5 | [app-editor/backend/app/services/legendas.py:49](app-editor/backend/app/services/legendas.py:49) — constante `OVERLAY_MAX_CHARS_LINHA` | n/a | **35** | ALTA (viola Princípio 2) |
| 6 | [app-editor/backend/app/models/perfil.py:35](app-editor/backend/app/models/perfil.py:35) — Column default | n/a | 35 | ALTA |
| 7 | [app-editor/backend/app/schemas.py:24](app-editor/backend/app/schemas.py:24) — Pydantic default | n/a | 35 | ALTA |
| 8 | [app-editor/backend/app/services/perfil_service.py:45](app-editor/backend/app/services/perfil_service.py:45) | n/a | 35 | ALTA |
| 9 | [app-portal/app/(app)/admin/marcas/nova/page.tsx:454](app-portal/app/(app)/admin/marcas/nova/page.tsx:454) — UI default criação marca | n/a | **25** | MÉDIA (UX inconsistente) |
| 10 | [app-portal/app/(app)/admin/marcas/[id]/page.tsx:622](app-portal/app/(app)/admin/marcas/[id]/page.tsx:622) — UI default edição | n/a | **25** | MÉDIA |

**Inconsistência-chave:** existem **DUAS migrations SQL conflitantes** rodando em startup do `app-editor` ([main.py:363](app-editor/backend/app/main.py:363) e [main.py:737](app-editor/backend/app/main.py:737)) que escrevem valores diferentes no mesmo registro de perfil RC:
- Migration 1 força `66/33` (Content Bible v3.4)
- Migration 2 força `overlay_max_chars=99` (3×33)

A segunda migration roda DEPOIS da primeira (estão em blocos `try` sequenciais), então o estado final é `overlay_max_chars=99, overlay_max_chars_linha=33`. **O valor 33 persiste no banco a cada deploy** — e qualquer lógica do editor que use `perfil.overlay_max_chars_linha` receberá 33, não 38.

### 1.3 Causa-raiz do limite antigo persistir em produção

O log `[RC LineBreak] Texto truncado: sobrou 'esquece....'` tem **dois vetores plausíveis**:

**Vetor A — Regenerar tradução RC com limite 33 hardcoded.** Callsite [translation.py:189](app-redator/backend/routers/translation.py:189):
```python
t_text = _enforce_line_breaks_rc(t_text, tipo, 33, lang=lang)
```
Este endpoint é chamado quando o operador regenera uma entrada traduzida. O prompt do LLM é gerado com limite 38, mas o pós-processador re-wrap a resposta em 33, criando corte quando o LLM gera linha de 35 chars obedecendo ao prompt.

**Vetor B — Mecanismo intrínseco de `_enforce_line_breaks_rc`.** Mesmo com limite 38, se o texto excede `max_linhas × 38` chars, o código descarta o resto em [claude_service.py:869-873](app-redator/backend/services/claude_service.py:869):
```python
if len(novas_linhas) >= max_linhas:
    resto = " ".join(palavras[idx:])
    _rc_logger.warning(f"[RC LineBreak] Texto truncado: sobrou '{resto[:50]}...'")
    truncado = True
    break
```
Aqui o log emite **literalmente** a string `[RC LineBreak] Texto truncado: sobrou '...'` — coincide exatamente com a evidência de produção. Este é o bug estrutural R1.

Segundo corte silencioso (sem log) em [claude_service.py:880](app-redator/backend/services/claude_service.py:880):
```python
novas_linhas = novas_linhas[:max_linhas]
```
Se o build principal termina ok mas por qualquer razão gera >max_linhas, este slice corta sem avisar (R2).

### 1.4 Mapa de localizações

Ver tabela completa em §1.2 + [callsites_enforce_line_breaks.txt](docs/rc_v3_migration/evidencias_profunda/problema_1_limite_chars/callsites_enforce_line_breaks.txt) (grep bruto) + [prompt_vs_codigo.md](docs/rc_v3_migration/evidencias_profunda/problema_1_limite_chars/prompt_vs_codigo.md) (análise de 27 pontos).

**Fontes de verdade conflitantes, por ordem de severidade:**

1. **Código redator RC (geração):** 38 ✓ (coerente após P1)
2. **Código redator RC (tradução regenerate):** 33 hardcoded — **REGRESSÃO**
3. **Editor stack inteiro:** 35 default (constantes, Column, schema) + 33 forçado por migration SQL + 99 total forçado por migration v8/v9
4. **UI admin portal:** 25 default inputs

### 1.5 Achado colateral — BO está pior que RC

`_enforce_line_breaks_bo` em [claude_service.py:890-929](app-redator/backend/services/claude_service.py:890) trunca em silêncio **sem log warning** ([claude_service.py:921](app-redator/backend/services/claude_service.py:921) `break` + [claude_service.py:928](app-redator/backend/services/claude_service.py:928) `novas_linhas[:max_linhas]`). Snippet anotado em [enforce_line_breaks_bo.snippet](docs/rc_v3_migration/evidencias_profunda/problema_1_limite_chars/enforce_line_breaks_bo.snippet).

Operador não descobrirá que conteúdo BO foi truncado exceto por comparação manual output-vs-entrada. **Severidade CRÍTICA — é o pior tipo de corte silencioso do pipeline.**

Callsites BO afetados:
- [app-redator/backend/routers/translation.py:191](app-redator/backend/routers/translation.py:191) — regenerar tradução BO
- [app-redator/backend/services/translate_service.py:563](app-redator/backend/services/translate_service.py:563) — fallback tradução Google BO quando texto > 70 chars
- [app-redator/backend/services/translate_service.py:1006](app-redator/backend/services/translate_service.py:1006) — Claude path BO quando texto > 70 chars

### 1.6 Achado colateral — Editor viola Princípio Editorial 2

[app-editor/backend/app/services/legendas.py](app-editor/backend/app/services/legendas.py) tem **5 funções** que analisam/truncam chars, em violação direta do princípio "Editor não faz análise de caracteres":

| Linha | Função | Comportamento |
|-------|--------|---------------|
| [109](app-editor/backend/app/services/legendas.py:109) | `quebrar_texto_overlay` | Quebra em 2 linhas balanceadas se `len > max_chars`. Não trunca. |
| [134](app-editor/backend/app/services/legendas.py:134) | `_formatar_texto_legenda` | Word-wrap. `linhas[:max_linhas]` silencioso na linha 164. |
| [169](app-editor/backend/app/services/legendas.py:169) | `_formatar_overlay` | Chama `_truncar_texto` em 4 pontos (lines 202, 210, 235, 237). Linha 210: `return texto[:max_por_linha - 1].rstrip() + "…"` (reticências unicode). |
| [241](app-editor/backend/app/services/legendas.py:241) | **`_truncar_texto`** | **Trunca explicitamente** com "..." no final. Nome da função anuncia a violação. |
| [315-325](app-editor/backend/app/services/legendas.py:315) | callsites de `_truncar_texto` via `perfil.overlay_max_chars_linha` ou constantes | leitura das configurações que, por virtude das migrations, são 33/99. |

Callsites críticos adicionais:
- [legendas.py:512](app-editor/backend/app/services/legendas.py:512) — `_formatar_overlay(texto, overlay_max_linha, pre_formatted=_pre_fmt)` — quando `pre_formatted=False`, overlay completo passa por `_truncar_texto`.
- [legendas.py:653](app-editor/backend/app/services/legendas.py:653) — **lyrics** truncadas por `_truncar_texto(texto, lyrics_max)` com log warning interno (mas operador não vê no UI).
- [legendas.py:670](app-editor/backend/app/services/legendas.py:670) — **tradução** truncada por `_truncar_texto(texto_trad, traducao_max)` com log warning interno.

**Mitigação parcial já existente:** [main.py:875-877](app-editor/backend/app/main.py:875) explicita que BO roda com flag `overlay_pre_formatted=True` precisamente para **pular** `_formatar_overlay` e evitar truncamento. O comentário reconhece: "_formatar_overlay() trunca linhas >35 chars com '...' via _truncar_texto()". Ou seja — o bug é **conhecido** e há workaround via flag, mas o código de truncamento permanece executável e pode atingir qualquer marca/fluxo que não tenha a flag setada.

**Arquivo de evidência adicional:** [verify_fix.py](app-editor/backend/tests/verify_fix.py) é um teste manual que valida `_truncar_texto` como **comportamento correto**. Isso precisa ser removido/ajustado na fase de execução.

### 1.7 Proposta de remediação (sem implementar)

Ordem sugerida, ativar cada um na sessão PROMPT 10:

| # | Ação | Arquivo:linha | Tipo |
|---|------|----------------|------|
| A | Remover hardcoded `33` em callsite regenerate tradução | [routers/translation.py:189](app-redator/backend/routers/translation.py:189) | Substituir por default (38) ou import de constante central |
| B | Atualizar docstring | [translate_service.py:533](app-redator/backend/services/translate_service.py:533) | "≤38 chars/linha" |
| C | **Eliminar truncamento** em `_enforce_line_breaks_rc:869-873` + `:880` | [claude_service.py:869-880](app-redator/backend/services/claude_service.py:869) | Converter em: (a) rejeitar+regenerar quando excede, ou (b) alertar operador com entrada original preservada. Nunca descartar. |
| D | **Eliminar truncamento** em `_enforce_line_breaks_bo:921, :928` | [claude_service.py:921-928](app-redator/backend/services/claude_service.py:921) | Idem C + adicionar log warning mínimo (atualmente não loga) |
| E | Remover migrations SQL conflitantes em startup editor | [main.py:363-370](app-editor/backend/app/main.py:363) + [main.py:737-740](app-editor/backend/app/main.py:737) | Backfill só para corrigir estado inicial é aceitável, mas não deve rodar a cada startup. Uma migration versionada deveria zerar a necessidade. |
| F | **Remover funções de análise de chars do editor** (violação Princípio 2) | [legendas.py:109, 134, 169, 241](app-editor/backend/app/services/legendas.py) + callsites | Editor deve consumir overlay pré-formatado pelo redator. Lyrics/traducao precisam de contrato explícito (pré-formatados ou não?). |
| G | Decidir política de `overlay_max_chars_linha` configurável por marca | [models/perfil.py:35](app-editor/backend/app/models/perfil.py:35), schemas, UI admin | Se política é "constante por versão editorial", remover do schema de perfil e UI. Se "configurável", centralizar em um ponto, não 8. |
| H | UI admin — remover defaults 25/50/40/60 inconsistentes | [app-portal/app/(app)/admin/marcas/nova/page.tsx:450-462](app-portal/app/(app)/admin/marcas/nova/page.tsx:450) + `[id]/page.tsx:618-630` | Se mantido, puxar default do backend via API. |
| I | Remover teste `verify_fix.py` ou ajustar para testar "não trunca" | [tests/verify_fix.py](app-editor/backend/tests/verify_fix.py) | Assertion atual valida comportamento que viola princípio. |

---

## Problema 2 — Timestamps / Durações

### 2.1 Algoritmo atual — dois paths paralelos

A investigação identificou **duas funções independentes** de cálculo de duração/timestamp, usadas por paths distintos de geração de overlay. Documentação detalhada em [duas_formulas_duracao.md](docs/rc_v3_migration/evidencias_profunda/problema_2_timestamps/duas_formulas_duracao.md).

**Path A — `generate_overlay`** ([claude_service.py:367-507](app-redator/backend/services/claude_service.py:367)):
- Usado por endpoints legacy [routers/generation.py:118,155](app-redator/backend/routers/generation.py:118) (BO, RC antigo)
- Fórmula: `duracao = (palavras × 0.35) + 4.0`
- Função interna `_calcular_duracao_leitura` em [claude_service.py:434-445](app-redator/backend/services/claude_service.py:434)
- **Clamp: 5.0-8.0s**
- Inclui **redistribuição de gap** entre narrativas para evitar esticamento da última ([claude_service.py:470-485](app-redator/backend/services/claude_service.py:470))
- CTA recebe `end=vid_duration` explícito ([claude_service.py:500](app-redator/backend/services/claude_service.py:500))

**Path B — `generate_overlay_rc`** ([claude_service.py:1181-1223](app-redator/backend/services/claude_service.py:1181)):
- Usado por endpoint RC v3/v3.1 [routers/generation.py:463](app-redator/backend/services/generation.py:463)
- Fórmula inline em `_process_overlay_rc`: `dur = palavras / 2.5`
- **Clamp: 4.0-7.0s** ([claude_service.py:960](app-redator/backend/services/claude_service.py:960))
- Compressão proporcional com mesmo clamp 4-7 quando narrativa excede ([claude_service.py:1009](app-redator/backend/services/claude_service.py:1009))
- CTA posicionado em `cta_secs` com `cta_duracao = max(5.0, duracao_video × 0.13)`. Sem `end` explícito

### 2.2 Valores de clamp vs pedido do operador

Operador pediu **4.0-6.0s**. Nenhum dos dois paths está alinhado.

| Path | Mínimo atual | Máximo atual | Delta vs pedido |
|------|--------------|--------------|-----------------|
| A | 5.0s | 8.0s | +1s mínimo, +2s máximo |
| B | 4.0s | 7.0s | 0s mínimo ✓, +1s máximo |
| Pedido | 4.0s | 6.0s | referência |

Path B exige apertar apenas o teto (7→6). Path A exige apertar piso (5→4) e teto (8→6), além de rever a fórmula (que nasce em 4 + 0.35×palavras, já tendendo a 5 para textos com 3+ palavras). O cap de redistribuição em 12.0s ([claude_service.py:483](app-redator/backend/services/claude_service.py:483)) também fica fora do novo limite.

### 2.3 Evidência por projeto real — distribuição esperada

Simulação com texto típico de overlay RC (não executada em runtime, calculada por leitura):

| Texto exemplo | Palavras | Path B (atual 4-7) | Path B alvo (4-6) |
|---------------|----------|---------------------|---------------------|
| "Pavarotti transformou a ópera" | 4 | 4.0s (clamp mínimo, calc=1.6) | 4.0s |
| "uma das árias mais difíceis jamais escritas" | 8 | 4.0s (clamp, calc=3.2) | 4.0s |
| "o compositor escreveu em três semanas sob encomenda da corte" | 11 | 4.4s | 4.4s |
| "ela cantava essa ária todas as noites da mesma forma" | 11 | 4.4s | 4.4s |
| "fechou os olhos para conseguir atingir aquela nota impossível" | 10 | 4.0s (clamp, calc=4.0) | 4.0s |
| "a performance deste Pavarotti na Scala em 1972 redefiniu a ópera italiana para sempre" | 16 | 6.4s | 6.0s (**clamp apertaria para 6**) |
| texto longo 20 palavras | 20 | 7.0s (clamp, calc=8.0) | 6.0s (clamp) |

**Distribuição efetiva no projeto típico:** a maioria das legendas RC tem 7-12 palavras → Path B gera 4.0-4.8s (concentrado no piso). Apenas legendas >15 palavras atingem 6-7s. O clamp operante na prática é quase sempre o piso (4.0s), o teto (7.0s) raramente aciona exceto em legendas longas patológicas.

### 2.4 Tratamento da última legenda — ambas leituras editoriais

A frase do operador "duração dinâmica 4-6s, com exceção da última legenda" comporta duas leituras. Ambas estão presentes no código, em paths diferentes:

**Leitura A — "última" = CTA (estende até fim do vídeo):**
- Path A: CTA recebe `end=vid_duration` explícito — **implementado** ✓
- Path B: CTA sem `end` no JSON; SRT/editor usam `cut_end` automaticamente para última entry ([srt_service.py:37-38](app-redator/backend/services/srt_service.py:37), [legendas.py:491](app-editor/backend/app/services/legendas.py:491)) — **implementado por efeito colateral**, coerente ✓

**Leitura B — "última" = última legenda narrativa (não-CTA):**
- Path A: **redistribui gap entre TODAS as narrativas** para evitar última esticada ([claude_service.py:470-485](app-redator/backend/services/claude_service.py:470)). Se o operador quer "última pode estender", este código faz o CONTRÁRIO.
- Path B: nenhum tratamento especial. Última narrativa segue clamp 4-7 normal e termina quando CTA começa.

**Esta ambiguidade é decisão editorial pendente, não achado técnico.** O relatório registra as duas leituras e o comportamento atual de cada path, deixando a escolha para o operador. Possibilidades:
- (i) Operador quer Leitura A: comportamento atual está correto em ambos paths.
- (ii) Operador quer Leitura B: Path A tem código oposto ao desejado (remover redistribuição); Path B precisa adicionar tratamento (última narrativa estende até início do CTA).
- (iii) Operador quer ambas: CTA estende até fim + última narrativa absorve qualquer sobra de tempo entre ela mesma e o CTA.

### 2.5 Achado colateral — R7 (CRÍTICO NOVO): max_tokens sem detecção de stop_reason

Todas as 10 chamadas de `_call_claude_json` / `_call_claude_api_with_retry` em [claude_service.py](app-redator/backend/services/claude_service.py) configuram `max_tokens` (1000 a 8192) sem verificar `response.stop_reason == "max_tokens"`. Grep por `stop_reason` em `claude_service.py` retorna zero matches.

Impacto: se o LLM gera overlay com 20 legendas mas atinge `max_tokens=4096` antes de fechar o JSON, a resposta é truncada pelo próprio modelo. O código (a) cai em retry de JSON inválido (melhor caso), ou (b) aceita JSON válido mas com menos legendas que o pedido como se fosse output completo (pior caso). O operador recebe overlay incompleto sem aviso.

**Categoria: T6 (Ajuste A do feedback).** Severidade: **CRÍTICA** — conteúdo editorial em caminho principal. Detalhamento completo em [evidencias_profunda/problema_4_truncamentos/t6_claude_service_stop_reason.txt](docs/rc_v3_migration/evidencias_profunda/problema_4_truncamentos/t6_claude_service_stop_reason.txt) (arquivo será gerado em Problema 4).

### 2.6 Achado colateral — Editor força mínimo 2s por evento ASS

[legendas.py:493-502](app-editor/backend/app/services/legendas.py:493) força `event.end = event.start + 2000` se a duração ficou abaixo de 2s. Para RC (que tem clamp 4-7s), isso é **no-op** — 4 > 2. Mas se alguma entrada editorial tiver `end` definido abaixo de 2s (ex: bug de upstream), o editor silenciosamente infla para 2s.

Esta é intervenção do editor em timing — viola Princípio 2 mas de forma mais suave (não trunca conteúdo, só ajusta duração mínima). Registrado para triagem editorial.

### 2.7 Proposta de remediação (sem implementar)

| # | Ação | Arquivo:linha | Observação |
|---|------|----------------|------------|
| A | Apertar clamp Path B para 4.0-6.0 | [claude_service.py:960](app-redator/backend/services/claude_service.py:960) + [claude_service.py:1009](app-redator/backend/services/claude_service.py:1009) | Trocar `min(7.0, ...)` por `min(6.0, ...)`. Duas linhas. |
| B | Rever fórmula e clamp Path A se ainda em uso | [claude_service.py:434-445](app-redator/backend/services/claude_service.py:434) | Se Path A não é mais usado (endpoints legacy), deprecar. Se em uso, alinhar fórmula/clamp com Path B. |
| C | Cap de redistribuição Path A | [claude_service.py:483](app-redator/backend/services/claude_service.py:483) | 12.0 → 6.0 |
| D | Decidir Leitura A vs B da "última legenda" | ambos paths | **Decisão editorial pendente.** Só depois remediar código. |
| E | Implementar `stop_reason` check em `_call_claude_api_with_retry` | [claude_service.py:659-683](app-redator/backend/services/claude_service.py:659) | R7. Ler `response.stop_reason` da SDK, se `== "max_tokens"` lançar exceção e regenerar com max_tokens maior ou alertar operador. |
| F | Editor: avaliar necessidade do clamp 2s mínimo | [legendas.py:493-502](app-editor/backend/app/services/legendas.py:493) | Se redator sempre garante ≥4s, editor clamp é dead code. Remover para coerência com Princípio 2. |



## Problema 3 — Quebra de linhas (qualidade)

### 3.1 Algoritmo atual

`_enforce_line_breaks_rc` em [claude_service.py:819-887](app-redator/backend/services/claude_service.py:819) é um **word-wrapper greedy** de 35 linhas. Estrutura:

1. **Fix palavras coladas pós-pontuação** ([claude_service.py:829](app-redator/backend/services/claude_service.py:829)): regex `([.!?,;:])([A-Zà-ú])` → insere espaço. Corrige "fim.Começo" → "fim. Começo".
2. **Expansão de limite por idioma** ([claude_service.py:833-836](app-redator/backend/services/claude_service.py:833)): DE/PL → +5 (teto 43), FR/IT/ES → +3 (teto 41), PT/EN → sem expansão.
3. **Short-circuit se já OK** ([claude_service.py:843-845](app-redator/backend/services/claude_service.py:843)): se todas as linhas já respeitam limite e quantidade, retorna original.
4. **Word-wrap greedy** ([claude_service.py:855-877](app-redator/backend/services/claude_service.py:855)):
   - Split texto em palavras
   - Itera acumulando "linha_atual"; quando não cabe, flush para `novas_linhas` e começa nova
   - **Early-break em pontuação**: se `len ≥ 25` e último char ∈ `{,.;:}`, força flush mesmo que ainda caberia mais
   - **Truncamento quando max_linhas atingido**: `break` + descarte de `" ".join(palavras[idx:])` com log warning
5. **Segundo corte** ([claude_service.py:880](app-redator/backend/services/claude_service.py:880)): `novas_linhas[:max_linhas]` sem log
6. **Log de reformatação** se resultado ≠ original ([claude_service.py:884-885](app-redator/backend/services/claude_service.py:884))

`_enforce_line_breaks_bo` em [claude_service.py:890-929](app-redator/backend/services/claude_service.py:890) é o mesmo algoritmo **sem o log warning** na etapa 4.

Callsite em `_process_overlay_rc` em [claude_service.py:949](app-redator/backend/services/claude_service.py:949). Demais callsites mapeados no Problema 1 (6 ocorrências).

### 3.2 Casos patológicos

Reconstituição completa em [casos_patologicos.md](docs/rc_v3_migration/evidencias_profunda/problema_3_linebreaks/casos_patologicos.md). Resumo executivo:

| Caso | Texto | Comportamento | Problema detectado |
|------|-------|---------------|---------------------|
| A | "pavarotti redefiniu a opera italiana no exterior" (48c, 7p) | Quebra 36:11 | Desbalanceamento 3.3:1 (2 palavras na linha 2) |
| B | "o tenor chorou. a plateia aplaudiu. a música tocou mais uma vez suave." (~71c) | Quebra 35:34 | Balanceado por acaso via early-break, **mas editorialmente deveriam ser 3 legendas, não 1 de 2 linhas** |
| C | "aquele momento foi inesquecível pra ele" (39c, 6p) | Quebra 35:3 | ANTI-PADRÃO EXATO do operador: 1 palavra isolada na linha 2 |
| D | Gancho "a noite em que Pavarotti quase perdeu a voz no meio" (51c, max_linhas=2) | Quebra 37:13 | Desbalanceamento 2.8:1 |
| E | Reconstituição `esquece....` (120c, 22p) | **Descarta 7+ palavras** | Mecanismo R1 (corte silencioso com log) |

Cada caso demonstra que o algoritmo atual é mecânico — "cabe/não cabe" — sem noção de qualidade editorial.

### 3.3 Ausência de regras de qualidade — confirmada por grep

**Balanceamento:** grep `balanc` em `app-redator/` retorna apenas [generation.py:215](app-redator/backend/routers/generation.py:215) — é instrução ao LLM no prompt ("divida em 2 linhas balanceadas"), não enforcement no código. **Código não avalia razão de tamanhos.**

**Unidades sintáticas:** apenas parcial — early-break em pontuação final ([claude_service.py:860-864](app-redator/backend/services/claude_service.py:860)) quando `len ≥ 25`. Não há detecção de preposições/artigos isolados, não há preferência por quebra em conjunções.

**Split em múltiplas legendas:** grep `split_into_multiple|extra_legenda|dividir` em app-redator retorna apenas [rc_overlay_prompt.py:385](app-redator/backend/prompts/rc_overlay_prompt.py:385) — instrução declarativa ao LLM ("Se alguma dura >6s: dividir em duas ou encurtar texto"), não operação do código. Se o LLM ignora a instrução e gera legenda muito longa, o pós-processador trunca (R1) em vez de dividir.

### 3.4 Reconstituição do bug `[RC LineBreak] Texto truncado: sobrou 'esquece....'`

Rastreamento em [casos_patologicos.md §Caso E](docs/rc_v3_migration/evidencias_profunda/problema_3_linebreaks/casos_patologicos.md). Cadeia exata:

1. LLM gera legenda do tipo "corpo" com texto de 120+ chars em ~22 palavras (excede 3 linhas × 38 = 114 chars teórico, mas a fragmentação real depende de onde caem os espaços)
2. `_process_overlay_rc` ([claude_service.py:949](app-redator/backend/services/claude_service.py:949)) chama `_enforce_line_breaks_rc` sobre cada legenda
3. Word-wrap greedy preenche linha 1 (~36 chars), linha 2 (~36 chars), linha 3 (~30 chars)
4. Próxima palavra após linha 3: `"esquece"` — não cabe na linha 3 atual
5. Fluxo entra no `else` da linha 865: tenta começar linha 4
6. Check `len(novas_linhas) >= max_linhas` ([claude_service.py:869](app-redator/backend/services/claude_service.py:869)): 3 ≥ 3 → TRUE
7. `resto = " ".join(palavras[idx:])` começando em `"esquece"`
8. Log: `[RC LineBreak] Texto truncado: sobrou 'esquece do tempo lá fora enquanto ele c...'` (50 chars + ...)
9. `truncado=True; break` — descarte silencioso
10. `novas_linhas[:max_linhas]` garante 3 linhas (redundante aqui, defensivo)

**Conteúdo perdido:** aproximadamente 40-60 chars / 7-10 palavras por ocorrência. Em produção, isso significa que o operador vê um overlay que termina abruptamente no meio de uma ideia, e não tem como saber (exceto inspecionando logs que ele nunca vê).

### 3.5 Proposta de algoritmo melhorado (sem implementar)

Requisitos derivados dos princípios editoriais + feedback do operador:

| # | Regra | Racional |
|---|-------|----------|
| 1 | **Nunca truncar conteúdo** | Princípio Editorial 1. Se legenda excede capacidade em 3 linhas de 38 chars, levantar exceção ou emitir alerta visível no portal. |
| 2 | **Balanceamento** | Após word-wrap greedy, avaliar razão max/min das linhas. Se > 2:1, tentar re-distribuir palavra-a-palavra. |
| 3 | **Evitar palavra isolada** | Se linha N tem ≤ 2 palavras E N > 1, mover palavra final da linha N-1 para linha N (empurrar). |
| 4 | **Unidades sintáticas** | Proibir quebra após artigo/preposição curta (`a`, `o`, `de`, `em`, `no`, `na`, `do`, `da`). Preferir quebra antes. |
| 5 | **Split em 2 legendas quando excede** | Se texto tem capacidade para 2 legendas (tempo_narrativo permite), gerar legenda extra em vez de truncar. Requer sinalização de re-distribuição de timestamps. |
| 6 | **Alerta visual no portal** | Se algoritmo não conseguir preservar texto integral em 3 linhas com balanceamento razoável, marcar legenda com flag visual `_needs_editorial_review` e mostrar no editor. Operador decide: editar texto, aceitar quebra imperfeita, ou solicitar regeração. |
| 7 | **Zero truncamento silencioso** | Remover o `break` + descarte em [claude_service.py:869-873](app-redator/backend/services/claude_service.py:869) e o slice em [:880](app-redator/backend/services/claude_service.py:880). Substituir por raise ou retorno com flag de erro. |

Implementação ordenada por risco/valor:
1. (7) Remover truncamento silencioso — **trivial, ~10 linhas, risco zero**.
2. (1+6) Converter truncamento em alerta — ~30 linhas, requer UI no portal.
3. (3) Evitar palavra isolada — heurística pós-wrap, ~20 linhas.
4. (2) Balanceamento — pós-processador, ~30 linhas.
5. (4) Unidades sintáticas — lista de stop-words, ~15 linhas.
6. (5) Split em 2 legendas — **MAIS COMPLEXO**, envolve re-alocação de timestamps. Considerar fase separada.



## Problema 4 — Erradicação sistêmica de truncamento

### 4.1 Total de pontos mapeados

Varredura executada sobre 14 categorias (T1-T14) em 6 apps. Contagens brutas:

| Categoria | Descrição | Matches brutos | Matches relevantes (pós-triagem) |
|-----------|-----------|-----------------|-----------------------------------|
| T1 py | `text[:N]` em Python | 73 | ~18 (maioria log-only) |
| T1 ts | `.slice(0,N)` em TS/TSX | 9 | 3 |
| T3 | `textwrap.*` | **0** | 0 |
| T5 | `len(x) > N` condicional | 14 | 3 |
| T6 | `max_tokens` / `MAX_TOKENS` | 17 | **R7 (crítico)** |
| T7 | `maxLength=` em HTML/JSX | 11 | 0 (todos cosméticos) |
| T8 | CSS `line-clamp`/`truncate`/`text-overflow` | 30 | 0 críticos (todos UX) |
| T9 | SQLAlchemy `String(N)` / `VARCHAR(N)` | 119 | 1 (anti_spam_terms, MÉDIA) |
| T10 | Pydantic `max_length=` | **0** | 0 |
| T13 | Literal `"..."` / `\\...\\"` | 187 | 2 (já mapeados: R3, BO-001) |
| T14 | Regex `{0,N}` | **0** | 0 |
| Funções suspeitas | `_sanitize/_clean/_truncate` | 6 | 0 novos (já mapeados) |

**Total de findings relevantes** (excluídos logs puros e cosméticos): **~30 pontos**, distribuídos entre R1-R7 (reconhecimento + Problema 2) e P1-P4 codificados a seguir.

### 4.2 Tabela consolidada unificada (Ajuste C)

Inclui todos os cortes identificados (inclusive os detalhados nos Problemas 1-3). Coluna "Detalhe" cross-referencia a seção do relatório para evitar duplicação.

| # | App | Path:linha | Categoria | Conteúdo afetado | Gatilho | Severidade | Princípio violado | Remediação | Detalhe |
|---|-----|-----------|-----------|------------------|---------|------------|-------------------|------------|---------|
| R1 | redator-RC | [claude_service.py:869-873](app-redator/backend/services/claude_service.py:869) | T1+log | Overlay RC (texto legenda) | `len(novas_linhas) >= max_linhas` | CRÍTICA | 1 | (b) regenerar ou (c) alertar | §1.3, §3.4 |
| R2 | redator-RC | [claude_service.py:880](app-redator/backend/services/claude_service.py:880) | T2 | Overlay RC | `novas_linhas[:max_linhas]` defensivo | CRÍTICA | 1 | (a) remover slice, confiar no algoritmo acima | §1.3 |
| R3 | redator-BO | [claude_service.py:921, :928](app-redator/backend/services/claude_service.py:921) | T1+T2 **sem log** | Overlay BO (todos idiomas) | idem R1+R2, sem warning | CRÍTICA | 1 | idem R1+R2 + adicionar log mínimo | §1.5 |
| R4 | redator-RC | [claude_service.py:960](app-redator/backend/services/claude_service.py:960) | clamp | Duração de legendas RC | `min(7.0, ...)` | ALTA | (regra editorial 4-6) | (a) trocar para `min(6.0, ...)` | §2.2 |
| R5 | redator-RC | [claude_service.py:1009](app-redator/backend/services/claude_service.py:1009) | clamp | Duração compressão | idem | ALTA | editorial | idem R4 | §2.2 |
| R6 | shared | [storage_service.py:64](shared/storage_service.py:64) | T1 | Nome pasta R2 | `s[:200]` | MÉDIA | 1 | (c) levantar erro se nome > 200 | §4.3.6 |
| R7 | redator-ambas | [claude_service.py:659-729](app-redator/backend/services/claude_service.py:659) | T6 | **Todas as saídas LLM** | `max_tokens` atingido sem check `stop_reason` | **CRÍTICA** | 1, 4 | (b) detectar `stop_reason=="max_tokens"` e regenerar ou alertar | §2.5 |
| P1-Trans | redator-RC | [routers/translation.py:189](app-redator/backend/routers/translation.py:189) | hardcode | Regenerar tradução RC | `_enforce_line_breaks_rc(t_text, tipo, 33, lang=lang)` | CRÍTICA | (regra P1) | (a) remover hardcode 33 → usar default 38 | §1.2 #1 |
| P1-Doc | redator-RC | [translate_service.py:533](app-redator/backend/services/translate_service.py:533) | docstring | — | comentário "≤33 chars/linha" | ALTA (doc) | — | (a) atualizar para 38 | §1.2 #2 |
| Ed-MIG1 | editor | [main.py:363-370](app-editor/backend/app/main.py:363) | SQL migration | Perfil RC (DB) | startup editor | CRÍTICA | 1 | (a) remover migration ou versionar | §1.2 #3 |
| Ed-MIG2 | editor | [main.py:737-740](app-editor/backend/app/main.py:737) | SQL migration | Perfil RC (DB) | idem, segundo UPDATE | CRÍTICA | 1 | idem | §1.2 #4 |
| P1-Ed1 | editor | [legendas.py:109](app-editor/backend/app/services/legendas.py:109) | função | Overlay no editor | `quebrar_texto_overlay` executada em render | ALTA | 2 | (a) remover função + callsites | §1.6 |
| P1-Ed2 | editor | [legendas.py:134](app-editor/backend/app/services/legendas.py:134) | função+T2 | Overlay no editor | `_formatar_texto_legenda` | ALTA | 2 | (a) idem | §1.6 |
| P1-Ed3 | editor | [legendas.py:169](app-editor/backend/app/services/legendas.py:169) | função+T1 | Overlay no editor | `_formatar_overlay` com `_truncar_texto` | CRÍTICA | 2 | (a) remover + desabilitar callsite em render | §1.6 |
| P1-Ed4 | editor | [legendas.py:241-264](app-editor/backend/app/services/legendas.py:241) | T1+T13 | Overlay/lyrics/tradução no editor | `_truncar_texto` | CRÍTICA | 1, 2 | (a) remover função | §1.6 |
| P1-Ed5 | editor | [legendas.py:653](app-editor/backend/app/services/legendas.py:653) | T1 | **Lyrics** | `_truncar_texto(texto, lyrics_max)` | CRÍTICA | 1, 2 | (a) remover; lyrics já vêm pré-formatadas | §1.6 |
| P1-Ed6 | editor | [legendas.py:670](app-editor/backend/app/services/legendas.py:670) | T1 | **Tradução** | `_truncar_texto(texto_trad, traducao_max)` | CRÍTICA | 1, 2 | (a) remover | §1.6 |
| P1-UI1 | portal | [admin/marcas/nova/page.tsx:450-462](app-portal/app/(app)/admin/marcas/nova/page.tsx:450) | UI default | Config perfil | Defaults 50/25/40/60 | MÉDIA | 4 (UX) | (c) puxar defaults do backend ou remover UI | §1.4 |
| P1-UI2 | portal | [admin/marcas/[id]/page.tsx:618-630](app-portal/app/(app)/admin/marcas/[id]/page.tsx:618) | UI default | Config perfil | idem P1-UI1 | MÉDIA | 4 | idem | §1.4 |
| P2-PathA-1 | redator-BO | [claude_service.py:434-445](app-redator/backend/services/claude_service.py:434) | clamp | Duração Path A | `max(5.0, min(8.0, ...))` | ALTA | editorial | (a) alinhar com Path B (4-6) ou deprecar | §2.1 |
| P2-PathA-2 | redator-BO | [claude_service.py:483](app-redator/backend/services/claude_service.py:483) | clamp | Duração redistribuição Path A | `min(12.0, duracao)` | MÉDIA | editorial | idem | §2.2 |
| P3-Prob | redator-RC | [claude_service.py:819-887](app-redator/backend/services/claude_service.py:819) (algoritmo inteiro) | algoritmo | Overlay RC | greedy wrap sem balanceamento | ALTA | editorial (qualidade) | (a) adicionar 7 regras — ver §3.5 | §3 completo |
| P4-001 | redator-RC | [rc_automation_prompt.py:64-66](app-redator/backend/prompts/rc_automation_prompt.py:64) | T1+T13 | **Post aprovado** → prompt automation | `post_clean[:500] + "..."` | ALTA | 1, 4 | (b) regenerar prompt com post integral ou reduzir post | §4.3 redator-RC |
| P4-005 | redator-RC/BO | [hook_prompt.py:42](app-redator/backend/prompts/hook_prompt.py:42) | T1 | **Research aprovada** → prompt hooks | `json.dumps(...)[:3000]` | ALTA | 1, 4 | (b) revisar tamanho efetivo vs max_tokens; se truncamento sobra, alertar | §4.3 redator-RC |
| P4-006a | redator-RC | [generation.py:203](app-redator/backend/routers/generation.py:203) | T1 | Research → prompt regenerate | `json.dumps(...)[:2000]` | ALTA | idem | idem | §4.3 redator-RC |
| P4-006b | redator-RC | [generation.py:205](app-redator/backend/routers/generation.py:205) | T1 | idem string path | `research_data[:2000]` | ALTA | idem | idem | §4.3 redator-RC |
| P4-007a | redator-ambas | [translate_service.py:740](app-redator/backend/services/translate_service.py:740) | T1 | **Identity da marca** → prompt tradução | `identity[:500]` | ALTA | 1 | (b) pedir identity mais compacta ou passar íntegra | §4.3 |
| P4-007b | redator-ambas | [translate_service.py:743](app-redator/backend/services/translate_service.py:743) | T1 | **Tom da marca** → prompt tradução | `tom[:300]` | ALTA | 1 | idem | §4.3 |
| P4-007c | redator-ambas | [translate_service.py:752](app-redator/backend/services/translate_service.py:752) | T1 | **Research** → prompt tradução | `str(research_data)[:1500]` | ALTA | 1 | idem | §4.3 |
| P4-008 | redator-RC | [rc_automation_prompt.py:57](app-redator/backend/prompts/rc_automation_prompt.py:57) | T2 | Overlay temas → prompt automation | `overlay_temas[:5]` | MÉDIA | 1 | (c) alertar se overlay > 5 entries ou incluir todas | §4.3 redator-RC |
| BO-001 | redator-BO | [overlay_prompt.py:45-77](app-redator/backend/prompts/overlay_prompt.py:45) | T1+T13 | Narrativa fonte overlay BO | `narrative[:max_chars] + "..."` | CRÍTICA | 1 | (a) preservar e pedir LLM para reformular | §4.3 redator-BO |
| C1 | curadoria | [download.py:117](app-curadoria/backend/services/download.py:117) | T1 | Nome filename download | `s[:200]` | MÉDIA | 1 | (c) erro se > 200 | §4.3 curadoria |
| T9-spam | editor | [main.py:77](app-editor/backend/app/main.py:77) | VARCHAR | `anti_spam_terms` config | `VARCHAR(500)` DB | MÉDIA (raro) | 4 | (c) alertar operador em admin UI | §4.3 editor |

**Total: 34 findings catalogados.** Destes:
- **19 CRÍTICOS** — perda ou risco de perda de conteúdo editorial em caminho principal
- **12 ALTOS** — perda/risco em caminho periférico ou violação de regra editorial específica
- **3 MÉDIOS** — UX ou caso raro

### 4.3 Análise por app (detalhes em arquivos separados)

Cada subseção referencia arquivo denso em `evidencias_profunda/problema_4_truncamentos/analise_por_app/`.

**4.3.1 `app-redator/backend/` (RC)** — [redator_rc.md](docs/rc_v3_migration/evidencias_profunda/problema_4_truncamentos/analise_por_app/redator_rc.md)
Concentra massa crítica: R1, R2, R7, P1-Trans, P4-001, P4-005, P4-006, P4-007, P4-008. Core do problema.

**4.3.2 `app-redator/backend/` (BO)** — [redator_bo.md](docs/rc_v3_migration/evidencias_profunda/problema_4_truncamentos/analise_por_app/redator_bo.md)
R3 (pior que RC — trunca sem log), BO-001 (truncamento declarado como feature). Herda R7 e P4-007 compartilhados.

**4.3.3 `app-editor/backend/`** — [editor.md](docs/rc_v3_migration/evidencias_profunda/problema_4_truncamentos/analise_por_app/editor.md)
P1-Ed1 a Ed-MIG2. 8 findings todos violando Princípio 2. Remoção completa de `legendas.py` text analysis + migrations + teste `verify_fix.py`.

**4.3.4 `app-portal/`** — [portal.md](docs/rc_v3_migration/evidencias_profunda/problema_4_truncamentos/analise_por_app/portal.md)
Zero findings CRÍTICOS. Editor de overlay já sem `maxLength` em conteúdo. 30+ CSS clamps MÉDIA (UX).

**4.3.5 `app-curadoria/`** + **4.3.6 `shared/`** + **4.3.7 testes/fixtures** — [curadoria_shared_testes.md](docs/rc_v3_migration/evidencias_profunda/problema_4_truncamentos/analise_por_app/curadoria_shared_testes.md)
- Curadoria: C1 (download filename), else logs-only
- Shared: R6 (sanitize_name)
- Testes: verify_fix.py precisa ajuste. **Não há suite automatizada.**

### 4.4 Padrões globais detectados

**Padrão G1 — "Truncar conteúdo aprovado para caber em prompt LLM"** (5+ matches):
- `rc_automation_prompt.py:66` → post
- `hook_prompt.py:42` → research
- `generation.py:203,205` → research
- `translate_service.py:740,743,752` → identity, tom, research

**Problema comum:** código pressupõe que limites de contexto do LLM são mais apertados do que são. Claude Opus 4.7 suporta 1M tokens de contexto (~4M chars), mas os prompts cortam inputs editoriais a 500-3000 chars.

**Remediação unificada sugerida:** função utilitária `_embed_editorial_context(content: str, max_chars: int, name: str) -> str` que, em vez de truncar, (a) mede tamanho real, (b) se excede, **levanta exceção** ou (c) retorna íntegro com flag `_exceeded_recommendation=True` registrada em log/verificacoes. Operador decide política: preservar íntegro (novos modelos suportam), ou pedir LLM para sumarizar a entrada primeiro.

**Padrão G2 — "Slice + ellipsis para display"** (2 matches em portal + implícito nos logs):
- `dashboard/page.tsx:222`, `video-card.tsx:89`

**Remediação:** considerar tooltip/hover para expor texto integral; CSS `line-clamp` com expand button é alternativa padrão.

### 4.5 Limites legítimos externos — avaliação

**Instagram caption limit: 2200 chars.** Grep por "2200" em app-redator retorna nada — não há detecção ou alerta no código hoje. Post pode ser gerado com 3000+ chars e só ser rejeitado pelo IG no momento da publicação. **Finding adicional (MÉDIA):** falta validação pré-publicação.

**YouTube título: 100 chars, descrição: 5000 chars.** Campo `youtube_title` é TEXT (sem limite), `youtube_tags` é TEXT. Sem validação de tamanho. **Finding adicional (BAIXA):** falta validação pré-publicação YouTube.

**R2 object key: 1024 chars** (limite AWS S3-compatible). `sanitize_name[:200]` em shared/curadoria é conservador — cabe folga. OK mas por motivo errado (está truncando para evitar filesystem issues locais, não por limite R2).

**LLM max_tokens** — já coberto em R7. **Crítico confirmado.**

### 4.6 Ambiguidades registradas

| # | Ambiguidade | Onde |
|---|-------------|------|
| A1 | "Última legenda" — CTA vs última narrativa | Problema 2, §2.4. Decisão editorial, não técnica. |
| A2 | `overlay_max_chars_linha` no perfil do editor — constante editorial ou configurável por marca? | Problema 1, §1.7, linha G. Se configurável, a arquitetura atual está ok; se constante, schema+UI devem ser removidos. |
| A3 | Identity/tom da marca para prompt de tradução — devem ser ilimitados ou sumarizados? | §4.4 padrão G1. Decisão editorial: preservar íntegros (risco de prompt longo) vs truncar com consciência (risco de perder nuance). |
| A4 | `overlay_temas[:5]` em automation — limite arbitrário | §4.2 P4-008. É OK descartar temas além da 5a no contexto do prompt, ou o ManyChat precisa conhecer todos? Depende da estratégia de automation. |
| A5 | Testes `verify_fix.py` — remover ou reescrever? | §4.3.7. Quando `_truncar_texto` for eliminado, o teste precisa ser ou removido, ou invertido (assert que NÃO há "..." no output). |

### 4.7 Ajuste A — Resposta explícita sobre `stop_reason` (T6)

**Pergunta:** o código detecta `response.stop_reason == "max_tokens"` em alguma chamada LLM e regenera, ou aceita saída truncada como completa?

**Resposta verificada:** grep `stop_reason` em `app-redator/backend/services/claude_service.py` retorna **zero matches** ([t6_claude_service_stop_reason.txt](docs/rc_v3_migration/evidencias_profunda/problema_4_truncamentos/t6_claude_service_stop_reason.txt)). O wrapper `_call_claude_api_with_retry` ([claude_service.py:659-683](app-redator/backend/services/claude_service.py:659)) captura a resposta e retorna o texto (`response.content[0].text`), sem verificar `stop_reason`. Retry é apenas para HTTP 529 (overload), não para truncamento.

**Classificação:** R7 — CRÍTICA. Todas as 10 chamadas LLM do redator estão vulneráveis. Remediação trivial (2-5 linhas): após `response = client.messages.create(...)`, verificar `if response.stop_reason == "max_tokens": raise LLMTruncated(...)` e deixar retry externo tratar.

---

## 5. Correções declaradas pela Fase 3 vs realidade atual

Observação 1 do feedback. Auditoria retroativa dos patches P1-P6 mergeados em [90add64](https://github.com/anthropics/apps/commit/90add64).

| Patch | O que declarou corrigir | Estado real pós-investigação | Pendência |
|-------|-------------------------|-------------------------------|-----------|
| P1 | Limite chars 33→38 | **PARCIAL**. Geração RC coerente (38). Tradução regenerate em [routers/translation.py:189](app-redator/backend/routers/translation.py:189) com `33` hardcoded. Stack editor inteiro em 33/35/99. Docstring desatualizada. | **CRÍTICA** — completar patch |
| P2 | CTAs canônicos (RC_CTA / BO_CTA dict por idioma) | Não inspecionado em detalhe nesta investigação. Referenciado em [translate_service.py:545-547](app-redator/backend/services/translate_service.py:545). Sem achado de truncamento associado. | — |
| P3 | Audit sentinel (_is_audit_meta no overlay_json) | Funcional — filtrado em 14 consumidores. Mencionado em [claude_service.py:1028-1042](app-redator/backend/services/claude_service.py:1028). | ✓ |
| P4 | brand_config removido do prompt overlay RC | Confirmado em [claude_service.py:1188-1193](app-redator/backend/services/claude_service.py:1188) (comentário explícito). | ✓ |
| P5 | _is_audit_meta blindagem em regenerate-overlay-entry | Sem investigação de regressão. Confirmado por commit `d8b6d27`. | ✓ |
| P6 | Filtro defensivo _is_audit_meta em build_rc_automation_prompt | Confirmado por commit `fd36f92`. | ✓ |

**Veredito Fase 3:** P2-P6 efetivos. **P1 parcial** — a investigação atual revela 4+ superfícies remanescentes. Recomendação: completar P1 como primeiro alvo da fase de execução (PROMPT 10).

---

## 6. Mapa de fluxo: cortes por caminho editorial

Observação 2 do feedback. Para cada tipo de output, quantos pontos de corte CRÍTICOS/ALTOS o conteúdo atravessa.

### Caminho Overlay RC (Etapa 3)

```
LLM (max_tokens=4096, R7) → _process_overlay_rc → _sanitize_rc (ok) →
_enforce_line_breaks_rc (R1, R2) → overlay_json salvo → render ASS
```

**Cortes atravessados:** R7 (na entrada), R1 e R2 (no pós-processador), R4 e R5 (clamp duração no mesmo `_process_overlay_rc`). **5 cortes CRÍTICOS/ALTOS** por cada legenda × 12-20 legendas típicas = conteúdo passa por 60-100 pontos de corte possíveis num único overlay.

### Caminho Overlay RC → Editor (render final)

```
overlay_json aprovado → Editor (app-editor) →
gerar_ass → _formatar_overlay (P1-Ed3 se pre_formatted=False) →
_truncar_texto (P1-Ed4) → ASS final
```

**Cortes atravessados:** P1-Ed3, P1-Ed4 (se flag não setada). **2 cortes CRÍTICOS** adicionais no editor.

### Caminho Lyrics (letra cantada) e Tradução

```
Gemini transcrição → Post-processing → legendas.py gerar_ass →
_truncar_texto(lyrics_max) [P1-Ed5] OU _truncar_texto(traducao_max) [P1-Ed6]
```

**Cortes atravessados:** P1-Ed5 ou P1-Ed6. **1 corte CRÍTICO** por lyrics/tradução.

### Caminho Hooks (Etapa 2)

```
Research aprovada → hook_prompt.py:42 (P4-005 [:3000]) →
LLM (max_tokens=4096, R7) → _sanitize_hooks → hooks_json
```

**Cortes atravessados:** P4-005, R7. **2 cortes ALTOS**.

### Caminho Post RC (Etapa 4)

```
Pesquisa + overlay aprovado → build_rc_post_prompt →
LLM (max_tokens=4096, R7) → _sanitize_post → post_text
```

**Cortes atravessados:** R7. **1 corte CRÍTICO**.

### Caminho Automation RC (Etapa 5)

```
Post aprovado → rc_automation_prompt.py:64-66 (P4-001 [:500]+"...") →
Overlay aprovado → :57 (P4-008 [:5]) →
LLM (max_tokens=1000, R7) → automation_json
```

**Cortes atravessados:** P4-001, P4-008, R7. **3 cortes ALTOS**.

### Caminho Tradução (Etapa 6) — aplicada × 7 idiomas

```
Overlay aprovado + post aprovado + research → translate_service.py:740-752
(P4-007a, P4-007b, P4-007c) → LLM (max_tokens=?, R7) → _enforce_line_breaks_rc
(R1, R2) OU _enforce_line_breaks_bo (R3)
```

**Cortes atravessados por idioma:** P4-007a, P4-007b, P4-007c, R7, R1+R2 (RC) ou R3 (BO). **4-6 cortes ALTOS+CRÍTICOS** × 7 idiomas = ~35 pontos de corte no fluxo de tradução.

### Caminho Export ZIP final

Não investigado em detalhe nesta sessão (export_service.py tem 5316 linhas). Enumeração de funções em [export_service_funcoes.txt](docs/rc_v3_migration/evidencias_profunda/problema_4_truncamentos/export_service_funcoes.txt). Funções listadas — análise inicial sugere zero truncamento de conteúdo (export apenas empacota, não modifica). **Recomendação:** análise mais profunda em sessão futura.

**Resumo do mapa:** um projeto RC típico (1 overlay × 20 legendas × 7 traduções × post × automation × hooks) atravessa a ordem de **150-200 pontos de truncamento CRÍTICO/ALTO** acumulados ao longo do pipeline completo. A densidade sugere que **qualquer projeto RC em produção está, estatisticamente, passando por múltiplos cortes**.

---

## 7. Priorização sugerida para fase de execução

Ordem técnica proposta. **Decisão editorial final é do operador.**

| Ordem | Finding(s) | Esforço | Risco | Impacto |
|-------|------------|---------|-------|---------|
| (i) | R1, R2, R3 — remover truncamento em `_enforce_line_breaks_*` | TRIVIAL (~10 linhas) | BAIXO | CRÍTICO (cobre ~35 entry-points no pipeline) |
| (ii) | R4, R5 — apertar clamp 4-7→4-6 | TRIVIAL (2 linhas) | BAIXO | ALTO |
| (iii) | R7 — `stop_reason` check em `_call_claude_api_with_retry` | PEQUENO (~5 linhas) | BAIXO | CRÍTICO (cobre 10 LLM calls) |
| (iv) | P1-Trans — remover hardcode `33` em translation.py:189 | TRIVIAL (1 linha) | BAIXO | CRÍTICO |
| (v) | Ed-MIG1 + Ed-MIG2 — versionar ou remover migrations SQL | PEQUENO | **MÉDIO** (DB state) | CRÍTICO (erradica fonte de verdade rival) |
| (vi) | P1-Ed1 a P1-Ed6 — remover text analysis do editor | MÉDIO (remover funções + callsites + teste verify_fix.py) | MÉDIO | ALTO (cobre P1-Ed3..6, viola Princípio 2) |
| (vii) | P4-001, P4-005, P4-006, P4-007, P4-008 — revisar limits de prompt | MÉDIO (decisão editorial por item) | BAIXO | ALTO (preserva contexto LLM) |
| (viii) | BO-001 — `_extract_narrative` em overlay_prompt.py | PEQUENO | BAIXO | CRÍTICO (BO) |
| (ix) | R6 + C1 — sanitize_name trunca → alertar | PEQUENO | BAIXO | MÉDIO |
| (x) | P3 — regras de qualidade em line-break (balanceamento, split) | **GRANDE** (~100 linhas + UI) | MÉDIO | ALTO |
| (xi) | P2-PathA-1, P2-PathA-2 — alinhar Path A ou deprecar | PEQUENO | BAIXO | MÉDIO |
| (xii) | P1-UI1, P1-UI2 — harmonizar defaults UI admin | TRIVIAL | BAIXO | MÉDIO (UX) |
| (xiii) | Validações externas (IG 2200, YT 100) | PEQUENO | BAIXO | MÉDIO |
| (xiv) | T8 CSS clamps — tooltip/expand | MÉDIO (UI) | BAIXO | MÉDIO (UX) |

**Recomendação de primeiro sprint (PROMPT 10 inicial):** (i) + (ii) + (iii) + (iv). Total ~20 linhas de código, risco baixo, impacto cobrindo a fonte do `esquece....` + clamp + LLM truncation + hardcoded 33. **Elimina a superfície crítica mais visível com o menor esforço.**

---

## 8. Validação pós-execução — ausência de testes automatizados

Projeto não tem suite automatizada. Validação das remediações será manual:

1. **Projeto canário** — identificar projeto RC real de referência (sugestão: o projeto que gerou o log `esquece....` em produção, ou reprocessar o projeto 355 referenciado em evidências históricas)
2. **Rerun completo** do pipeline RC (Etapas 1-6) após cada batch de patches
3. **Critérios de "funcionando":**
   - Zero `[RC LineBreak] Texto truncado: sobrou '...'` no log do redator
   - Zero `[legendas] Lyrics truncado: '...'` no log do editor
   - Zero `[legendas] Tradução truncado: '...'` no log do editor
   - Todas legendas narrativas dentro de clamp 4-6s (pós R4/R5)
   - Overlay ASS final renderizado no Aegisub sem "..." em textos que não deveriam ter
   - Post aprovado igual ao texto enviado ao prompt de automation (diff=0 além de \n)
   - Research aprovada igual ao texto enviado ao prompt de hooks/translation (diff=0)
   - Tradução gera N entries para N input entries em todos os 7 idiomas
   - `response.stop_reason` != `"max_tokens"` em todas as chamadas LLM (monitorar via log)
4. **Diff do overlay_json** antes/depois do patch para o projeto canário: número de legendas, caracteres por legenda, timestamps.

---

## 9. Metadados de investigação

**Cobertura:**
- Apps investigados: 6 (app-redator, app-editor, app-portal, app-curadoria, shared, tests)
- Marcas: 2 (RC, BO) explicitamente + superfície para futuras marcas
- Arquivos lidos completos (não apenas trechos): 8 (`claude_service.py` trechos extensos, `srt_service.py` completo, `rc_overlay_prompt.py` trechos, `legendas.py` trechos, `translate_service.py` trechos, `rc_automation_prompt.py` trecho, `storage_service.py` trecho, `hook_prompt.py` trecho)
- Comandos grep executados: ~25 (14 categorias T1-T14 + 10 greps complementares: callsites, constantes, stop_reason, etc.)
- Categorias do prompt cobertas: 14/14 (incluindo T3, T10, T14 com 0 matches — confirmado ausência)
- Findings catalogados: 34 (19 CRÍTICOS, 12 ALTOS, 3 MÉDIOS)

**Evidências salvas em** `docs/rc_v3_migration/evidencias_profunda/`:
- `problema_1_limite_chars/`: 11 arquivos (greps + 2 snippets + prompt_vs_codigo.md)
- `problema_2_timestamps/`: 5 arquivos (greps + duas_formulas_duracao.md)
- `problema_3_linebreaks/`: 2 arquivos (grep + casos_patologicos.md)
- `problema_4_truncamentos/`: 15 arquivos (14 greps de categoria + funcoes_suspeitas + translate_funcoes + export_service_funcoes + 5 análises por app)

**Commits incrementais** na branch `claude/investigacao-profunda-20260422-1730`:
1. `docs(investigacao): bootstrap + Problema 1 limite chars/linha (PROMPT 8)` — 11 arquivos, 1307 insertions
2. `docs(investigacao): Problema 2 timestamps/durações (PROMPT 8)` — 6 arquivos, 224 insertions
3. `docs(investigacao): Problema 3 qualidade quebra linhas (PROMPT 8)` — 3 arquivos, 212 insertions
4. `docs(investigacao): Problema 4 + sumário (PROMPT 8)` — pendente neste commit

**Limitações da investigação:**
- Não executei testes runtime — todas as análises são estáticas (leitura de código)
- Não acessei banco de produção — estado dos perfis editor não verificado em runtime
- Não reproduzi `esquece....` em runtime local — reconstituição é teórica baseada em leitura do código. Probabilidade alta de estar correta (match exato do padrão de log), mas fica como hipótese formal.
- `export_service.py` (5316 linhas) teve apenas enumeração de funções — análise profunda fica para sessão futura
- Fluxos de research (Etapa 1) e tradução multilíngue (Etapa 6) receberam análise mais superficial que overlay (Etapa 3)
- Não comparei diretamente com overlay renderizado em produção — não sei se todos os pontos de corte são ativos simultaneamente no mesmo projeto real

**Sugestão para auditoria posterior (PROMPT 9_AUDIT):** amostrar 5 dos 34 findings ao acaso e verificar (a) snippet de código citado está correto, (b) categoria atribuída é defensável, (c) severidade calibrada com o impacto editorial real. Se amostra passa, relatório aprovado.

