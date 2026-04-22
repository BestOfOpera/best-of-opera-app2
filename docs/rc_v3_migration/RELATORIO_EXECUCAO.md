# Relatório de Execução — Fase 3 RC v3/v3.1

**Data:** 2026-04-22
**Branch:** `feature/rc-v3-v3.1-migration`
**Base:** `main` (commit `86f6b68`)
**Sessão:** PROMPT 2 revisado (6 patches P1-P6)

---

## Sumário executivo

Os 6 patches planejados foram aplicados em sequência de dependência conforme PROMPT 2 seção 4. Cada patch passou em smoke test programático localmente antes do commit. Um E2E sintético validou compatibilidade de shape entre as 6 etapas do pipeline. Nenhum teste com LLM real foi executado nesta sessão (custo/ambiente) — a **regressão narrativa editorial (seção 9 do PROMPT 2) permanece pendente** e é o último gate antes do merge para `main`.

**Commits da feature (7 no total):**

| # | SHA | Escopo | Descrição curta |
|---|-----|--------|---|
| 1 | `7a1190b` | docs | Investigação + anexos v3/v3.1 + plano execução |
| 2 | `105491f` | **P1** | limite de 38 chars por linha em 5 pontos (v3.1 baseline) |
| 3 | `77e6227` | **P2** | RC_CTA e RC_POST_CTA para tabela canônica v3 (F6.8) |
| 4 | `df78ed5` | **P3** | automation prompt v3 com post_text e A/B/C (F5.2) |
| 5 | `750ef6b` | **P4** | overlay v3.1 com fio dinâmico e cortes_aplicados (F3.1-F3.11) |
| 6 | `039337c` | **P5** | rc_post_prompt v3 da SKILL + save_cta em _format_post_rc (F4.1, F4.3, F4.5, F4.6) |
| 7 | `4a1d717` | **P6** | regras v3 em _build_translation_prompt (Opção C, F6.1-F6.9) |

**Escopo total:** 8 arquivos tocados, ~1450 linhas +/−. Nenhuma migração de banco. Sem breaking change de API pública.

---

## Decisões editoriais aplicadas (PROMPT 2 seção 2)

| # | Decisão | Status |
|---|---------|--------|
| 1 | HOOK-SEO descartado globalmente (F4.2 e em translation v3) | ✅ aplicada — `hook_seo` ausente em todos os prompts e em `_format_post_rc` |
| 2 | Tradução Opção C (inline, não função separada) | ✅ aplicada — `_build_translation_prompt` reescrito; `build_rc_translation_prompt` NÃO foi criado |
| 3 | `cortes_aplicados` Opção A (apenas persistir) | ✅ aplicada via sentinel `_is_audit_meta` (ver NOTAS_EXECUCAO) — sem UI, sem log estruturado específico |
| 4 | CTAs canônicos do anexo D.1 | ✅ aplicada — `RC_CTA` e `RC_POST_CTA` atualizados byte-a-byte conforme anexo |

**Sub-decisão do operador embutida:** margens verbosas mantidas (FR/IT/ES=+3, DE/PL=+5) no `_enforce_line_breaks_rc`. Implementadas.

---

## Detalhamento por patch

### P1 — limite 38 chars (commit `105491f`)

**Arquivos tocados:**
- [app-redator/backend/services/claude_service.py](app-redator/backend/services/claude_service.py): `_enforce_line_breaks_rc` default 33→38; margens 40→43 (DE/PL), 38→41 (FR/IT/ES); `_validate_overlay_rc` warning threshold 40→42 chars
- [app-redator/backend/services/translate_service.py](app-redator/backend/services/translate_service.py): 2 callsites com 33 literal → 38; prompt inline overlay_rules atualizado
- [app-redator/backend/routers/generation.py](app-redator/backend/routers/generation.py): prompt de `regenerate-overlay-entry` "33 caracteres"→"38 caracteres"

**Smoke test (5 casos):** PT 43ch→quebra; PT 37ch→intocado; FR 39ch (lim 41)→intocado; DE 44ch (lim 43)→quebra em 43; PT gancho 40ch→quebra em 38.

### P2 — CTAs canônicos v3 (commit `77e6227`)

**Arquivos tocados:** apenas [translate_service.py:37-67](app-redator/backend/services/translate_service.py:37)

**Mudanças:**
- `RC_CTA` (7 idiomas, com `\n`): EN/ES/DE/FR/IT/PL alterados para tabela canônica. PT intacto.
- `RC_POST_CTA` (7 idiomas, 1 linha com 👉): EN/ES/DE/FR/IT/PL alterados. PT intacto.

**Validação programática:** todas as linhas respeitam 38 + margem por idioma (14 linhas validadas). Cada `RC_POST_CTA` começa com `👉 `. PT byte-a-byte idêntico ao anexo D.1.

### P3 — automation v3 (commit `df78ed5`)

**Arquivos tocados:** apenas [prompts/rc_automation_prompt.py](app-redator/backend/prompts/rc_automation_prompt.py) — substituição integral pelo anexo D.2 (SHA256 `dce13a10...`).

**Mudanças:**
- `post_text` agora INJETADO no prompt como bloco `DESCRIÇÃO APROVADA:` (truncado em 500 chars com `...`)
- Estratégias A/B/C nomeadas explicitamente
- Novo campo JSON: `estrategia_diversidade_aplicada ∈ {A, B, C}`
- `genre_map` com "do/da/de" nos rótulos

**Callsite inalterado** em [claude_service.py:1202-1204](app-redator/backend/services/claude_service.py:1202) (assinatura preservada).

**Smoke test:** bloco `DESCRIÇÃO APROVADA:` presente; truncamento com `...` para post>500ch; A/B/C nomeadas; schema inclui novo campo; post curto aparece integral.

### P4 — overlay v3.1 (commit `750ef6b`)

**Arquivos tocados (5):**
- [prompts/rc_overlay_prompt.py](app-redator/backend/prompts/rc_overlay_prompt.py): substituído pelo anexo D.3 (SHA256 `a2c9f66d...`)
- [services/claude_service.py](app-redator/backend/services/claude_service.py): callsite em `generate_overlay_rc` atualizado (hook_tipo em vez de brand_config); `_process_overlay_rc` anexa sentinel `_is_audit_meta`; `_validate_overlay_rc` filtra sentinel
- [services/srt_service.py](app-redator/backend/services/srt_service.py): filtra sentinel antes de gerar SRT
- [services/translate_service.py](app-redator/backend/services/translate_service.py): `translate_overlay_json`, `translate_one_claude`, `translate_project_parallel` filtram sentinel
- [docs/rc_v3_migration/NOTAS_EXECUCAO.md](docs/rc_v3_migration/NOTAS_EXECUCAO.md): registro das decisões arquiteturais (brand_config removido, sentinel em vez de dict shape)

**Mudanças no prompt:**
- Assinatura: `brand_config` removido, `hook_tipo=""` adicionado
- Helper `_estimar_legendas(int)` → `_estimar_faixa_legendas(min, max tuple)`
- 4 seções novas: `<duracao_dinamica>`, `<fio_narrativo_dinamico>`, `<oralidade>`, `<anti_padroes_nomeados>`
- Rubric Fase 3 expandida (7 → 11 dimensões)
- 38 chars/linha como referência (P1 baseline)
- Novos campos no schema: `cortes_aplicados`, `fio_unico_identificado`, `pontes_planejadas`, `verificacoes.ancoragens_causais/descritivas`, `cenas_especificas`, `gancho_fechamento_ecoam`

**Persistência de auditoria (Decisão 3):** campos v3.1 são anexados como `{_is_audit_meta: True, fio_unico_identificado, pontes_planejadas, verificacoes}` no **final da lista** `overlay_json`. Shape lista preservada — compatível com 14+ consumidores sem mudar tipagem. Consumidores críticos (SRT, tradução, validador) filtram naturalmente.

**Smoke test:** assinatura v3.1 ativa (hook_tipo presente, brand_config ausente); seções novas presentes no prompt gerado (31395 chars); sentinel de auditoria preservado no final da lista; SRT filtra sentinel; tradução filtra sentinel.

### P5 — post v3 (commit `039337c`)

**Arquivos tocados (2):**
- [prompts/rc_post_prompt.py](app-redator/backend/prompts/rc_post_prompt.py): **construído do zero** a partir de `docs/rc_v3_migration/rc-post_SKILL.md`, preservando assinatura
- [services/claude_service.py:1067+](app-redator/backend/services/claude_service.py:1067): `_format_post_rc` atualizado para consumir `save_cta` e `follow_cta`

**Fichas aplicadas:** F4.1 (JSON estruturado), F4.3 (save_cta específico), F4.5 (keywords em prosa natural), F4.6 (8 anti-padrões IA nomeados).
**Fichas descartadas (por decisão do operador):** F4.2 (HOOK-SEO — `hook_seo` AUSENTE em todo o prompt e no montador), F4.4 (mix 5-8 hashtags — mantém 4).

**Layout de `_format_post_rc` v3:**
```
header_linha1
header_linha2
header_linha3 (se existir)
•
paragrafo1
•
paragrafo2
•
paragrafo3
•
save_cta
follow_cta            ← linha imediatamente seguinte, SEM "•" entre
•
•
•
[4 hashtags separadas por espaço]
```

**Retrocompatibilidade v2:** se `save_cta` ausente ou schema antigo com `cta`, layout anterior mantido (sem regressão visual).

**Smoke test:** prompt v3 com `EXATAMENTE 4`, `save_cta`, `anti_repeticao`, `follow_cta` presentes; `hook_seo`/`HOOK-SEO`/`125 chars`/`mix 2-3 amplas` AUSENTES; `_is_audit_meta` filtrado do overlay_resumo; post_text v3 com save_cta→follow_cta consecutivos (linhas 9 e 10); retrocompat v2 com schema `cta` funciona.

### P6 — translation v3 (commit `4a1d717`)

**Arquivo tocado:** apenas [services/translate_service.py](app-redator/backend/services/translate_service.py)

**Decisão arquitetural:** Opção C — incorporar regras no prompt inline existente. NÃO foi criado arquivo `build_rc_translation_prompt`. NÃO foi mudada persistência para campos estruturados.

**Adições:**
- Dict `_BANNED_VOCAB_BY_LANG` (6 idiomas, F6.5)
- Dict `_OVERLAY_LINE_LIMIT` (7 idiomas: PT/EN=38, FR/IT/ES=41, DE/PL=43)
- Função `validate_translation(translated_overlay, target_lang) -> list[dict]` — detecta linhas excedentes pós-LLM (F6.6)

**Mudanças no `_build_translation_prompt`:**
- Instrução explícita: "FORBIDDEN: shorten by cutting words" + "REQUIRED: reformulate the sentence" (Regra 2 do PROMPT 2)
- Seção `BANNED VOCABULARY IN <IDIOMA>` injetada
- Schema de saída inclui `verificacoes.legendas_com_linha_excedendo_38_chars[]` e `alertas[]`
- Mantém `post_text` como string monolítica (F6.6)

**Mudanças no `translate_one_claude`:**
- **F6.3 early-return PT:** `if target_lang == "pt"` retorna input byte-a-byte sem chamar LLM, com `verificacoes.pt_copiado_identico: True`
- Pós-tradução: `validate_translation` roda e registra excedentes em `verificacoes.alertas`; warning no log. Linha mantida íntegra (Regra 2).

**Smoke test:** prompt EN com regras v3 ("FORBIDDEN: shorten by cutting", vocab banido EN "timeless masterpiece"); prompt DE com ceiling 43 + vocab "Meisterwerk"; `validate_translation` detecta excedentes respeitando margem por idioma; `translate_one_claude(PT)` early-return preserva 3 entradas (incluindo `_is_cta`).

---

## E2E sintético (Beethoven/Roman Kim)

Executado localmente com fake responses (sem LLM). Valida shape-compatibilidade entre as 6 etapas:

```
[E1 Research] Prompt: 11482 chars OK
[E2 Hooks] Prompt: 8664 chars OK
[E3 Overlay v3.1] Prompt: 31754 chars OK — seções novas presentes
[E3 Overlay] _process_overlay_rc retornou 6 items (incl 1 audit sentinel)
[E3 Overlay] Todas linhas narrativas ≤38 chars (P1 funcional)
[E4 Post v3] Prompt: 18016 chars OK
[E4 Post v3] post_text (466 chars), save_cta → follow_cta consecutivos
[E5 Automation v3] Prompt: 5560 chars OK
[E6 Translation PT] Early-return — 5 overlays copiados idênticos
[E6 Translation EN prompt] 5491 chars — regras v3 presentes
[SRT] 5 blocos (audit_meta filtrado)
[CTAs] RC_CTA e RC_POST_CTA canônicos aplicados
```

**Cadeia validada:** `research_data (dict)` → `hooks_json (ganchos[])` → `selected_hook + hook_tipo` → `overlay_json (list com sentinel audit no final)` → `post_text (string via _format_post_rc)` → `automation_json (com estrategia_diversidade_aplicada)` → `translations (PT early-return + outros via prompt v3)`.

Nenhuma etapa quebrou. Todos os sentinels filtrados corretamente. Nenhum campo vazou entre etapas.

---

## Testes NÃO executados nesta sessão

### Regressão narrativa (PROMPT 2 seção 9) — PENDENTE

**Motivo:** requer chamada real ao Claude (custo + tempo) e inspeção editorial manual dos outputs. Fora do escopo da sessão de execução local.

**Pendências para o operador executar em staging antes do merge:**

1. Criar projeto-teste com metadata Beethoven/Roman Kim em banco de staging (não produção)
2. Rodar pipeline completo via endpoints HTTP:
   - `POST /api/projects/{id}/generate-research-rc`
   - `POST /api/projects/{id}/generate-hooks-rc`
   - `PUT /api/projects/{id}/select-hook` (usar `ganchos[0]`)
   - `POST /api/projects/{id}/generate-overlay-rc`
   - `POST /api/projects/{id}/generate-post-rc`
   - `POST /api/projects/{id}/generate-automation-rc`
   - `POST /api/projects/{id}/translate`

3. Inspeção editorial do overlay gerado — critérios do PROMPT 2 seção 9.1:
   - [ ] Nenhuma legenda (exceto gancho) menciona "Roman Kim" por nome
   - [ ] Nenhuma legenda menciona "Haydn" ou "Bonn" (cortados como fio secundário)
   - [ ] Nenhuma legenda descreve tecnicamente o que a imagem já mostra
   - [ ] Pelo menos uma legenda faz ponte explícita entre "angústia/surdez" e "notas ouvidas"
   - [ ] Pelo menos uma ancoragem causal (não apenas descritiva)
   - [ ] Vocabulário oral predominante ("contou", "Beethoven regeu")
   - [ ] Fio único: todas as legendas servem à narrativa "angústia → 5ª → reconhecimento"
   - [ ] `verificacoes.cortes_aplicados` não-vazio, citando pelo menos Roman Kim técnica / Haydn / Bonn
   - [ ] Cada legenda: duração entre 4.0 e 6.5 segundos

Se qualquer checklist falhar, investigar:
1. SHA dos arquivos no repo (vs anexos) — confirmar P3-P6 aplicados
2. `_enforce_line_breaks_rc` com default 38 — confirmar P1 ativo
3. Modelo LLM atual — confirmar `claude-sonnet-4-6` em [claude_service.py:23](app-redator/backend/services/claude_service.py:23)

### Teste HTTP E2E — PENDENTE

O E2E via endpoints HTTP descrito na seção 8 do PROMPT 2 também exige banco + LLM reais. Recomendo rodar em staging antes do merge, com o operador inspecionando outputs intermediários.

---

## Rollback plan (resumo, para referência)

Se alguma regressão aparecer em staging:

- **P1 regrediu:** revert `105491f`. Prompts v3.1 geram 38 chars mas re-wrap volta a 33 — cobertura degrada, não quebra.
- **P2 regrediu:** revert `77e6227`. CTAs voltam à versão anterior.
- **P3 regrediu:** revert `df78ed5`. `post_text` volta a ser parâmetro morto; campo `estrategia_diversidade_aplicada` sumiria.
- **P4 regrediu:** revert `750ef6b`. Prompt overlay antigo; perde fio dinâmico e `cortes_aplicados`. Overlays antigos no banco continuam funcionando (sentinel é anexado no final — código antigo nunca o adicionou, então não há histórico corrompido).
- **P5 regrediu:** revert `039337c`. Prompt post antigo; `save_cta` não é gerado; `_format_post_rc` volta ao layout sem save_cta. Posts gerados durante P5-ativo perdem o save_cta visualmente após rollback — operador pode regerar.
- **P6 regrediu:** revert `4a1d717`. Prompt de tradução volta ao anterior (33 chars se P1 também reverteu); `translate_one_claude(pt)` passa a chamar LLM novamente. Traduções já geradas em banco permanecem.

Cada revert é `git revert <SHA>` isolado, sem interdependência de ordem.

---

## Limitações conhecidas / registrados em NOTAS_EXECUCAO.md

1. **Sentinel `_is_audit_meta` em vez de dict shape** (P4): escolha conservadora para não quebrar ~14 consumidores. Registrado em [NOTAS_EXECUCAO.md](docs/rc_v3_migration/NOTAS_EXECUCAO.md). Se operador preferir shape dict `{"legendas": [...], ...}`, é refactor adicional (fora desta sessão).

2. **`brand_config` removido do overlay v3.1** (P4): anexo descarta; atualmente overlay é exclusivo da marca RC. Se futuro outro `brand_slug` reutilizar, reintroduzir `brand_section`. Risco SPEC-009 classificado BAIXO.

3. **Margens verbosas FR/IT/ES=+3, DE/PL=+5** (P1): sub-decisão do operador (seção 5.1.7 PROMPT 2). Se revisão editorial pedir 38 dura para todos os idiomas, zerar as margens em `_enforce_line_breaks_rc` e `_OVERLAY_LINE_LIMIT`.

4. **Validação de tradução não faz retry automático de reformulação** (P6 seção 5.6.7): registra excedentes mas não chama Claude novamente para uma segunda tentativa. Decisão conservadora — evita loop infinito / custo extra silencioso. Se em staging notar muitos `alertas`, considerar adicionar retry único.

5. **Regressão narrativa manual pendente** (seção 9): impossível executar sem LLM + inspeção humana.

---

## Critérios de aceitação (PROMPT 2 seção 12)

| Item | Status |
|---|---|
| 6 patches aplicados em ordem | ✅ P1 → P2 → P3 → P4 → P5 → P6 |
| Cada patch passou no smoke test antes do próximo | ✅ todos passaram |
| Teste E2E completo (seção 8) | ⚠️ E2E sintético local OK; E2E HTTP+LLM pendente (staging) |
| Teste de regressão narrativa (seção 9) | ❌ pendente (requer LLM + inspeção humana em staging) |
| RELATORIO_EXECUCAO.md criado | ✅ este arquivo |
| NOTAS_EXECUCAO.md com notas de execução | ✅ criado, 3 entradas registradas |
| Rollback plan documentado | ✅ seção acima |
| Commits isolados no branch de feature | ✅ 7 commits, sem merge em main |

---

## Próximos passos recomendados

1. **Operador abre o PR** (a partir deste branch contra `main`) e revisa os 7 commits.
2. **Deploy em staging** (Railway) e validação manual:
   - Rodar pipeline completo em projeto-teste Beethoven/Roman Kim
   - Inspeção editorial conforme checklist seção 9 do PROMPT 2
   - Verificar logs em busca de warnings inesperados
3. Se regressão narrativa passa + logs limpos → **merge para `main`** → deploy produção.
4. Monitoramento pós-deploy:
   - Logs do `rc_pipeline` e `translate_claude` nos primeiros projetos pós-deploy
   - Atenção a `[RC WARN]` de linhas >42 chars (threshold v3.1)
   - Atenção a `[CLAUDE] ... linha(s) excederam limite` em traduções
5. Se alguma marca futura reutilizar prompt overlay, reintroduzir `brand_section` (SPEC-009).

---

## Anexos

- [RELATORIO_INVESTIGACAO.md](docs/rc_v3_migration/RELATORIO_INVESTIGACAO.md) — mapeamento pré-execução
- [NOTAS_EXECUCAO.md](docs/rc_v3_migration/NOTAS_EXECUCAO.md) — surpresas e decisões pontuais
- [mapa_paths.txt](docs/rc_v3_migration/mapa_paths.txt) — paths RC-relevantes

Fim do relatório.
