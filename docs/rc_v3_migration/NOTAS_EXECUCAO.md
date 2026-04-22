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

### 2026-04-22 · P4 · brand_config removido do prompt overlay v3.1

**Contexto:** O anexo `rc_overlay_prompt_v3_1.py` descarta `brand_config` da assinatura (substituído por `hook_tipo=""`). Confirmado via `grep -n "brand_config|brand_section" docs/rc_v3_migration/rc_overlay_prompt_v3_1.py` — zero resultados.

**Análise de impacto:**
- `build_rc_overlay_prompt` tem **um único callsite**: `claude_service.py:1160` em `generate_overlay_rc`
- `generate_overlay_rc` é invocado apenas por `POST /generate-overlay-rc` em `routers/generation.py:456`, que valida `brand_slug == "reels-classics"` antes de rodar
- Logo, na prática, o prompt overlay só é usado pela marca RC atualmente
- Os prompts hook/post/research/automation continuam recebendo `brand_config` — isolamento multi-brand (SPEC-009) preservado nessas etapas

**Decisão:** aplicar v3.1 como está. Brand directives não são injetadas no prompt overlay — o próprio prompt v3.1 é específico ao estilo "Reels Classics" por design editorial.

**Risco de regressão SPEC-009:** BAIXO por ora. Se no futuro outro brand_slug precisar reutilizar o prompt overlay, será necessário reintroduzir brand_section. Registrado aqui para consulta futura.

### 2026-04-22 · P4 · _estimar_legendas preserva compatibilidade

O anexo v3.1 troca `_estimar_legendas(duracao)→int` por `_estimar_faixa_legendas(duracao)→(min,max)`. Confirmado via grep que `_estimar_legendas` é **módulo-privado do overlay** (duplicado também em `rc_research_prompt.py` como função independente). Substituir só o do overlay não quebra research.

### 2026-04-22 · Padrão de mensagem de commit

PROMPT 2 sugeriu mensagens em inglês (padrão convencional commits em inglês). Porém `CLAUDE.md` do projeto estabelece "Commits em português" como regra. Adotando português conforme padrão do repo. Escopos usados: `fix(redator)`, `feat(redator)` espelhando commits anteriores do histórico.

### 2026-04-22 · P4 · Persistência de `cortes_aplicados` via sentinel `_is_audit_meta`

**Ambiguidade detectada:** PROMPT 2 seção 5.4.3 propõe que `_process_overlay_rc` retorne **dict** `{"legendas": [...], "fio_unico_identificado": "...", "pontes_planejadas": [...], "verificacoes": {...}}`. Mas **mudar o shape de lista→dict quebra ~14 consumidores**:

1. `_validate_overlay_rc(overlay_json)` itera como lista (claude_service.py:1029)
2. `generate_post_rc`, `generate_automation_rc` passam `project.overlay_json or []` como lista
3. `build_rc_post_prompt`, `build_rc_automation_prompt` iteram `for leg in overlay_legendas`
4. `translate_overlay_json` itera lista
5. `_build_translation_prompt` recebe `overlay_entries` como lista
6. `generate_srt(overlay_json, cut_end)` em `srt_service.py` itera lista
7. `routers/generation.py:187` `overlay = project.overlay_json or []`
8. `export_service._save_language_to_r2` passa lista pra `generate_srt`
9. `approve-post.tsx` e TypeScript via `ProjectOut.overlay_json: Optional[list]`
10. Editor recebe via HTTP esperando lista

**Decisão conservadora (aplicada):** manter shape **lista**. Anexar campos de auditoria como **item sentinel no final** com `_is_audit_meta: True`. Consumidores que iteram sobre entradas reais ganham um filtro `{'_is_audit_meta': True}` — padronizado com o filtro existente de `_is_cta`. Menos invasivo que migrar 14 callsites para dict.

**Cumpre Decisão 3 (Opção A — apenas persistir):**
- ✅ `cortes_aplicados` e campos v3.1 persistidos em `project.overlay_json`
- ✅ Sem UI, sem log estruturado
- ✅ Shape da lista preservado (compatibilidade completa com consumidores)

**Custo da decisão:**
- Consumidores iteradores que usam campo `text`/`texto` são naturalmente resilientes (audit item não tem campo text). Poucos consumers precisam filtro explícito.
- `_validate_overlay_rc` ganha filtro explícito para não logar warnings sobre o sentinel.

**Tradeoff aceito:** se algum consumidor novo for adicionado no futuro iterando overlay_json sem filtrar `_is_audit_meta`, pode acontecer log estranho (ex: "legenda sem texto"). Mitigação: nomenclatura `_is_audit_meta` explícita + este registro.

**Registrado para contra-argumento:** se operador prefere shape dict a despeito do custo, reverter este patch e aplicar versão dict-based + adaptar os 14 consumidores.
