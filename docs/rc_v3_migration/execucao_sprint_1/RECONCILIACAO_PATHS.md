# Reconciliação de path:linha — pré-Sprint 1 (PROMPT 10A)

**Contexto:** a main recém-recebeu dois merges paralelos — auditoria PROMPT 9 (`8d0c62c`) e refactor `overlay-sentinel-restructure` (`d584029`). Os findings R1-R7 e P1-Trans foram escritos **antes** do refactor. Esta reconciliação valida, em modo read-only, se os path:linha declarados ainda batem com o código atual de `main`.

**Método:** `sed -n '<linha>p' <arquivo>` para cada finding; `grep -n '<padrão>' <arquivo>` quando a linha não retornava o conteúdo esperado.

**Arquivos inspecionados:**
- `app-redator/backend/services/claude_service.py` (1267 linhas)
- `app-redator/backend/services/translate_service.py` (1039 linhas)
- `app-redator/backend/routers/translation.py`

---

## Tabela consolidada

| Finding | Path:linha declarado | Path:linha atual | Status | Observações |
|---|---|---|---|---|
| R1 | `app-redator/backend/services/claude_service.py:869-873` | 869-873 | **INTACTO** | `break` dentro de `_enforce_line_breaks_rc` (def @819) descartando `resto = " ".join(palavras[idx:])`. Código atual já tem `_rc_logger.warning` antes do `break` — o descarte persiste, apenas com log. Finding ainda válido (patch: preservar conteúdo, não só logar). |
| R2 | `claude_service.py:880` | 880 | **INTACTO** | `novas_linhas = novas_linhas[:max_linhas]` — slice silencioso confirmado. |
| R3 | `claude_service.py:890-929` | 890-929 | **INTACTO** | `_enforce_line_breaks_bo` (def @890) trunca via `break` + slice `[:max_linhas]` sem logger. |
| R4 | `claude_service.py:960` | **968** | **DESLOCADO (+8)** | `dur = max(4.0, min(7.0, round(dur, 1)))` moveu 8 linhas para baixo. Padrão e conteúdo idênticos. |
| R5 | `claude_service.py:1009` | **1017** | **DESLOCADO (+8)** | `dur_por_legenda = max(4.0, min(7.0, dur_por_legenda))` moveu 8 linhas para baixo. Mesmo deslocamento de R4 — o refactor inseriu ~8 linhas acima de R4, propagando para R5. |
| R7.1 | `claude_service.py:96` | 96 | **INTACTO** | `message = client.messages.create(**kwargs)` |
| R7.2 | `claude_service.py:171` | 171 | **INTACTO** | `message = client.messages.create(` |
| R7.3 | `claude_service.py:237` | 237 | **INTACTO** | idem |
| R7.4 | `claude_service.py:337` | 337 | **INTACTO** | idem |
| R7.5 | `claude_service.py:358` | 358 | **INTACTO** | idem |
| R7.6 | `claude_service.py:666` | 666 | **INTACTO** | `message = client.messages.create(` dentro de `_call_claude_json` (docstring @660 confirma: `"""Chama client.messages.create com retry para 529/overloaded. Retorna raw text."""`). |
| R7.7 | `translate_service.py:910` | **—** | **TRANSFORMADO** | `grep client.messages.create` em `app-redator/backend/services/translate_service.py` retorna **zero matches**. A chamada SDK direta foi refatorada em `translate_one_claude` (def @832) para usar o helper `_call_claude_json(prompt=prompt, max_tokens=2048, temperature=0.3)` em `translate_service.py:907`. Como `_call_claude_json` é o próprio R7.6 (`claude_service.py:666`), este callsite **converge** para R7.6 e não requer patch próprio. |
| P1-Trans | `app-redator/backend/routers/translation.py:189` | 189 | **INTACTO** | `t_text = _enforce_line_breaks_rc(t_text, tipo, 33, lang=lang)` — hardcode `33` confirmado. |

---

## Implicações para o Sprint 1 (PROMPT 10A)

1. **R4 e R5 exigem ajuste de path:linha no pacote do Sprint 1** (960→968, 1009→1017). Conteúdo do patch inalterado — apenas reetiquetar a linha.
2. **R7 reduz de 7 para 6 callsites.** O refactor `overlay-sentinel-restructure` já eliminou a chamada SDK direta em `translate_service.py:910`, substituindo-a pela chamada ao helper `_call_claude_json`. O Sprint 1 deve:
   - Tratar os 6 callsites em `claude_service.py` (96, 171, 237, 337, 358, 666).
   - Consignar no relatório que `translate_service.py` já herda o tratamento via helper.
   - Remover a menção a `translate_service.py:910` da lista de alvos R7 no SPRINT_1_EXECUTION_PLAN (se existir).
3. **R1 merece nota de contexto no patch.** O fix original presumia ausência de log; o código atual já loga o descarte via `_rc_logger.warning`. O problema real (perda de conteúdo via `break`) continua — a justificativa do patch deve deixar claro que logar o descarte **não resolve** o bug.
4. **Todos os outros findings** (R2, R3, R7.1-R7.6, P1-Trans): path:linha intactos, patch aplica sem ajuste.

---

## Procedência (comandos executados)

```bash
sed -n '869,873p' app-redator/backend/services/claude_service.py      # R1
sed -n '880p'     app-redator/backend/services/claude_service.py      # R2
sed -n '890,929p' app-redator/backend/services/claude_service.py      # R3
sed -n '960p'     app-redator/backend/services/claude_service.py      # R4 (não bateu)
sed -n '1009p'    app-redator/backend/services/claude_service.py      # R5 (não bateu)
sed -n '96p;171p;237p;337p;358p;666p' app-redator/backend/services/claude_service.py  # R7.1-R7.6
sed -n '910p'     app-redator/backend/services/translate_service.py   # R7.7 (não bateu)
sed -n '189p'     app-redator/backend/routers/translation.py           # P1-Trans

# Grep de localização para as linhas que não bateram:
grep -n 'max\(4\.0,\s*min\(7\.0' app-redator/backend/services/claude_service.py      # → 968, 1017
grep -n 'client\.messages\.create' app-redator/backend/services/translate_service.py # → 0 matches
```
