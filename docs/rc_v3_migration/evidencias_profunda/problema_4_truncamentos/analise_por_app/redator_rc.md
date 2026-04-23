# Análise de truncamento — `app-redator/backend/` (RC)

## Pontos CRÍTICOS (conteúdo editorial aprovado/gerado truncado)

| # | Path:linha | Categoria | O quê |
|---|------------|-----------|-------|
| R1 | [claude_service.py:869-873](app-redator/backend/services/claude_service.py:869) | T1+log | `break` + descarte de `" ".join(palavras[idx:])` em `_enforce_line_breaks_rc`. Log warning, conteúdo perdido. **Fonte do `esquece....` em produção.** |
| R2 | [claude_service.py:880](app-redator/backend/services/claude_service.py:880) | T2 | `novas_linhas[:max_linhas]` sem log. Segundo corte silencioso em RC. |
| R7 | [claude_service.py:659-729](app-redator/backend/services/claude_service.py:659) | T6 | `_call_claude_api_with_retry` não verifica `response.stop_reason == "max_tokens"`. 10 chamadas LLM com max_tokens=1000-8192 aceitam output truncado como completo. |
| P4-001 | [rc_automation_prompt.py:64-66](app-redator/backend/prompts/rc_automation_prompt.py:64) | T1+T13 | `post_summary = post_clean[:500].rstrip() + "..."`. Post aprovado (possivelmente 1500+ chars) truncado para 500 antes de ir ao prompt LLM de ManyChat. LLM gera respostas com contexto parcial. |
| P4-005 | [hook_prompt.py:42](app-redator/backend/prompts/hook_prompt.py:42) | T1 | `research_str = json.dumps(research_data)[:3000]`. Research aprovado truncado antes do prompt de hooks. Hooks podem perder fatos. |
| P4-006a | [routers/generation.py:203](app-redator/backend/routers/generation.py:203) | T1 | `research_str = _json.dumps(research_data)[:2000]` (dict path) |
| P4-006b | [routers/generation.py:205](app-redator/backend/routers/generation.py:205) | T1 | `research_str = research_data[:2000]` (string path) — callsite regenerate entry, limite menor que hook_prompt |
| P4-007a | [translate_service.py:740](app-redator/backend/services/translate_service.py:740) | T1 | `{identity[:500] if identity else ...}` em prompt de tradução Claude. Identity da marca truncada. |
| P4-007b | [translate_service.py:743](app-redator/backend/services/translate_service.py:743) | T1 | `{tom[:300] if tom else ...}` — tom da marca truncado |
| P4-007c | [translate_service.py:752](app-redator/backend/services/translate_service.py:752) | T1 | `{str(research_data)[:1500] if research_data else ...}` — research truncado para prompt de tradução. Rodado × 7 idiomas. |
| P4-008 | [rc_automation_prompt.py:57](app-redator/backend/prompts/rc_automation_prompt.py:57) | T2 | `overlay_resumo = " | ".join(overlay_temas[:5])`. Se overlay tem 12 legendas, 7 descartadas do contexto do LLM de automation. |

## Pontos MÉDIOS (ruído ou UX-only)

| # | Path:linha | Categoria | Observação |
|---|------------|-----------|------------|
| M1 | [translate_service.py:985-1015](app-redator/backend/services/translate_service.py:985) | T2 justificável | Loop sobre `overlay_json` PT. Se Claude retorna extras em `claude_result["overlay"]`, são descartados silenciosamente (sem alerta, sem log). Entries faltantes recebem fallback do texto PT original (comportamento correto). |
| M2 | [routers/translation.py:191](app-redator/backend/routers/translation.py:191) | elif | `elif len(t_text) > 70:` — trigger para chamar `_enforce_line_breaks_bo` (já mapeado em Problema 1) |

## Pontos OK — `_sanitize_*` sem truncamento

| # | Path:linha | Análise |
|---|------------|---------|
| OK1 | [claude_service.py:574-590](app-redator/backend/services/claude_service.py:574) `_sanitize_post` | Remove separators markdown e engagement bait patterns. **Remove linhas inteiras** por regex — mas decisão editorial intencional (evitar LLM patterns), não truncamento. |
| OK2 | [claude_service.py:768-804](app-redator/backend/services/claude_service.py:768) `_sanitize_rc` | Remove travessões, metadados, markdown, emojis. **Nenhum slice, nenhum truncamento.** Apenas substituição. |
| OK3 | [claude_service.py:611](app-redator/backend/services/claude_service.py:611) `_strip_markdown_preamble` | Remove headers markdown de resposta LLM. Decisão editorial, não truncamento. |
| OK4 | [claude_service.py:916-935](app-redator/backend/services/translate_service.py:916) | **Exemplo positivo**: validação de excesso de chars em tradução registra `excedidos[]` e **preserva íntegro** com alerta "Regra 2: nunca cortar" na mensagem. Padrão a replicar em outras funções. |

## Logs / debugging (BAIXA severidade)

Dezenas de `[:50]`, `[:100]`, `[:200]`, `[:500]` em `logger.info/warning` — truncamento de strings em mensagens de log. Não afeta conteúdo editorial (é apenas log). Listagem completa em [t1_slice_py.txt](docs/rc_v3_migration/evidencias_profunda/problema_4_truncamentos/t1_slice_py.txt). Representativos: `claude_service.py:386, 502, 698, 871, 1041, 1197`; `translate_service.py:112, 116, 914, 934`; `routers/generation.py:51, 78`.
