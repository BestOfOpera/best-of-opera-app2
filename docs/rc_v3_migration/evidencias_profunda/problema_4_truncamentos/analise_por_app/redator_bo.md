# Análise de truncamento — `app-redator/backend/` (BO / marcas genéricas)

BO compartilha a infraestrutura de `app-redator/backend/` com RC mas usa funções e prompts separados (`overlay_prompt.py` vs `rc_overlay_prompt.py`, `hook_prompt.py` vs `rc_hook_prompt.py`, etc.). Alguns pontos de truncamento são específicos de BO, outros são compartilhados (afetando ambas as marcas).

## Pontos CRÍTICOS (específicos de BO)

| # | Path:linha | Categoria | O quê |
|---|------------|-----------|-------|
| R3 | [claude_service.py:890-929](app-redator/backend/services/claude_service.py:890) | T1+T2 **sem log** | `_enforce_line_breaks_bo` trunca em silêncio absoluto. `break` na linha 921 + slice na linha 928, **sem warning**. Operador nunca descobre que conteúdo BO foi cortado. Pior que RC. |
| BO-001 | [overlay_prompt.py:77](app-redator/backend/prompts/overlay_prompt.py:77) | T1+T13 | `narrative = narrative[:max_chars].rsplit(" ", 1)[0] + "..."`. Truncamento explícito com reticências na função `_extract_narrative` que alimenta o prompt BO. Segundo comentário do código ([overlay_prompt.py:45-48](app-redator/backend/prompts/overlay_prompt.py:45)): "Retorna texto truncado em max_chars". **Declarado como feature**, mas viola Princípio 1. |

## Pontos MÉDIOS

| # | Path:linha | Categoria | Observação |
|---|------------|-----------|------------|
| BO-M1 | [translate_service.py:563](app-redator/backend/services/translate_service.py:563) | callsite R3 | `_enforce_line_breaks_bo(translated_text, max_chars_linha=max_linha, max_linhas=2)` quando `len(translated_text) > 70` no fluxo Google fallback. Traduções BO sofrem truncamento silencioso (R3). |
| BO-M2 | [translate_service.py:1006](app-redator/backend/services/translate_service.py:1006) | callsite R3 | Idem, no fluxo Claude path. |

## Pontos CRÍTICOS compartilhados com RC

R7 (max_tokens sem stop_reason) afeta **ambas as marcas** — o `_call_claude_api_with_retry` é chamado tanto por paths RC quanto BO.

P4-007 (identity/tom/research truncados em prompt de tradução) afeta **todas as marcas** — o `translate_service.py:740-752` é usado para todas as 7 línguas e não discrimina marca.

## Observação editorial

BO atualmente tem mitigação via flag `overlay_pre_formatted=True` ([app-editor/backend/app/main.py:875-877](app-editor/backend/app/main.py:875)) que pula `_formatar_overlay()` no editor. Isso evita **apenas** o truncamento no editor — não resolve R3 (truncamento BO no redator) nem BO-001 (truncamento em `_extract_narrative`).

**Resumo:** BO tem superfície de truncamento específica (R3, BO-001) que opera silenciosamente (nenhum log warning) + herda toda a superfície compartilhada com RC (R7, P4-007).
