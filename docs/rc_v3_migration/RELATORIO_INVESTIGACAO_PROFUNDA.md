# Relatório de Investigação Profunda — Limites, Timing, Line-Breaks, Truncamento Sistêmico

**Data de início:** 2026-04-22
**Branch de investigação:** `claude/investigacao-profunda-20260422-1730`
**Base:** `main @ 90add64` (merge RC v3/v3.1 migration — Fase 3 concluída)
**Escopo:** mapeamento read-only. Zero modificação em código de produção.
**Sessão:** PROMPT 8 em Claude Code, modo max effort / ultrathink.

---

## Sumário executivo

> Atualizado progressivamente conforme cada problema é concluído. Seção final consolidada após Problema 4.

**Status no momento do último commit:** Problemas 1 concluído. Problemas 2, 3, 4 pendentes.

**Findings pré-investigação (reconhecimento):** 6 pontos de truncamento CRÍTICO identificados antes da varredura sistemática (R1-R6, ver §1 e §4 quando redigido).

**Nota operacional sobre validação:** o projeto não tem suite de testes automatizada. Verificação das remediações na fase posterior (PROMPT 10) será manual — rerun de pipeline completo em projeto RC/BO teste com comparação de output.

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

> Pendente. Será preenchido no próximo commit.

---

## Metadados de investigação

> Preenchido ao final da sessão.
