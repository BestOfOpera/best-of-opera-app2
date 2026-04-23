# Análise de truncamento — `app-editor/backend/`

Decisão editorial: **editor não deve analisar chars** (Princípio 2). Qualquer função em `app-editor/` que conte/analise/limite chars é candidata a remoção.

## Pontos CRÍTICOS (violam Princípio 2)

| # | Path:linha | Categoria | O quê |
|---|------------|-----------|-------|
| P1-Ed1 | [legendas.py:109-131](app-editor/backend/app/services/legendas.py:109) `quebrar_texto_overlay` | T1 | Quebra em 2 linhas se `len(texto) > max_chars`. Não trunca, mas analisa chars no editor. Callsite: [legendas.py:183](app-editor/backend/app/services/legendas.py:183). |
| P1-Ed2 | [legendas.py:134-166](app-editor/backend/app/services/legendas.py:134) `_formatar_texto_legenda` | T2 | Word-wrap com `linhas[:max_linhas]` silencioso na linha 164. |
| P1-Ed3 | [legendas.py:169-238](app-editor/backend/app/services/legendas.py:169) `_formatar_overlay` | T1+T13 | Chama `_truncar_texto` em 4 pontos (linhas 202, 210, 235, 237). Linha 210 literal: `return texto[:max_por_linha - 1].rstrip() + "…"`. |
| P1-Ed4 | [legendas.py:241-264](app-editor/backend/app/services/legendas.py:241) `_truncar_texto` | **T1+T13** | Função explícita de truncamento com "..." sufixo. Cortesia do editor em descartar conteúdo sem alerta. |
| P1-Ed5 | [legendas.py:653](app-editor/backend/app/services/legendas.py:653) | T1 | **Lyrics** truncadas via `_truncar_texto(texto, lyrics_max)` (default 43). Log warning emitido, mas operador não vê — log fica em container efêmero do Railway. |
| P1-Ed6 | [legendas.py:670](app-editor/backend/app/services/legendas.py:670) | T1 | **Tradução** truncada via `_truncar_texto(texto_trad, traducao_max)` (default 100). Log warning, operador não vê. |
| Ed-MIG1 | [main.py:363-370](app-editor/backend/app/main.py:363) | Migration SQL | `UPDATE editor_perfis SET overlay_max_chars=66, overlay_max_chars_linha=33 WHERE sigla='RC' AND overlay_max_chars=70` — backfill v3.4 força RC para 33. Roda a cada startup. |
| Ed-MIG2 | [main.py:737-740](app-editor/backend/app/main.py:737) | Migration SQL | `UPDATE editor_perfis SET overlay_max_chars=99 WHERE sigla='RC' AND overlay_max_chars != 99` — segundo backfill conflitante. |

## Pontos BAIXOS (logs/debugging)

Editor tem ~30 matches de `[:N]` em `pipeline.py`, `legendas.py`, `auth.py`, `worker.py` — todos em `logger.info/warning/error` ou em `erro_msg=str(e)[:500]` para gravar em DB. Representativos em [t1_slice_py.txt](docs/rc_v3_migration/evidencias_profunda/problema_4_truncamentos/t1_slice_py.txt) linhas 24-52.

**Erro_msg em DB com slice [:500]** (pipeline.py:666, 1156, 1695, 2246, 2261, 2265, 2310, 2808) — se a mensagem de erro é longa, fica truncada em DB. Impacto: **diagnóstico** (operador vê menos contexto). Não afeta conteúdo editorial.

## VARCHAR — `app-editor/backend/app/models/` e `main.py` CREATE TABLE

119 ocorrências de `VARCHAR(N)` ou `String(N)` em app-editor. Análise amostrada (detalhe em [t9_varchar.txt](docs/rc_v3_migration/evidencias_profunda/problema_4_truncamentos/t9_varchar.txt)):

| Tipo de campo | Exemplo | VARCHAR | Adequado? |
|---------------|---------|---------|-----------|
| IDs / slugs | `slug VARCHAR(50)`, `sigla VARCHAR(5)` | pequeno | ✓ |
| Datas timestamp | `corte_original_inicio VARCHAR(20)` | 20 chars MM:SS ok | ✓ |
| URLs | `youtube_url String(500)`, `logo_url VARCHAR(500)` | 500 para URLs longas | ✓ |
| Nomes próprios | `artist String(255)`, `nome VARCHAR(100)` | 255/100 para nomes | ✓ (pode clamp em nomes extremos, MÉDIA) |
| Hashes | `senha_hash VARCHAR(500)` | bcrypt fits | ✓ |
| **anti_spam_terms** | `VARCHAR(500)` | lista de termos | **MÉDIA** — se operador adicionar muitos termos, clamp silencioso |
| Config editorial | `overlay_style`, `post_style`, `research_data` | Não são VARCHAR, são JSON/TEXT | ✓ **editoriais são JSON/TEXT** |

**Conclusão T9 editor:** Nenhum campo editorial (overlay_json, post_texto, research_data) é VARCHAR. Todos são JSON/TEXT. Há possível clamp em `anti_spam_terms` se operador abusar — MÉDIA severidade, raro.

## Tests (tests/verify_fix.py)

[verify_fix.py](app-editor/backend/tests/verify_fix.py) é teste manual que **valida** `_truncar_texto` e `_formatar_overlay` como comportamento correto. Contém cópia das funções (lines 1-75) + assertions de que o truncamento "..." aparece no output. **Precisa ser removido ou invertido** quando as funções forem removidas/corrigidas na fase de execução.

## Resumo editor

- 8 findings CRÍTICOS (P1-Ed1 a Ed-MIG2)
- 0 findings que truncam conteúdo editorial além do que já foi mapeado
- Todas as violações de Princípio 2 concentradas em `app/services/legendas.py` + `app/main.py` migrations
- Remediação: remover `_truncar_texto` + callsites + migrations SQL + teste `verify_fix.py`
