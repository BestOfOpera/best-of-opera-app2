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

### 2026-04-22 · BYPASS EXPLÍCITO · merge direto em `main` sem rodar checklist de staging

**Contexto:** operador autorizou merge da `feature/rc-v3-v3.1-migration` em `main` **sem rodar os 6 itens do checklist "Pending before merge"** que estavam listados no corpo do PR #1 (Draft) e no RELATORIO_EXECUCAO.md seção "Critérios de aceitação":

1. ❌ E2E HTTP real em staging (Beethoven/Roman Kim — 6 endpoints de geração + translate)
2. ❌ Regressão narrativa (inspeção humana do overlay_json contra as 6 regras v3.1)
3. ❌ Validar tradução em DE, FR, PL (idiomas com margem maior, edge cases de reformulação)
4. ❌ Verificar frontend `app-portal/components/redator/approve-post.tsx` renderiza `save_cta` antes de `follow_cta`
5. ❌ Verificar que Editor recebe `overlay_json` com sentinel `_is_audit_meta` e não processa como legenda visível no ASS/burn-in
6. ❌ Run de stress (5 projetos seguidos)

**Autorização literal do operador:**
> *"Opção B. Bypass autorizado. Faça merge da feature/rc-v3-v3.1-migration em main e push. Risco meu. Registra no NOTAS_EXECUCAO.md que foi bypass explícito sem rodar os 6 itens do checklist."*

**Implicações do bypass:**
- Código v3/v3.1 vai para produção (deploy Railway automático a partir de `main`) sem validação end-to-end com LLM real
- Regressões narrativas (caso exista) só aparecerão nos primeiros projetos pós-deploy
- Possível comportamento inesperado do Editor ao receber `_is_audit_meta` no `overlay_json` — não foi testado contra o fluxo `/api/v1/editor/importar`
- Frontend pode não renderizar `save_cta` se `approve-post.tsx` tiver lógica que ignore campos novos (improvável, mas não validado)

**Plano de monitoramento pós-deploy sugerido (operador):**
- Observar logs `rc_pipeline` e `translate_claude` no Railway nas primeiras horas pós-deploy
- Gerar um projeto Beethoven/Roman Kim logo após deploy e validar output manualmente
- Se regressão crítica: rollback seguindo seção "Rollback plan" do RELATORIO_EXECUCAO.md (cada commit é revert-isolado)

**Risco assumido pelo operador.** Este registro serve como trilha de auditoria caso haja necessidade de post-mortem futuro.

---

## 2026-04-22 · Refactor `overlay-sentinel-restructure` (PROMPT 6B)

Refactor estrutural que desfaz a decisão "sentinel no array" do P4 em favor de campo `overlay_audit` separado. Motivado pelo `RELATORIO_INVESTIGACAO_REGRESSAO.md` (Bloco A) que identificou essa decisão como causa-raiz da tela "Ocorreu um erro inesperado" no portal.

**Branch:** `refactor/overlay-sentinel-restructure` a partir de `main` @ `90add64`.

### Decisões técnicas fixadas (PROMPT 6B, seção 4 do plano revisado)

- **D1 — Shape do retorno de `_process_overlay_rc`:** tupla `(legendas: list, audit: dict)` — pythônica, callsite já usa `overlay_json = _process_overlay_rc(...)`, mudança para `legendas, audit = …` é mínima.
- **D2 — Schema do `overlay_audit`:** dict livre persistido como `Mapped[Optional[str]] = mapped_column(JSON, nullable=True)`, mesmo padrão de `research_data`, `hooks_json`, `automation_json`.
- **D3 — Testes:** infraestrutura de testes automatizados é inexistente no repo; criação de `pytest`/`vitest` está fora do escopo. Validação por: (a) script E2E sintético `scripts/e2e_shape_compat.py`, (b) smoke manual via Python REPL após cada commit backend, (c) `npx tsc --noEmit` + `npm run lint && npm run build` no portal, (d) staging Railway antes do merge.
- **D4 — Migration de dados legados:** SQL one-shot que **descarta** o sentinel do array `overlay_json` sem popular `overlay_audit` — `cortes_aplicados` histórico não tem valor editorial. `overlay_audit` fica NULL para projetos antigos.
- **D5 — Coluna em `Translation`:** não adicionar. `translate_service` nunca persistiu sentinel em traduções (item-por-item rebuild com só `timestamp` + `text`). `overlay_audit` só faz sentido no projeto raiz.
- **D6 — `generation.py:regenerate-overlay-entry`:** consumer #9 (não listado no catálogo original do PROMPT 6B; achado por grep nesta sessão). Vai no Commit 3 junto com os outros consumers. Cuidado extra: além de filtro, faz **re-persistência** do `raw_overlay` completo (linha 258 atual) — após refactor, persistência fica trivial pois `project.overlay_json` é sempre lista limpa.

### Divergências entre catálogo do PROMPT 6B e código real (registrar para auditoria)

1. **9 consumers, não 8.** Grep revelou `routers/generation.py:187-190` (regenerate-overlay-entry) como consumer não listado. Introduzido pelo commit `d8b6d27` da Fase 3 (hardening posterior ao P4).
2. **Projeto NÃO usa Alembic.** Migrations auto-aplicadas em `main.py:_run_migrations()` no startup (padrão idempotente com `ALTER TABLE ADD COLUMN`). Commit 1 segue esse padrão, não Alembic.
3. **Zero infra de testes no repo.** Sem `tests/`, sem `pytest.ini`, sem jest/vitest. `package.json` do portal não tem `type-check` nem `test`. Plano de validação ajustado em D3.
4. **Linhas do catálogo divergem do código em ±1 linha** em alguns pontos (ex: `rc_automation_prompt.py` catálogo :50, real :51). Não-material.

### Commit 1 — `refactor(db): adiciona coluna overlay_audit`

**Arquivos:**
- `app-redator/backend/models.py:53` — adicionada linha `overlay_audit: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)` logo após `overlay_json`
- `app-redator/backend/main.py:67-69` — adicionado bloco idempotente `if "overlay_audit" not in cols: ALTER TABLE projects ADD COLUMN overlay_audit JSON` (marcado como v17)

**Smoke test:** `docs/rc_v3_migration/smoke_test_results/commit_1.log` — validado:
- coluna `overlay_audit` criada com tipo `JSON`
- total 42 colunas em `projects`
- idempotência 3x (não falha ao re-executar)
- roundtrip de dados: gravar dict em `overlay_audit` e recuperar intacto

**Não tocou:** `Translation` model, `schemas.py` (vai no Commit 4), nenhum consumer (vai no Commit 3).

### Commit 2 — `refactor(claude_service): _process_overlay_rc retorna (legendas, audit)`

**Arquivos:**
- `app-redator/backend/services/claude_service.py:932-943` — assinatura muda para `tuple[list, dict]`; docstring documenta contrato explícito.
- `app-redator/backend/services/claude_service.py:1035-1047` — sentinel `_is_audit_meta` removido do array; audit virou dict local construído no mesmo bloco de quando `response` traz campos de auditoria. Log mantido, só ajustado (`audit_item` → `audit`).
- `app-redator/backend/services/claude_service.py:1051` — `return overlay_json, audit` (antes `return overlay_json`).
- `app-redator/backend/services/claude_service.py:1223-1229` — `generate_overlay_rc` desempacota tupla e persiste em dois campos: `project.overlay_json = legendas`, `project.overlay_audit = audit or None`. Preserva retorno de `list` (assinatura pública do wrapper não muda).

**Smoke test:** `docs/rc_v3_migration/smoke_test_results/commit_2.log` — 3 casos:
- Caso 1: response com campos de auditoria → tupla `(list, dict)`, lista homogênea (todos itens têm `text` + `timestamp`), audit populado.
- Caso 2: response sem campos de auditoria → audit `{}` (para wrapper armazenar NULL).
- Caso 3: serialização JSON de `legendas` não contém a string `_is_audit_meta` em lugar nenhum.

**Nota sobre contagem de legendas no smoke test Caso 1:** input tem 5 legendas, output tem 4. Diferença é pré-existente — `_enforce_line_breaks_rc` ou sanitização descartou uma (não relacionado ao refactor; mesma lógica antes e depois).

**Consumers em seguida:** `_validate_overlay_rc` ainda tem filtro interno de `_is_audit_meta` (linhas 1051-1055) — vai virar no-op nesta versão porque o sentinel nunca mais está na lista, mas só removido formalmente no Commit 3. Idem para os outros 8 consumers.

### Commit 3 — `refactor(consumers): remove filtros de _is_audit_meta (9 pontos)`

**Arquivos tocados (7 arquivos, 9 pontos de filtro):**
- `app-redator/backend/services/claude_service.py:~1053` — `_validate_overlay_rc` mantém filtro de `_is_cta` apenas (docstring ajustada)
- `app-redator/backend/prompts/rc_post_prompt.py:~54` — `build_rc_post_prompt` loop de `overlay_textos`: removido `leg.get("_is_audit_meta")` do OR, comentário atualizado
- `app-redator/backend/prompts/rc_automation_prompt.py:~51` — idem no loop de `overlay_temas`
- `app-redator/backend/services/srt_service.py:18-21` — removidas 3 linhas (comentário, filtro list-comp) e docstring ajustada; agora `overlay_json = overlay_json or []`
- `app-redator/backend/services/translate_service.py:540` — `translate_overlay_json`: list-comp trocada por `overlay_json = overlay_json or []`; comentário removido
- `app-redator/backend/services/translate_service.py:817` — `validate_translation`: OR simplificado para só `_is_cta`
- `app-redator/backend/services/translate_service.py:846-852` — `translate_one_claude`: docstring e filtro
- `app-redator/backend/services/translate_service.py:955-960` — `translate_project_parallel`: docstring e filtro
- `app-redator/backend/routers/generation.py:187-190, 258-260` — **consumer #9, NÃO listado no catálogo do PROMPT 6B**. Era caso delicado: filtrava para obter `overlay` mas persistia `raw_overlay` com sentinel preservado. Pós-refactor: `project.overlay_json` já é lista limpa, `raw_overlay` deixa de existir, variável única `overlay`, persistência trivial (`project.overlay_json = overlay`). Mutação in-place continua correta pois não há mais dois nomes para a mesma lista.

**Smoke test:** `docs/rc_v3_migration/smoke_test_results/commit_3.log` — 9 subcasos:
- C1: `_validate_overlay_rc` não quebra com lista homogênea (warnings pré-existentes sobre #legendas baixo são esperados pelo teste mínimo)
- C2-C3: loops de `rc_post_prompt` e `rc_automation_prompt` filtram só CTA; 4 narrativas de 5 total
- C4: `generate_srt` produz 20 linhas SRT corretas
- C5-C8: `translate_service` source inspecionado; zero menções a `_is_audit_meta`
- C9a: `generation.py` source inspecionado; zero menções a `_is_audit_meta` **e** zero a `raw_overlay`
- C9b: fluxo de `regenerate-overlay-entry` simulado — índice 2 mutado in-place, outras legendas (gancho, CTA) intactas

**Grep confirma:** `grep -rn "_is_audit_meta" --include="*.py" .` retorna zero resultados em todo o código Python após este commit.

**Ponto de atenção para Commit 4:** o endpoint GET `/api/projects/{id}` ainda não expõe `overlay_audit`. Frontend atual ainda não conhece o campo. Fluxo segue quebrado para projetos antigos (banco ainda tem sentinel no array) — não é problema deste commit; projetos novos gerados pós-Commit 2 já têm lista limpa.
