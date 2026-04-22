# Notas de Execução — Fase 3 RC v3/v3.1

*Registro de surpresas, ambiguidades, e decisões pontuais tomadas durante a execução do PROMPT 2 revisado. Cada entrada tem data, patch, descrição e resolução.*

---

## Decisões editoriais fixas (do PROMPT 2 revisado, seção 2)

1. **HOOK-SEO descartado globalmente** — F4.2 permanece descartada. Nenhum `hook_seo` no schema de post v3 nem no consumidor translation.
2. **Tradução: Opção C** — incorporar regras v3 no `_build_translation_prompt` inline existente. Não criar arquivo separado `build_rc_translation_prompt`.
3. **`cortes_aplicados`: Opção A** — apenas persistir em `project.overlay_json`. Sem UI, sem logging estruturado.
4. **CTAs canônicos: versão do anexo D.1** — atualizar `RC_CTA` e `RC_POST_CTA` para corresponder à tabela do anexo `rc_translation_prompt_v3.py`.

### Sub-decisão do operador embutida no PROMPT 2

- **Margens verbosas por idioma mantidas**: FR/IT/ES = +3 (limite 41); DE/PL = +5 (limite 43). Motivo: verbosidade natural não é culpa do LLM; cortar palavras viola Regra 2.

---

## Observações durante execução

(registradas conforme surgem)
