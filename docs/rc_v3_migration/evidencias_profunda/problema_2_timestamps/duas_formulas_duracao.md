# Duas fórmulas paralelas de duração — mapeamento

## Path A — `generate_overlay` (legacy/BO)

**Função:** `generate_overlay` em [app-redator/backend/services/claude_service.py:367-507](app-redator/backend/services/claude_service.py:367)

**Callsites:**
- [app-redator/backend/routers/generation.py:118](app-redator/backend/routers/generation.py:118) — endpoint legacy `POST /overlay`
- [app-redator/backend/routers/generation.py:155](app-redator/backend/routers/generation.py:155) — endpoint legacy com `custom_prompt`

**Função interna:** `_calcular_duracao_leitura` em [claude_service.py:434-445](app-redator/backend/services/claude_service.py:434)
```python
def _calcular_duracao_leitura(text: str) -> float:
    """Range: 5.0s a 8.0s."""
    palavras = len(text.split())
    duracao = (palavras * 0.35) + 4.0
    return max(5.0, min(8.0, duracao))
```

**Características:**
- Fórmula: `0.35 × palavras + 4.0`
- **Clamp: 5.0-8.0s** (mínimo 5, máximo 8)
- **Tratamento da última narrativa:** [claude_service.py:470-485](app-redator/backend/services/claude_service.py:470) redistribui gap entre TODAS as narrativas para evitar última esticada (`extra_per = gap / len(parsed)`, aplicado a cada entry)
- **Cap de redistribuição:** 12.0s por legenda individual ([claude_service.py:483](app-redator/backend/services/claude_service.py:483))
- **CTA:** posicionado em `cta_secs = vid_duration - interval_secs` com `end = _secs_to_ts(vid_duration)` explícito ([claude_service.py:500](app-redator/backend/services/claude_service.py:500)) → CTA estende até fim do vídeo

## Path B — `generate_overlay_rc` (RC v3/v3.1)

**Função:** `generate_overlay_rc` em [claude_service.py:1181-1223](app-redator/backend/services/claude_service.py:1181), que chama `_process_overlay_rc` em [claude_service.py:932-1043](app-redator/backend/services/claude_service.py:932)

**Callsite:** [app-redator/backend/routers/generation.py:463](app-redator/backend/routers/generation.py:463) — `generate_overlay_rc_endpoint` (via `/rc/overlay`)

**Cálculo inline:** [claude_service.py:954-964](app-redator/backend/services/claude_service.py:954)
```python
if tipo == "cta":
    dur = cta_duracao   # max(5.0, duracao_video * 0.13)
else:
    palavras = len(texto.split())
    dur = palavras / 2.5   # ~2.5 palavras/segundo
    dur = max(4.0, min(7.0, round(dur, 1)))

if tipo != "cta" and tempo_narrativo > 0 and timestamp_sec + dur > tempo_narrativo:
    dur = max(4.0, tempo_narrativo - timestamp_sec)
```

**Compressão proporcional** quando narrativas excedem tempo_narrativo: [claude_service.py:1005-1016](app-redator/backend/services/claude_service.py:1005)
```python
dur_por_legenda = cta_inicio_ideal / len(narrativas)
dur_por_legenda = max(4.0, min(7.0, dur_por_legenda))
```

**Características:**
- Fórmula: `palavras / 2.5`
- **Clamp: 4.0-7.0s** (mínimo 4, máximo 7)
- **Tratamento da última narrativa:** NENHUM especial. Última é apenas a última do loop, herda clamp normal
- **CTA:** posicionado em `cta_secs = vid_duration - cta_duracao` com `cta_duracao = max(5.0, duracao_video * 0.13)`. Sem campo `end` explícito — SRT e editor usam `cut_end` automaticamente para último entry

## Comparação quantitativa

| Nº de palavras | Path A (5-8s) | Path B (4-7s) | Desejo operador (4-6s) |
|----------------|---------------|----------------|-------------------------|
| 2 palavras | 5.0s (clamp) | 4.0s (clamp) | 4.0s |
| 5 palavras | 5.75s | 4.0s (clamp, calc=2.0) | ≥4.0 |
| 8 palavras | 6.8s | 4.0s (clamp, calc=3.2) | 4-6 |
| 10 palavras | 7.5s | 4.0s (clamp, calc=4.0) | 5-6 |
| 15 palavras | 8.0s (clamp, calc=9.25) | 6.0s | 6.0s |
| 18 palavras | 8.0s (clamp) | 7.0s (clamp, calc=7.2) | 6.0s |
| 25 palavras | 8.0s (clamp) | 7.0s (clamp, calc=10) | 6.0s |

**Leitura:** Path A superestima (5-8 vs 4-6 = 1-2s acima), Path B subestima para textos curtos (clamp 4s quando devia ser 4-5) e superestima para textos longos (7s vs 6s).

## Tratamento da "última legenda" — ambas leituras editoriais

**Leitura A — "última" = CTA (estende até fim do vídeo):**
- Path A: CTA tem `end=vid_duration` explícito ✓
- Path B: CTA tem timestamp em `cta_secs`, sem `end` explícito no JSON. SRT generator usa `cut_end` automaticamente ([srt_service.py:37-38](app-redator/backend/services/srt_service.py:37)). Editor ASS usa `duracao_total_ms` para último ([legendas.py:491](app-editor/backend/app/services/legendas.py:491)) ✓

**Leitura B — "última" = última narrativa (não-CTA):**
- Path A: **redistribui gap** entre todas para evitar esticada ([claude_service.py:470-485](app-redator/backend/services/claude_service.py:470)). Se operador quer "última pode estender", isso é COMPORTAMENTO OPOSTO.
- Path B: nenhum tratamento especial. Última narrativa dura o clamp normal (4-7s) e termina quando CTA começa.

## Max_tokens (pre-coleta Ajuste A T6)

Chamadas LLM e `max_tokens` configurado, sem nenhum check de `stop_reason`:

| Linha | Função | max_tokens | stop_reason check? |
|-------|--------|------------|---------------------|
| [90](app-redator/backend/services/claude_service.py:90) | call inicial (provavelmente `_check_language_leak` ou similar) | 2048 | ✗ |
| [173](app-redator/backend/services/claude_service.py:173) | —— | 1024 | ✗ |
| [239](app-redator/backend/services/claude_service.py:239) | —— | 1024 | ✗ |
| [339](app-redator/backend/services/claude_service.py:339) | —— | 1024 | ✗ |
| [360](app-redator/backend/services/claude_service.py:360) | —— | 1024 | ✗ |
| [1152](app-redator/backend/services/claude_service.py:1152) | research RC (`generate_research_rc`) | 8192 | ✗ |
| [1167](app-redator/backend/services/claude_service.py:1167) | hooks RC | 4096 | ✗ |
| [1217](app-redator/backend/services/claude_service.py:1217) | **overlay RC** | **4096** | **✗** |
| [1238](app-redator/backend/services/claude_service.py:1238) | post RC | 4096 | ✗ |
| [1258](app-redator/backend/services/claude_service.py:1258) | automation RC | 1000 | ✗ |

**R7 — FINDING CRÍTICO NOVO:** Grep `stop_reason` em `claude_service.py` retorna **zero matches**. Nenhuma chamada LLM verifica se a resposta foi truncada pelo modelo. Se o overlay RC gera 20 legendas mas `max_tokens=4096` corta no meio, o código recebe JSON parcial, tenta parsear, e na melhor hipótese cai no retry de JSON inválido. Na pior hipótese (JSON válido mas com menos legendas que o pedido), o output é aceito silenciosamente como correto.

Esta é a categoria mais grave de truncamento — o próprio LLM é a fonte do corte, e o sistema não tem como detectar. Remediar requer ler `response.stop_reason` da SDK Anthropic e regenerar quando `== "max_tokens"`.
