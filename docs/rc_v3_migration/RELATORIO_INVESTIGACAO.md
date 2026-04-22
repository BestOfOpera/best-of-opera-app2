# Relatório de Investigação — RC Pipeline (pré-migração v3/v3.1)

**Data:** 2026-04-22
**Sessão:** PROMPT 1 (investigação estática, read-only)
**Artefato de saída:** este arquivo + `mapa_paths.txt`
**Próxima fase:** PROMPT 2 (execução dos patches), após aprovação deste relatório

---

## 0. Sumário executivo

O pipeline RC vive integralmente em `app-redator/` (backend FastAPI síncrono) com dispatch etapa-a-etapa via endpoints `POST /api/projects/{id}/generate-{etapa}-rc`. Cada etapa persiste seu resultado em colunas JSON do `Project` e alimenta a próxima (`research_data → hooks_json → selected_hook → overlay_json → post_text → automation_json`). A tradução (Etapa 6) NÃO é uma função `build_rc_translation_prompt` — vive em `translate_service.py` com prompt hardcoded inline, Claude como primário e Google Translate como fallback. O frontend (`app-portal`, Next.js 16) consome `post_text` como string monolítica em textarea (sem split, sem campos estruturados). Persistência SQLAlchemy com **migrations DIY** via `ALTER TABLE` manual em `main.py` no startup — não há Alembic.

**Cinco achados críticos para o patch futuro:**

- **38 chars por linha (v3.1) vs 33 chars hardcoded em 4 lugares** ([claude_service.py:819,1038](app-redator/backend/services/claude_service.py:819), [translate_service.py:555,609,817](app-redator/backend/services/translate_service.py:555), [generation.py:210](app-redator/backend/routers/generation.py:210)). Mudança no prompt sozinha NÃO se propaga — o re-wrap pós-LLM reimpõe 33.
- **Schema v3 de tradução pressupõe campo `hook_seo` na descrição**, mas Lote B explicitamente DESCARTOU F4.2 (HOOK-SEO). Contradição entre anexos — resolver antes do patch.
- **Campo `save_cta` do Lote B não é consumido por `_format_post_rc`** ([claude_service.py:1067](app-redator/backend/services/claude_service.py:1067)) — se prompt v3 do post gerar, a string final não incluirá.
- **`rc_translation_prompt_v3.py` do anexo não tem consumidor no repo.** Função nova; decidir entre (a) adicioná-la ao repo + criar wrapper que a invoca via Claude, ou (b) incorporar suas regras ao `_build_translation_prompt` inline existente.
- **Assinatura do `build_rc_overlay_prompt` diverge entre repo e anexo v3.1**: repo usa `brand_config=None`, anexo usa `hook_tipo=""`. Aplicar v3.1 sem ajustar callsite em [claude_service.py:1159-1163](app-redator/backend/services/claude_service.py:1159) quebra a chamada.

---

## 1. Arquitetura de alto nível

**Stack Python:** Python 3.11 (Dockerfile), FastAPI 0.115.6, SQLAlchemy 2.0.36, Pydantic 2.10.3, anthropic 0.42.0, Sentry-SDK opcional. Ver [app-redator/requirements.txt](app-redator/requirements.txt).

**Frontend:** Next.js 16.1.6 + React 19.2.3 + App Router + TypeScript + Tailwind 4 + Radix UI. Único repo de frontend em [app-portal/](app-portal/) (não confundir com `app-redator/frontend/` — o `frontend/` dentro do redator parece ser uma aplicação SPA separada buildada e servida via `StaticFiles` no Dockerfile). Confirmado: `app-portal/` é o front principal; `app-redator/frontend/` é mencionado em [app-redator/Dockerfile:6](app-redator/Dockerfile) mas não afeta o pipeline RC em termos de lógica editorial — fica fora do escopo desta investigação para confirmar seu papel atual.

**Monorepo:** backend e frontend convivem no mesmo repo; arquitetura por-domínio:
- `app-curadoria/` — curadoria YouTube (fora de escopo)
- `app-redator/` — **TODO o pipeline RC vive aqui** (backend FastAPI + frontend SPA legado)
- `app-editor/` — pipeline de vídeo (burn-in, FFmpeg, ASS)
- `app-portal/` — frontend Next.js único (entry-point UI para operador)
- `shared/` — storage_service.py (abstração R2)

**Estrutura RC no redator:**
```
app-redator/backend/
├── main.py             ─ Bootstrap FastAPI, migrations DIY, routers register
├── database.py         ─ SQLAlchemy engine + Base
├── models.py           ─ Project (com campos RC) + Translation
├── schemas.py          ─ Pydantic request/response (sem validação do JSON interno)
├── config.py           ─ env vars + HOOK_CATEGORIES + load_brand_config
├── prompts/
│   ├── rc_research_prompt.py   ─ build_rc_research_prompt
│   ├── rc_hook_prompt.py       ─ build_rc_hook_prompt
│   ├── rc_overlay_prompt.py    ─ build_rc_overlay_prompt
│   ├── rc_post_prompt.py       ─ build_rc_post_prompt
│   ├── rc_automation_prompt.py ─ build_rc_automation_prompt
│   └── bo_research_prompt.py, hook_helper.py, hook_prompt.py, overlay_prompt.py, post_prompt.py, youtube_prompt.py ─ (BO, fora escopo)
├── routers/
│   ├── generation.py    ─ endpoints /generate-*-rc
│   ├── translation.py   ─ endpoints /translate, /retranslate/{lang}
│   ├── projects.py, approval.py, calendar.py, export.py, health.py
├── services/
│   ├── claude_service.py      ─ LLM, sanitize, line-breaks, _format_post_rc, _process_overlay_rc
│   ├── translate_service.py   ─ Google Translate + Claude translation hybrid
│   ├── srt_service.py         ─ generate_srt (50 linhas, simples)
│   └── export_service.py      ─ save_texts_to_r2
```

**Linguagens adicionais:** Docker (Dockerfile), Shell (Procfile, CMD uvicorn), JSON (railway.json), TypeScript (app-portal).

---

## 2. Fluxo de dados do pipeline

**Entrada:** formulário web — operador cria `Project` via [routers/projects.py](app-redator/backend/routers/projects.py) com metadados (artist, work, composer, cut_start, cut_end, brand_slug="reels-classics", etc). Existem endpoints de detecção automática via Claude screenshot/texto ([claude_service.py:130](app-redator/backend/services/claude_service.py:130), [claude_service.py:334](app-redator/backend/services/claude_service.py:334)).

**Dispatch por etapa:** cada etapa é endpoint SÍNCRONO separado (não há worker nem fila). Operador clica → backend roda Claude → persiste → retorna. Ordem no pipeline RC:

| Etapa | Endpoint | Função service | Persiste em | Valida pré-requisitos |
|---|---|---|---|---|
| 1 Research | `POST /generate-research-rc` | `generate_research_rc` | `project.research_data` | brand_slug==RC |
| 2 Hooks | `POST /generate-hooks-rc` | `generate_hooks_rc` | `project.hooks_json` | research_data existe |
| — Select | `PUT /select-hook` | inline | `project.selected_hook`, `project.hook` | hooks_json existe |
| 3 Overlay | `POST /generate-overlay-rc` | `generate_overlay_rc` | `project.overlay_json` | selected_hook existe |
| — Regen entry | `POST /regenerate-overlay-entry/{idx}` | inline em [generation.py:173](app-redator/backend/routers/generation.py:173) | `project.overlay_json[idx]` | overlay existe |
| 4 Post | `POST /generate-post-rc` | `generate_post_rc` | `project.post_text` (string) | overlay_json existe |
| — Approve | `PUT /approve-post` | — | `project.post_approved=True` | — |
| 5 Automation | `POST /generate-automation-rc` | `generate_automation_rc` | `project.automation_json` | post_text existe |
| — Approve | `PUT /approve-automation` | — | `project.automation_approved=True` | — |
| 6 Translation | `POST /translate` | `translate_project` em [routers/translation.py:36](app-redator/backend/routers/translation.py:36) | cria N registros em `translations` | RC: overlay+post approved |

**Assincronia:** NÃO. Tudo síncrono dentro do request HTTP. Sem Celery, RQ, Dramatiq. Tradução interna usa `ThreadPoolExecutor(max_workers=6)` para paralelizar 6 idiomas ([translate_service.py:846](app-redator/backend/services/translate_service.py:846)), mas dentro de um único request.

**Passagem entre etapas:** sempre pelo banco — cada etapa LÊ `project.*` da etapa anterior e ESCREVE sua própria coluna. Não há cache Redis, não há passagem direta de objeto.

**Rollback/retry:** manual. Não há rollback automático. Endpoint `/regenerate-*` para refazer uma etapa específica. Endpoint `/regenerate-overlay-entry/{idx}` refaz UMA legenda do overlay isoladamente. Em falha Claude 529, `_call_claude_api_with_retry` tenta 3x com backoff 10/20/30s ([claude_service.py:659](app-redator/backend/services/claude_service.py:659)).

**Recovery de startup:** `_recover_stuck_projects()` em [main.py:80](app-redator/backend/main.py:80) — marca projetos em `translating`/`generating` como `awaiting_approval` quando app reinicia. Previne zombies pós-restart.

---

## 3. Integração com LLM

**Provedor único para geração:** Anthropic (`anthropic` SDK v0.42.0). Google Translate v2 apenas como fallback na tradução.

**Modelo hardcoded:** `claude-sonnet-4-6` em [claude_service.py:23](app-redator/backend/services/claude_service.py:23). Não configurável por etapa ou via env var. SPEC-006 (✅ CONCLUÍDO) atualizou de `claude-sonnet-4-5-20250929`.

**Parâmetros por etapa** (em `generate_*_rc` de [claude_service.py](app-redator/backend/services/claude_service.py:1104-1210)):

| Etapa | max_tokens | temperature |
|---|---:|---:|
| research | 8192 | 0.7 |
| hooks | 4096 | 0.85 |
| overlay | 4096 | 0.85 |
| post | 4096 | 0.7 |
| automation | 1000 | 0.5 |
| translation (1 idioma) | 2048 | 0.3 |
| regenerate-overlay-entry | — (default 2048) | 0.8 |

**System prompt para JSON:** `"Return RAW JSON only. Rules: 1) First character must be { or [. 2) Last character must be } or ]. 3) No ```json fences. 4) No text before or after the JSON."` ([claude_service.py:689](app-redator/backend/services/claude_service.py:689)).

**Tratamento de JSON inválido:** cadeia de 4 tentativas em `_call_claude_json` ([claude_service.py:686](app-redator/backend/services/claude_service.py:686)):
1. `_strip_json_fences` + `json.loads`
2. extrai por `{...}` via `find/rfind`
3. extrai por `[...]` via `find/rfind`
4. retry com nova chamada Claude adicionando "CRITICAL: Your previous response was not valid JSON"

Se tudo falhar, `raise ValueError("Claude retornou JSON inválido após 2 tentativas. Últimos 500 chars: ...")`.

**Retry 529/overloaded:** 3 tentativas, backoff 10/20/30s ([claude_service.py:659](app-redator/backend/services/claude_service.py:659)). Endpoint handlers convertem em HTTP 503 para o frontend.

**Timeout:** 120s na construção do client (`client = anthropic.Anthropic(api_key=..., timeout=120.0)` em [claude_service.py:22](app-redator/backend/services/claude_service.py:22)).

**Streaming:** NÃO. Usa `client.messages.create()` bloqueante.

**Logging:** stdlib `logging` com loggers nomeados `"rc_pipeline"` ([generation.py:10](app-redator/backend/routers/generation.py:10)) e `"translate_claude"` ([translate_service.py:586](app-redator/backend/services/translate_service.py:586)). Logs registram: tamanho do prompt (chars/tokens estimados), tempo decorrido, primeiros/últimos 200 chars em erro. Sentry-SDK opcional (`SENTRY_DSN` env) em [main.py:12-21](app-redator/backend/main.py:12).

**Contabilização tokens/custo:** não há. Apenas log de tamanho de prompt/resposta.

---

## 4. Prompts do pipeline

### 4.1 rc-research

- **Path:** [app-redator/backend/prompts/rc_research_prompt.py](app-redator/backend/prompts/rc_research_prompt.py)
- **Linhas totais:** 333
- **Função:** `def build_rc_research_prompt(metadata: dict) -> str:` — linha 28
- **Assinatura:** 1 parâmetro (`metadata` dict)
- **Sem versionamento no nome.** Não há `_v2`, `_v3` coexistindo.
- **Helpers locais:**
  - `_calcular_duracao(cut_start, cut_end) -> int` — linha 11
  - `_estimar_legendas(duracao_seg) -> int` — linha 21 (retorna INT único, média 5.5s/legenda)
- **Docstring:** método Kephart (Role → Context → Task → Constraints → Format → Self-check). Prompt interno, operador não vê output.
- **Seções internas do prompt:** `<role>`, `<context>`, `<task>` (7 ETAPAS), `<constraints>`, `<format>`, `<self_check>`
- **Schema JSON declarado** (parafraseado):
  ```
  compositor_na_epoca { idade_na_composicao, situacao_pessoal, local, outras_obras_periodo, evento_recente_marcante }
  por_que_a_peca_existe { motivacao, dedicatoria, opiniao_do_compositor, tempo_de_composicao, instrucao_original_ignorada }
  recepcao_e_historia { estreia, reacao_publica, criticas_famosas, redescoberta, performance_historica_marcante }
  interprete { origem_trajetoria, diferencial, historia_pessoal, relacao_com_esta_peca, observavel_nesta_performance }
  fatos_surpreendentes [] { fato, tipo (evento|estado|conexao), verificavel, potencial_emocional, sobre }
  conexoes_culturais [] { conexao, dados_verificaveis, tipo }
  cadeias_de_eventos [] { nome, resumo_cadeia, eventos [{id, evento}] }
  angulos_narrativos [] { nome, tipo, fio_narrativo, fato_central, potencial_hook }
  alertas []
  ```
- **Callsite:** [claude_service.py:1108-1118](app-redator/backend/services/claude_service.py:1108) — `generate_research_rc`. Não passa `brand_config` (função não aceita).

### 4.2 rc-hooks

- **Path:** [app-redator/backend/prompts/rc_hook_prompt.py](app-redator/backend/prompts/rc_hook_prompt.py)
- **Linhas totais:** 247
- **Função:** `def build_rc_hook_prompt(metadata: dict, research_data: dict, brand_config: dict | None = None) -> str:` — linha 35
- **Helpers locais:**
  - `_build_rc_brand_section(brand_config)` — linha 11 (retorna string de directives da marca)
- **Docstring:** Recebe metadados + `research_data` (output etapa 1); produz N ganchos ranqueados.
- **Seções:** `<role>`, `{brand_section}`, `<context>`, `<task>` (7 PASSOS), `<constraints>`, `<format>`, `<self_check>`
- **Schema JSON declarado:**
  ```
  ganchos [] { rank, texto, linhas (1|2), angulo, tipo (emocional|cultural|estrutural|especifico), fio_narrativo, cadeia_base, por_que_funciona }
  descartados_e_motivos [] { texto, motivo_descarte }
  ```
- **Callsite:** [claude_service.py:1123-1141](app-redator/backend/services/claude_service.py:1123). Se LLM devolver lista em vez de dict, `generate_hooks_rc` wrappea em `{"ganchos": [...], "descartados_e_motivos": []}` (fallback).
- **Consumo downstream:** `generate_overlay_rc` busca `h["texto"]` e `h["fio_narrativo"]` do gancho selecionado (linha 1153-1157 do claude_service).

### 4.3 rc-overlay

- **Path:** [app-redator/backend/prompts/rc_overlay_prompt.py](app-redator/backend/prompts/rc_overlay_prompt.py)
- **Linhas totais:** 441
- **SHA256:** `2ab8267f22c2c9449afb63e465981f7b9b9249857f09817e393e25c757160486`
- **Função:** `def build_rc_overlay_prompt(metadata, research_data, selected_hook, hook_fio_narrativo="", brand_config: dict | None = None) -> str:` — linha 31
- **Helpers locais (repo atual):**
  - `_calcular_duracao` — linha 11
  - `_estimar_legendas(duracao_seg) -> int` — linha 21 (retorna INT, subtrai CTA ~13%)
- **Seções:** `<role>`, `{brand_section}`, `<context>`, `<task>` (FASE 1-3, 4 PASSOS + 6 VERIFICAÇÕES), `<constraints>`, `<examples>` (Mozart Réquiem + La Campanella), `<format>`, `<self_check>` (9 verificações)
- **Regra crítica:** linha 227 — *"Máximo 33 caracteres por linha"* (literal no prompt). CTA fixo hardcoded `"Siga, o melhor da música clássica,\ndiariamente no seu feed. ❤️"` (linhas 148-149).
- **Schema JSON declarado:**
  ```
  mapa_eventos_interno: str (E1→E2→...)
  legendas [] { numero, tipo (gancho|corpo|fechamento|cta), texto, linhas, evento_mapa, funcao }
  verificacoes { total_legendas, ancoragens_ao_video, legendas_do_angulo_vs_expansao, gancho_fechamento_par, paralelismos_encontrados, metaforas_sensoriais, travessoes }
  ```
- **Callsite:** [claude_service.py:1159-1163](app-redator/backend/services/claude_service.py:1159). Invoca com `(metadata, research_data, selected_hook, hook_fio, brand_config=brand_config)` — 5º argumento é `brand_config` **posicional/nomeado**.

### 4.4 rc-post

- **Path:** [app-redator/backend/prompts/rc_post_prompt.py](app-redator/backend/prompts/rc_post_prompt.py)
- **Linhas totais:** 261
- **Função:** `def build_rc_post_prompt(metadata: dict, research_data: dict, overlay_legendas: list, brand_config: dict | None = None) -> str:` — linha 11
- **Helpers locais:** nenhum além de inline `overlay_resumo` builder (linha 39-49).
- **Seções:** `<role>`, `{brand_section}`, `<context>`, `<task>` (7 PASSOS), `<constraints>`, `<examples>` (Mendelssohn/Hahn), `<format>`, `<self_check>` (9 verificações)
- **Schema JSON declarado** (repo ATUAL — sem save_cta/hook_seo):
  ```
  header_linha1: str
  header_linha2: str
  header_linha3: str
  paragrafo1: str
  paragrafo2: str
  paragrafo3: str
  cta: str (default "👉 Siga, o melhor da música clássica, diariamente no seu feed.")
  hashtags: [str, str, str, str]  # padrão 4
  anti_repeticao { fatos_overlay, fatos_descricao, algum_fato_repetido }
  ```
- **Callsite:** [claude_service.py:1181-1184](app-redator/backend/services/claude_service.py:1181). Depois do LLM, `_format_post_rc` monta string.

### 4.5 rc-automation

- **Path:** [app-redator/backend/prompts/rc_automation_prompt.py](app-redator/backend/prompts/rc_automation_prompt.py)
- **Linhas totais:** 193
- **SHA256:** `173ecf5dd18c4eeacfed635a0e91cdcb6cd99359151b80145da2ec9b53a5f624`
- **Função:** `def build_rc_automation_prompt(metadata: dict, overlay_legendas: list, post_text: str) -> str:` — linha 11
- **Helpers locais:** nenhum (genre_map inline, linha 33-44).
- **Seções:** `<role>`, `<context>`, `<task>` (3 COMPONENTES), `<constraints>`, `<format>`, `<self_check>`
- **Observação crítica:** `post_text` é RECEBIDO como parâmetro mas **NÃO é injetado no prompt LLM**. Parâmetro morto. Este é exatamente o fix D.2 do anexo v3.
- **Schema JSON declarado:**
  ```
  respostas_curtas: [str, str, str]
  dm_fixa: str
  comentario_keyword { texto_completo, keyword }
  ```
- **Callsite:** [claude_service.py:1202-1204](app-redator/backend/services/claude_service.py:1202). **NÃO passa brand_config** (função não aceita).

### 4.6 rc-translation

**Função `build_rc_translation_prompt` NÃO EXISTE no repo.** Verificado por `grep -rn "def build_rc_translation_prompt" .` — zero ocorrências.

**O que existe no lugar:**

- **`_build_translation_prompt` inline** em [translate_service.py:594-699](app-redator/backend/services/translate_service.py:594). Prompt em inglês, hardcoded, mono-idioma (recebe `target_lang` e gera 1 idioma por chamada). Assinatura: `(overlay_entries, post_text, target_lang, brand_slug, brand_config, research_data, protected_names)`.
- **Schema JSON esperado pelo `_build_translation_prompt`:**
  ```
  overlay: [ {index: int, text: str} ]   # text com \n para quebras
  post: str                               # string monolítica com • separadores
  ```
- **Regras no prompt inline** (linhas 608-627): RC `"Maximum 33 characters per line"`; DE/PL `"maximum 40 characters per line"`; FR/IT/ES `"maximum 38 characters per line"`. CTAs traduzidos via **`RC_CTA`** dict em [translate_service.py:37-45](app-redator/backend/services/translate_service.py:37) e **`RC_POST_CTA`** em linha 59-67.
- **Chamada:** `translate_one_claude` ([translate_service.py:702](app-redator/backend/services/translate_service.py:702)) paraleliza com `translate_project_parallel` ([translate_service.py:761](app-redator/backend/services/translate_service.py:761)) via ThreadPoolExecutor max 6 workers.
- **Fallback:** se Claude falhar, `translate_post_text` + `translate_overlay_json` usam Google Translate ([translate_service.py:91](app-redator/backend/services/translate_service.py:91)).

### Sumário de callsites (quem chama quem)

```
routers/generation.py
  └─ generate_research_rc      → prompts/rc_research_prompt.build_rc_research_prompt(metadata)
  └─ generate_hooks_rc         → prompts/rc_hook_prompt.build_rc_hook_prompt(metadata, research, brand_config)
  └─ generate_overlay_rc       → prompts/rc_overlay_prompt.build_rc_overlay_prompt(metadata, research, hook, fio, brand_config)
  └─ generate_post_rc          → prompts/rc_post_prompt.build_rc_post_prompt(metadata, research, overlay_legendas, brand_config)
                                     ↓
                                 _format_post_rc(response) → string
  └─ generate_automation_rc    → prompts/rc_automation_prompt.build_rc_automation_prompt(metadata, overlay, post_text)
                                     # post_text recebido mas não usado no prompt atual

routers/translation.py
  └─ translate_project         → services/translate_service.translate_project_parallel
                                     ↓
                                 translate_one_claude (por idioma)
                                     ↓
                                 _build_translation_prompt (inline)
                                     ↓ fallback
                                 translate_post_text + translate_overlay_json (Google)
```

**Duplicatas:** nenhuma função `build_rc_*` existe duplicada no repo. Verificado por grep.

---

## 5. Validadores de schema JSON

**NENHUM validador Pydantic/jsonschema aplicado ao output LLM dos prompts RC.**

Confirmado por: `grep -rn "BaseModel\|@validator\|pydantic" app-redator/backend/prompts/rc_*.py app-redator/backend/services/claude_service.py` — zero ocorrências. [schemas.py](app-redator/backend/schemas.py) só tem modelos Pydantic de API (request/response HTTP: `ProjectOut`, `TranslationOut`, `ApprovePostRequest`, etc), que apenas tipam `overlay_json: Optional[list]` e `post_text: Optional[str]` sem validar estrutura interna.

**Validação existente (informal / warning-only):**

- **`_validate_overlay_rc`** em [claude_service.py:1029](app-redator/backend/services/claude_service.py:1029): warnings de qualidade (linha > 40 chars, palavras compartilhadas >60% entre legendas, CTA ausente, <5 narrativas). **Não bloqueia**, só loga.
- **`_call_claude_json` (tentativa 4)**: se JSON parseing falhar em todos os fallbacks, `raise ValueError` — viável 500/502 para o frontend.
- **Shape validation implícita:** o código acessa campos esperados via `.get("campo", default)` — se o LLM não gerar `header_linha1`, vai como `""`. Silencioso.

**Consequência para patch v3/v3.1:** adicionar um campo novo ao schema (ex: `cortes_aplicados`, `save_cta`) **não causa erro** — é só "ignorado". Isso é *backward-compatible* mas também significa que dados importantes podem ser perdidos sem sinal.

---

## 6. Pós-processamento

Três pós-processadores importantes em [claude_service.py](app-redator/backend/services/claude_service.py), aplicados após o retorno do LLM:

### `_sanitize_rc(texto)` — linha 768

Determinístico, aplica em cada legenda do overlay e (via chamada explícita) no `post_text` final.

- Remove travessões (`—`, `–`) substituindo por `. ` ou `, `
- Remove metadados vazados: `\d+px`, `GANCHO`, `CORPO`, `CLÍMAX`, `FECHAMENTO`, `CTA`, `CONSTRUÇÃO`, `DESENVOLVIMENTO` (case-insensitive)
- Remove markdown: `**`, `__`, `---`, `___`, `***`
- Remove emojis **exceto ❤️**: lista hardcoded `['🎵', '🎶', '🎼', '💫', '🌟', '⭐', '🎭', '🎪']`
- Colapsa espaços múltiplos e linhas vazias consecutivas
- **Preserva** `\n` (quebras de linha intencionais) — assume entrada já com `\n` onde deve haver

### `_enforce_line_breaks_rc(texto, tipo, max_chars_linha=33, lang="pt")` — linha 819

- **Hardcode `max_chars_linha=33`** no default (CRÍTICO para v3.1)
- Idiomas verbosos ganham margem: DE/PL → +5 (máx 38), FR/IT/ES → +3 (máx 36)
- `max_linhas`: 2 para gancho/fechamento/cta, 3 para corpo
- Se já está OK (todas linhas ≤ limite e `len(linhas) <= max_linhas`), retorna sem mexer
- Se não, re-wrap: split em palavras, remontagem com preferência de quebra após pontuação (se linha ≥25 chars e termina em `,.;:`)
- Se excede `max_linhas`, trunca e loga warning

### `_process_overlay_rc(response, project)` — linha 931

Orquestra pós-processamento do overlay:

1. Extrai `response.get("legendas", [])` — **APENAS este campo é consumido**. `mapa_eventos_interno`, `verificacoes`, `pontes_planejadas`, `cortes_aplicados` são **IGNORADOS**.
2. Para cada legenda: aplica `_sanitize_rc` → `_enforce_line_breaks_rc(texto, tipo)` (33 chars hardcoded — ignora `lang` param, usa default "pt").
3. Calcula duração: `palavras / 2.5` seg, clamp 4.0-7.0s. Para CTA: `max(5.0, duracao_video * 0.13)`.
4. Constrói timestamps incrementais (gap zero entre legendas).
5. **Cap de timestamps contra duração do vídeo:** se narrativas ultrapassam `duracao_video - cta_duracao`, comprime proporcionalmente (`dur_por_legenda = cta_inicio_ideal / len(narrativas)`, clamp 4-7s). Reposiciona timestamps narrativos.
6. CTA sempre em `duracao_video - cta_duracao`.

Resultado: lista de `{text, timestamp (MM:SS), type, _is_cta, [end]}`.

### `_format_post_rc(response)` — linha 1067

**CRÍTICO para Bloco 7 (frontend).** Monta a string `post_text` a partir do JSON do LLM:

```python
lines = [h1]
if h2: lines.append(h2)
if h3: lines.append(h3)
if p1: lines.append("•"); lines.append(p1)
if p2: lines.append("•"); lines.append(p2)
if p3: lines.append("•"); lines.append(p3)
lines.append("•")
lines.append(cta)
lines.append("•"); lines.append("•"); lines.append("•")
if hashtags: lines.append(" ".join(hashtags))
return "\n".join(lines)
```

**Consome:** `header_linha1/2/3`, `paragrafo1/2/3`, `cta`, `hashtags` (list).
**NÃO consome:** `anti_repeticao`, e (se aplicado) **`hook_seo`**, **`save_cta`**, **`follow_cta`**.

**Resultado:** string com estrutura fixa — header (1-3 linhas) → `•` → P1 → `•` → P2 → `•` → P3 → `•` → CTA → `•` → `•` → `•` → hashtags. Usa `\n` único entre todas as linhas (não `\n\n`). `•` em linha própria é o separador visual.

### Pós-processamento de outras etapas

- **Research, Hooks, Automation:** sem pós-processamento. O JSON retorna direto para `project.research_data / .hooks_json / .automation_json`.
- **Hooks:** wrapper defensivo — se LLM devolver list, converte em `{"ganchos": [...], "descartados_e_motivos": []}`.
- **Translation:** pós-processamento em `translate_project_parallel` — aplica `_enforce_line_breaks_rc(texto, tipo, 33, lang=lang)` (33 hardcoded posicional) sobre cada tradução do Claude ([translate_service.py:817](app-redator/backend/services/translate_service.py:817)).

---

## 7. Frontend da descrição (ALTA CRITICIDADE)

**Onde vive:** `app-portal/` (Next.js 16 + App Router + TypeScript).

**Componente principal:** [app-portal/components/redator/approve-post.tsx](app-portal/components/redator/approve-post.tsx) (~186 linhas). Consome `post_text` (string) via prop/API.

**Como renderiza:**
- Textarea editável: `<Textarea value={postText} onChange={...} className="min-h-[500px]" />` (linhas 160-164)
- Preview: `<div className="whitespace-pre-wrap text-sm leading-relaxed">{postText}</div>` (linha 177)
- **Sem parsing, sem split, sem extração de hashtags.** A string vai inteira para o textarea e para o preview.

**Ordem atual dos campos na string final** (definida 100% por `_format_post_rc`):
1. `header_linha1`
2. `header_linha2`
3. `header_linha3` (se existe)
4. `•`
5. `paragrafo1`
6. `•`
7. `paragrafo2`
8. `•`
9. `paragrafo3`
10. `•`
11. `cta`
12. `•`, `•`, `•` (três linhas separadas)
13. hashtags (string com `" ".join()`)

**Separador:** `•` (U+2022, caractere Unicode real) em **linha própria**, não inline. Join com `\n` simples entre todas as linhas (não `\n\n`).

**Emojis:** literais Unicode; backend adiciona no header via prompt, CTA fixo em `_format_post_rc` tem `👉`. Frontend não toca.

**Persistência:** `post_text` fica em `projects.post_text` TEXT (string, não JSON) — modelo em [models.py:53](app-redator/backend/models.py:53). Traduções também em `translations.post_text` TEXT.

**Botão copiar:**
- [approve-post.tsx:95-98](app-portal/components/redator/approve-post.tsx:95) — `handleCopy() → navigator.clipboard.writeText(postText)`
- [finalizados/finalizado-card.tsx:280-283](app-portal/components/finalizados/finalizado-card.tsx:280) — botão `Copiar` em projetos finalizados

**Preview Instagram:** NÃO existe preview visual que imite o Instagram. Apenas `<div whitespace-pre-wrap>` com a string crua.

**Lógica condicional RC vs BO:**
- [approve-post.tsx:30](app-portal/components/redator/approve-post.tsx:30) — `const isRC = project?.brand_slug === "reels-classics"`
- Fluxo pós-aprovação: RC vai para `/automation` (etapa 5); BO vai para `/youtube`
- Geração: RC chama `generatePostRC()`, BO chama `regeneratePost()`

**IMPLICAÇÃO PARA PATCH:** como a montagem da string é 100% backend (`_format_post_rc`), **qualquer mudança de ordem, campo novo, ou formatação da descrição pode ser feita backend-only**. O frontend não tem lógica que reimplemente a montagem — ele confia na string.

Exceção: se o patch introduzir edição estruturada (ex: campos separados de save_cta editável), frontend precisa mudar. Mas o design atual aceita qualquer string.

---

## 8. Renderização do overlay

### Formato final

**Dois formatos gerados, papéis distintos:**

1. **SRT** — gerado por `generate_srt` em [app-redator/backend/services/srt_service.py:13](app-redator/backend/services/srt_service.py:13) (50 linhas totais). Usado para exportação (R2) e consumo pelo Editor. Duração de cada legenda = até 1s antes da próxima; última legenda até `cut_end` ou `+10s`.
2. **ASS** — gerado por `gerar_ass` em [app-editor/backend/app/services/legendas.py:291](app-editor/backend/app/services/legendas.py:291). Usado no burn-in via FFmpeg. Biblioteca `pysubs2` ([app-editor requirements](app-editor/backend/requirements.txt:9)).

### Integração Redator → Editor

- Editor recebe via `POST /api/v1/editor/importar` em [app-editor/backend/app/routes/pipeline.py](app-editor/backend/app/routes/pipeline.py). Payload inclui `overlay_json`.
- Editor armazena em DB próprio (tabela `Overlay` em `app-editor/backend/app/models/`).
- Textos também vão para R2 via `export_service.save_texts_to_r2` ([export_service.py:11](app-redator/backend/services/export_service.py:11)) — arquivos `subtitles.srt`, `post.txt`, `youtube.txt` por idioma.

### Burn-in (no editor)

FFmpeg via filtro ASS: `-vf "... ass='{ass_escaped}':fontsdir={fontsdir}"` ([pipeline.py:~2114](app-editor/backend/app/routes/pipeline.py)). Codec: libx264, CRF 18, AAC 192k.

### Fonte, cor, tamanho, posição

Definido em `ESTILOS_PADRAO` ([legendas.py:9-46](app-editor/backend/app/services/legendas.py:9)):
- Fonte: TeX Gyre Schola
- Overlay principal: 40px, branco `#FFFFFF`, outline 3px preto
- Lyrics: 30px, amarelo `#FFFF64`, outline 2px
- Tradução: 30px, branco, outline 2px, rodapé

**Customização por perfil (brand_config):** `gancho_fontsize`, `corpo_fontsize`, `cta_fontsize`, `overlay_max_chars_linha` (**default 35 no editor** — diverge do 33 gerador e do 38 target v3.1), `overlay_pre_formatted` (flag). Ver `_estilos_do_perfil` em legendas.py.

**Posicionamento dinâmico:** `image_top_px` calcula `marginv` com base na altura da imagem ([legendas.py:334-363](app-editor/backend/app/services/legendas.py)).

### Timestamps

- Gerados pelo Redator em `_process_overlay_rc` ([claude_service.py:931](app-redator/backend/services/claude_service.py:931)) — palavras/2.5, clamp 4-7s.
- Editor **NÃO recalcula**. Usa os recebidos (ordena por `_get_start_ms()` em [legendas.py:414](app-editor/backend/app/services/legendas.py:414)).
- CTA sempre empurrado para o final no Editor ([legendas.py:428-440](app-editor/backend/app/services/legendas.py:428)).

### Preview do overlay

- Endpoint no Editor: `POST /api/v1/editor/{edicao_id}/renderizar_preview` ([pipeline.py:2333](app-editor/backend/app/routes/pipeline.py)).
- Task async `_render_task(..., is_preview=True)` ([pipeline.py:1750](app-editor/backend/app/routes/pipeline.py)).
- Aprovação: `POST .../aprovar_preview` dispara render final.

### Ferramenta de burn-in

**FFmpeg único.** Nada de Remotion, OpenCV, MoviePy. Confirmado em requirements do Editor.

---

## 9. Persistência e banco

**SGBD:** PostgreSQL em produção, SQLite em dev (fallback). Definido por `DATABASE_URL` ([config.py:9](app-redator/backend/config.py:9)). `psycopg2-binary>=2.9.9` em requirements.

**ORM:** SQLAlchemy 2.0.36 com `DeclarativeBase` em [database.py:14](app-redator/backend/database.py:14).

### Tabelas relevantes ao pipeline RC

**`projects`** — [models.py:10-82](app-redator/backend/models.py:10). Campos-chave:

| Coluna | Tipo | Uso RC |
|---|---|---|
| `id` | int PK | — |
| `brand_slug` | String(50) | `"reels-classics"` para RC |
| `artist, work, composer` | String(255) | metadata |
| `cut_start, cut_end` | String(20) | MM:SS |
| `instrument_formation, orchestra, conductor` | String(255) nullable | metadata RC |
| `status` | String(50) | `input_complete | generating | awaiting_approval | translating | export_ready` |
| `overlay_json` | JSON nullable | output etapa 3 (lista de dicts) |
| `post_text` | Text nullable | output etapa 4 (string montada por `_format_post_rc`) |
| `overlay_approved, post_approved` | Boolean | gate de tradução |
| `research_data` | JSON nullable | output etapa 1 (dict estruturado) |
| `hooks_json` | JSON nullable | output etapa 2 (dict com `ganchos[]`) |
| `selected_hook` | Text nullable | escolha operador |
| `automation_json` | JSON nullable | output etapa 5 (dict) |
| `automation_approved` | Boolean | gate final |
| `scheduled_date` | Date nullable indexed | calendário |
| `r2_folder` | String(500) nullable | referência R2 |

**`translations`** — [models.py:85-97](app-redator/backend/models.py:85). Um registro por idioma por projeto.

| Coluna | Tipo |
|---|---|
| `id, project_id, language (10 chars)` | PK/FK/idioma |
| `overlay_json` | JSON nullable |
| `post_text` | Text nullable (string montada) |
| `youtube_title, youtube_tags` | Text nullable |

### Como JSON é armazenado

**Todo JSON de etapa vai em blob único (coluna JSON).** Não há colunas normalizadas para `header_linha1`, `paragrafo1`, `save_cta`, etc. — tudo mora dentro de `project.post_text` (como string montada) ou `project.overlay_json` (como lista de dicts).

**Consequência para patch:** adicionar um campo novo ao schema JSON (ex: `cortes_aplicados` no overlay v3.1, ou `save_cta` no post v3) **não requer migration de banco**. O JSON blob aceita qualquer estrutura.

### Sistema de migrations

**Não há Alembic.** Verificado por `find app-redator -name "alembic*" -o -name "migrations"` — zero resultados.

**Migrations DIY em `main.py`:**

- [main.py:24](app-redator/backend/main.py:24): `Base.metadata.create_all(bind=engine)` — cria tabelas que faltam.
- [main.py:27-67](app-redator/backend/main.py:27): função `_run_migrations()` executa ALTER TABLE condicionais no startup. Exemplos:
  ```python
  if "hook_category" not in cols:
      conn.execute(text("ALTER TABLE projects ADD COLUMN hook_category VARCHAR(50) DEFAULT ''"))
  ```
- Versões rotuladas em comentários: `v13 — RC foundation fields`, `v14 — RC metadata fields`, `v15 — Calendar`, `v16 — R2 folder`.

**Se o patch futuro precisar de coluna nova:** adicionar bloco `if "nova_coluna" not in cols: conn.execute(...)` em `_run_migrations()` no padrão existente.

Tabelas adjacentes (logs/histórico/auditoria): NÃO identificadas. Status machine é flag simples no próprio `projects.status`.

---

## 10. Internacionalização

### Como funciona

Etapa 6 disparada por `POST /api/projects/{id}/translate` em [routers/translation.py:36](app-redator/backend/routers/translation.py:36).

**Pré-requisitos RC:** `overlay_approved AND post_approved` (sem youtube — RC não tem).

**7 idiomas** (ALL_LANGUAGES em [translate_service.py:10](app-redator/backend/services/translate_service.py:10)): `["en", "pt", "es", "de", "fr", "it", "pl"]`. PT é copiado do original (não traduzido).

**Estratégia de tradução:**
1. **Claude primeiro, paralelo 6 idiomas** — `translate_project_parallel` usa `ThreadPoolExecutor(max_workers=6)` ([translate_service.py:846](app-redator/backend/services/translate_service.py:846)).
2. **Google Translate como fallback** — se Claude falha ou devolve JSON inválido.
3. Cada idioma vira 1 registro em `translations`.

**Formato final:** 7 registros separados em `translations` (não ZIP). Anexo v3 `rc_translation_prompt_v3.py` **contradiz** — seu schema devolve 1 JSON único com 7 idiomas. Ver Seção 16 para diff.

**Output storage:** textos também espelhados no R2 via `save_texts_to_r2` ([export_service.py:11](app-redator/backend/services/export_service.py:11)) — `subtitles.srt`, `post.txt`, `youtube.txt` por idioma. Editor consome.

### CTAs por idioma (hardcoded)

Existem **3 dicionários separados** em [translate_service.py](app-redator/backend/services/translate_service.py):

**`RC_CTA`** (linha 37) — overlay (com `\n`):
```
pt: Siga, o melhor da música clássica,\ndiariamente no seu feed. ❤️
en: Follow for the best of classical music,\ndaily on your feed. ❤️
es: Sigue, lo mejor de la música clásica,\na diario en tu feed. ❤️
de: Folge uns für die beste klassische Musik,\ntäglich in deinem Feed. ❤️
fr: Suis-nous pour le meilleur\nde la musique classique. ❤️
it: Seguici per il meglio della musica classica,\nogni giorno nel tuo feed. ❤️
pl: Obserwuj nas, najlepsza muzyka klasyczna\ncodziennie na Twoim feedzie. ❤️
```

**`BO_CTA`** (linha 48) — Best of Opera (fora do escopo patch RC).

**`RC_POST_CTA`** (linha 59) — descrição Instagram (com `👉`, sem `\n`):
```
pt: 👉 Siga, o melhor da música clássica, diariamente no seu feed.
en: 👉 Follow for the best of classical music, daily on your feed.
es: 👉 Sigue, lo mejor de la música clásica, a diario en tu feed.
de: 👉 Folge uns für die beste klassische Musik, täglich in deinem Feed.
fr: 👉 Suis-nous pour le meilleur de la musique classique.
it: 👉 Seguici per il meglio della musica classica, ogni giorno nel tuo feed.
pl: 👉 Obserwuj nas, najlepsza muzyka klasyczna codziennie na Twoim feedzie.
```

**Observação crítica:** DE, FR, IT, PL **JÁ têm pronomes explícitos** (`Folge uns`, `Suis-nous`, `Seguici`, `Obserwuj nas`) conforme Decisão 5 F6.8. **Decisão parcial já aplicada no código via SPEC-010 em andamento.**

### Divergência entre anexo v3 translation e `RC_POST_CTA` do repo

Comparando pontuação/texto:

| Idioma | Anexo v3 (linha 210-219) | Repo atual |
|---|---|---|
| pt | `👉 Siga, o melhor da música clássica, diariamente no seu feed.` | idem |
| en | `👉 Follow for the best of classical music daily on your feed.` | `👉 Follow for the best of classical music, daily on your feed.` (**vírgula extra**) |
| es | `👉 Síguenos para lo mejor de la música clásica en tu feed.` | `👉 Sigue, lo mejor de la música clásica, a diario en tu feed.` (**divergente**) |
| de | `👉 Folge uns für das Beste der klassischen Musik in deinem Feed.` | `👉 Folge uns für die beste klassische Musik, täglich in deinem Feed.` (**divergente**) |
| fr | `👉 Suis-nous pour le meilleur de la musique classique dans ton feed.` | `👉 Suis-nous pour le meilleur de la musique classique.` (**faltando "dans ton feed"**) |
| it | `👉 Seguici per il meglio della musica classica nel tuo feed.` | `👉 Seguici per il meglio della musica classica, ogni giorno nel tuo feed.` (**"ogni giorno" extra**) |
| pl | `👉 Obserwuj nas po najlepsze utwory muzyki klasycznej.` | `👉 Obserwuj nas, najlepsza muzyka klasyczna codziennie na Twoim feedzie.` (**divergente**) |

Decisão editorial sobre qual texto prevalece pertence ao PROMPT 2.

### Tradução do header RC

`_translate_header_rc` em [translate_service.py:343](app-redator/backend/services/translate_service.py:343) — traduz **seletivamente**:
- L1 (`[emojis] Compositor – Obra`): **não traduz** (nomes próprios)
- L2 (`Artista – instrumento [emoji]`): **traduz APENAS o instrumento**
- L3 (`Orquestra – Regente`): **não traduz**

### Tradução de hashtags

`_translate_hashtags` em [translate_service.py:320](app-redator/backend/services/translate_service.py:320). Preserva tags de marca (`bestofopera`, `reelsclassics`). Traduz demais via Google Translate, colapsa espaços.

---

## 11. Logs, observabilidade, tratamento de erros

**Biblioteca:** stdlib `logging`.

**Loggers nomeados:** `"rc_pipeline"` ([generation.py:10](app-redator/backend/routers/generation.py:10)), `"translate_claude"` ([translate_service.py:586](app-redator/backend/services/translate_service.py:586)), `logging.getLogger(__name__)` nos services.

**Destino:** stdout (gerado por Railway/Docker, capturado pela plataforma). Sem configuração explícita de handler de arquivo.

**Sentry:** opcional via env `SENTRY_DSN`. Configurado em [main.py:12-21](app-redator/backend/main.py:12-21) com `traces_sample_rate=0.1`, `environment="production"`, `server_name="redator-backend"`. Se env não existe, SDK não inicializa.

**Tratamento de erros do pipeline:**

- `_call_claude_api_with_retry` em [claude_service.py:659](app-redator/backend/services/claude_service.py:659) — 3 tentativas, backoff 10/20/30s em 529/overloaded.
- `_call_claude_json` 4 tentativas de parse (fences → braces → brackets → nova chamada).
- Endpoint handlers em [generation.py](app-redator/backend/routers/generation.py): `try/except ValueError → 502`, `try/except Exception → 500` (com check "overloaded"/"529" → 503).
- `_recover_stuck_projects` no startup ([main.py:80](app-redator/backend/main.py:80)) — projetos em `translating`/`generating` são resetados para `awaiting_approval`. Previne zombies.

**Observabilidade:** sem OpenTelemetry, sem Prometheus, sem analytics pós-publicação identificado.

---

## 12. Testes existentes

**Comando verificado:** `find app-redator -name "test_*.py" -o -name "*_test.py"` — **zero resultados.**

**Conclusão:** não há testes unitários, de integração ou E2E no `app-redator`.

**Fixtures de teste (metadata, pesquisa, overlay de exemplo):** não identificadas.

**CI/CD:** `ls -la .github/workflows/` retornou vazio/inexistente (o comando saiu com exit code 1). Nenhum test rodando em CI.

**Implicação para patch:** teste de regressão do pipeline terá que ser construído do zero no PROMPT 2, ou executado manualmente (smoke tests via cURL nos endpoints).

---

## 13. Deploy, branches e ambientes

**Git:** branch principal `main` (confirmado pelo contexto).

**Deploy:** Railway, configurado via [app-redator/railway.json](app-redator/railway.json):
```json
{
  "build": {"builder": "DOCKERFILE", "dockerfilePath": "app-redator/Dockerfile"},
  "deploy": {"numReplicas": 1, "restartPolicyType": "ON_FAILURE", "restartPolicyMaxRetries": 3}
}
```

**Dockerfile** ([app-redator/Dockerfile](app-redator/Dockerfile)): multistage:
1. Frontend build: `node:18-slim` → `npm ci && npm run build` (em `app-redator/frontend/`)
2. Backend run: `python:3.11-slim` → `pip install` + copia `backend/` + copia `shared/` + copia `frontend/dist/`
3. CMD: `uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}`

**Procfile:** `web: uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}` (para fallback/outras plataformas).

**Como código entra em produção:** presumivelmente `git push → Railway auto-deploy` (padrão Railway). Não há workflow de release manual confirmado.

**Staging:** não identificado no repo. CLAUDE.md menciona "Railway horizontal scaling" como decisão fechada. `RAILWAY_ENVIRONMENT` env var pode diferenciar.

**Rollback:** via UI Railway (plataforma). Não há script de rollback explícito no repo.

---

## 14. Secrets e configuração

**Secrets (env vars):**
- `DATABASE_URL` — banco (default SQLite local)
- `ANTHROPIC_API_KEY` — Claude
- `GOOGLE_TRANSLATE_API_KEY` — Google Translate v2
- `GOOGLE_APPLICATION_CREDENTIALS` — path para JSON GCP (pode estar não-usado no caminho RC)
- `EXPORT_PATH` — path opcional local
- `EDITOR_API_URL` — URL do app-editor (com auto-detect Railway)
- `RAILWAY_ENVIRONMENT`, `RAILWAY_PROJECT_ID` — detecção ambiente
- `SENTRY_DSN` — observabilidade (opcional)
- `ALLOWED_ORIGINS` — CORS
- `PORT` — uvicorn
- `BRAND_SLUG` — opcional sem default (multi-brand)

Todos via `os.getenv()` com defaults em [config.py](app-redator/backend/config.py). Arquivo `.env` via `python-dotenv`.

**Configs não-secretas:**
- `HOOK_CATEGORIES` em [config.py:65-213](app-redator/backend/config.py:65) — 10 categorias hardcoded com labels/emojis/prompts. SPEC-010 Bloco 4 pretende migrar para banco (`app_config` tabela), mas **ainda pendente**.
- `brand_config` via `load_brand_config(slug)` — HTTP call para `{EDITOR_API_URL}/api/internal/perfil/{slug}/redator-config` com cache 5min. Retorna dict com `identity_prompt_redator`, `tom_de_voz_redator`, `escopo_conteudo`, `overlay_cta`, `overlay_max_chars`, `overlay_interval_secs`, `r2_prefix`, etc. Se editor offline, `HTTPException(503)`.

**Rotação de secrets:** manual via Railway dashboard. Nenhum vault interno.

**Secret não-óbvio:** `_SENTRY_DSN` em [main.py:12](app-redator/backend/main.py:12) — se env existe, init Sentry; se não, silenciosamente pula. Não há logging de "Sentry ativado".

---

## 15. Dependências e versões

**Gerenciador:** `pip` + `requirements.txt` (não poetry/uv).

**Arquivo:** [app-redator/requirements.txt](app-redator/requirements.txt) (12 linhas). Principais:

```
fastapi==0.115.6
uvicorn[standard]==0.34.0
sqlalchemy==2.0.36
anthropic==0.42.0
python-dotenv==1.0.1
aiofiles==24.1.0
pydantic[email]==2.10.3
python-multipart==0.0.20
requests>=2.31.0
psycopg2-binary>=2.9.9
boto3>=1.34.0
sentry-sdk[fastapi]>=2.0.0
```

**Versões travadas:** principais libs fixas (`==`). Auxiliares flexíveis (`>=`).

**Versão anthropic SDK:** `0.42.0` — relativamente recente, suporta Claude 4.x. Sem risco imediato de quebra por API change.

**Dep obsoleta/risco:** não identificada. `sqlalchemy 2.x` e `pydantic 2.x` (compatíveis com `DeclarativeBase` e `model_config`/`model_validator` usados em [models.py](app-redator/backend/models.py) e [schemas.py](app-redator/backend/schemas.py)).

---

## 16. Diff simbólico — estado atual vs anexos v3/v3.1

### 16.1 `rc_overlay_prompt_v3_1.py` (anexo D.3)

- **Path anexo:** [docs/rc_v3_migration/rc_overlay_prompt_v3_1.py](docs/rc_v3_migration/rc_overlay_prompt_v3_1.py)
- **Path repo alvo:** [app-redator/backend/prompts/rc_overlay_prompt.py](app-redator/backend/prompts/rc_overlay_prompt.py)
- **SHA256 anexo:** `a2c9f66d7e42998e0bb975350f9489d6cd3bbf224d18facf06fb69d2cc91aabf`
- **SHA256 repo:** `2ab8267f22c2c9449afb63e465981f7b9b9249857f09817e393e25c757160486`
- **wc -l:** anexo 698 linhas; repo 441 linhas (diff net +257 linhas)
- **`diff -u` lines +/-:** 1141 linhas (add+remove, sem contar cabeçalho @@)

**Principais mudanças (anexo v3.1 → repo):**

- **Assinatura mudou:** anexo remove `brand_config`, adiciona `hook_tipo=""`.
  ```
  Repo:  build_rc_overlay_prompt(metadata, research_data, selected_hook, hook_fio_narrativo="", brand_config=None)
  Anexo: build_rc_overlay_prompt(metadata, research_data, selected_hook, hook_fio_narrativo="", hook_tipo="")
  ```
- **Helper mudou:** anexo usa `_estimar_faixa_legendas(duracao) -> tuple(min, max)` em vez de `_estimar_legendas(duracao) -> int`.
- **38 chars por linha:** em vez de 33 no repo. Literal no prompt: *"38 CARACTERES POR LINHA como REFERÊNCIA"*.
- **Seções novas** no anexo:
  - `<duracao_dinamica>` — regra 4-6s por legenda, elimina tabela fixa.
  - `<fio_narrativo_dinamico>` — fio dinâmico com detecção de esgotamento e transição para fio complementar.
  - `<oralidade>` — lista operacional de substituições de vocabulário (escreveu→contou, estava doente→lutava contra...).
  - `<anti_padroes_nomeados>` — 8 padrões IA nomeados explicitamente.
- **Campo novo no schema JSON:** `verificacoes.cortes_aplicados[]` (rastreamento antidescarte silencioso). Novos campos auxiliares: `fio_unico_identificado`, `pontes_planejadas[]`, `verificacoes.fio_unico_respeitado`, `pontes_causais_inseridas`, `ancoragens_causais`, `ancoragens_descritivas`, `cenas_especificas`, `gancho_fechamento_ecoam`.
- **Fase 2 nova:** "Gerar 3 versões variadas" (dimensões A Ritmo + B Foco + C Revelação).
- **Arcos-ouro trocados:** anexo usa Beethoven/Roman Kim + Liszt/Lisitsa (14 e 16 legendas); repo usa Mozart/Réquiem + La Campanella (mesmo Liszt).
- **Rubric expandida para 11 dimensões** (Fase 3 Autocrítica).
- **11 verificações V1-V11** em Fase 5 (vs 6 no repo).

**Campos do JSON do anexo que NÃO existem no prompt do repo:**
- `fio_unico_identificado`, `pontes_planejadas`, `cortes_aplicados`, `fio_unico_respeitado`, `pontes_causais_inseridas`, `ancoragens_causais` (vs `ancoragens_ao_video` no repo), `ancoragens_descritivas`, `cenas_especificas`, `gancho_fechamento_ecoam`.

**Consumo no pós-processamento:** `_process_overlay_rc` **só consome `legendas[]`** — novos campos seriam persistidos em `overlay_json` (coluna JSON) mas sem uso. Logicamente compatível (não quebra), mas `cortes_aplicados` não chega a lugar nenhum.

### 16.2 `rc_automation_prompt_v3.py` (anexo D.2)

- **Path anexo:** [docs/rc_v3_migration/rc_automation_prompt_v3.py](docs/rc_v3_migration/rc_automation_prompt_v3.py)
- **Path repo alvo:** [app-redator/backend/prompts/rc_automation_prompt.py](app-redator/backend/prompts/rc_automation_prompt.py)
- **SHA256 anexo:** `dce13a10b77ae0314d5ff5b50860db5bf48bcf3d4cad448e886b54226bbae7eb`
- **SHA256 repo:** `173ecf5dd18c4eeacfed635a0e91cdcb6cd99359151b80145da2ec9b53a5f624`
- **wc -l:** anexo 233; repo 193 (diff net +40)
- **`diff -u` lines +/-:** 194

**Principais mudanças:**

- **Assinatura IDÊNTICA:** `(metadata, overlay_legendas, post_text)`. Sem `brand_config` nos dois.
- **`post_text` agora é USADO no prompt** (fix F5.2): anexo adiciona bloco `DESCRIÇÃO APROVADA:` dentro do `<context>` com `post_summary` (truncado em 500 chars com `...` se necessário). No repo, `post_text` é parâmetro morto.
- **`genre_map` levemente diferente:** anexo usa `"do repertório pianístico"` (com "do"), repo usa `"repertório pianístico"` (sem "do"). Diferenças pequenas em todas as categorias.
- **Estratégias A/B/C nomeadas** em `<task>`:
  - A: por tom (informativa/poética/provocadora)
  - B: por aspecto (compositor/peça/intérprete)
  - C: por verbo (verbos diferentes de envio)
  - Prompt instrui declarar a estratégia explicitamente.
- **Novo campo no schema:** `estrategia_diversidade_aplicada: "A|B|C"`.
- **Exemplos atualizados** — dois exemplos bons com estratégia explicitada + 1 exemplo ruim (falha diversidade).

**Campos novos:** `estrategia_diversidade_aplicada`.

**Consumo downstream:** `generate_automation_rc` persiste `result` inteiro em `project.automation_json`. Campo novo é persistido mas não processado especificamente.

### 16.3 `rc_translation_prompt_v3.py` (anexo D.1)

- **Path anexo:** [docs/rc_v3_migration/rc_translation_prompt_v3.py](docs/rc_v3_migration/rc_translation_prompt_v3.py)
- **Path repo alvo:** **NÃO EXISTE.** Função `build_rc_translation_prompt` não existe no repo.
- **SHA256 anexo:** `7416368b48b52610900ff468446dccd4512b573911811b71d65381f46f45e94f`
- **wc -l anexo:** 513

**Implementação atual no repo (substituto):**
- [translate_service.py:594-699](app-redator/backend/services/translate_service.py:594) — `_build_translation_prompt` inline (em inglês, hardcoded, mono-idioma por chamada).

**Diferenças estruturais:**

| Dimensão | Anexo `build_rc_translation_prompt` | Repo `_build_translation_prompt` |
|---|---|---|
| Assinatura | `(metadata, overlay_aprovado, descricao_aprovada)` | `(overlay_entries, post_text, target_lang, brand_slug, brand_config, research_data, protected_names)` |
| Idiomas | 7 simultâneos (1 chamada, output com 7 overlays + 7 descrições) | 1 por chamada, paralelizado externamente |
| Linguagem prompt | Português | Inglês |
| Schema de `descricao_aprovada` | `{hook_seo, header_linha1/2/3, paragrafo1/2/3, save_cta, follow_cta, hashtags}` (campos estruturados) | `post_text: str` (string monolítica) |
| Limite chars | 38/linha REGRA DURA nas traduções | 33 RC (com margens 36/40 por idioma) |
| Regra PT | `<regra_pt_intocavel>` explícita: copiar identicamente | implícita (PT é cópia direta) |
| CTAs por idioma | 7 idiomas overlay + 7 descrição (tabela inline) | `RC_CTA` (overlay) e `RC_POST_CTA` (post) hardcoded em arquivo separado |
| Vocabulário banido | Por idioma (en/es/de/fr/it/pl) — 6 blocos | Não presente (só menciona "don't use clichés") |
| Output format | JSON único com `overlays{}`, `descricoes{}`, `verificacoes{}` | JSON simples `{overlay:[...], post:str}` |
| Campo alertas | `verificacoes.legendas_com_linha_excedendo_38_chars`, `verificacoes.linhas_reformuladas_por_idioma`, `alertas[]` | não há |

**Contradição crítica detectada:**

O anexo v3 pressupõe que `descricao_aprovada` tem o campo `hook_seo`:
```python
# linha 42 do anexo
descricao_aprovada: dict com estrutura v3:
    {hook_seo, header_linha1, header_linha2, header_linha3,
     paragrafo1, paragrafo2, paragrafo3, save_cta, follow_cta, hashtags}
```

Mas [RELATORIO_LOTES_A_B_C_F.md:70-74](docs/rc_v3_migration/RELATORIO_LOTES_A_B_C_F.md:70) explicitamente diz **F4.2 (HOOK-SEO antes do header) foi DESCARTADA** pelo operador. Logo o prompt `rc-post_SKILL.md` (Lote B) NÃO gera `hook_seo`. O Translation v3 vai receber JSON sem `hook_seo` e pode falhar ou tratar como "" vazio.

**Decisão necessária no PROMPT 2:** ajustar `rc_translation_prompt_v3.py` para não pressupor `hook_seo`, OU reverter F4.2 decisão e manter.

**Contrato de chamada:** o site hoje passa `post_text: str` (string monolítica) para tradução — o `_build_translation_prompt` atual **NÃO decompõe** em campos estruturados. Se o anexo v3 for adotado, precisa:
- OPÇÃO A: adicionar `rc_translation_prompt.py` + criar wrapper que primeiro extrai os campos da string `post_text` (reverse-engineering do `_format_post_rc`), depois invoca o prompt v3.
- OPÇÃO B: alterar o pipeline para persistir o JSON do post separadamente do `post_text` string, e alimentar o tradutor com o dict.
- OPÇÃO C: manter `_build_translation_prompt` atual e incorporar regras v3 (38 chars, vocabulário banido, CTAs novos) sem mudar o fluxo.

### Resumo comparativo

| Patch | Arquivo repo | Existe? | Mudança estrutural | Schema JSON novo | Consumo downstream precisa mudar |
|---|---|---|---|---|---|
| D.3 overlay v3.1 | `rc_overlay_prompt.py` | SIM | alta (assinatura + seções novas + 38 chars) | `cortes_aplicados`, `fio_unico_identificado`, etc | `_process_overlay_rc` precisa ler `cortes_aplicados`; `_enforce_line_breaks_rc` precisa aceitar 38 chars (hoje default 33) |
| D.2 automation v3 | `rc_automation_prompt.py` | SIM | baixa (campo `post_text` passa a ser usado, genre_map tweaks, estratégias A/B/C) | `estrategia_diversidade_aplicada` | nenhuma mudança no backend; `automation_json` já armazena tudo |
| D.1 translation v3 | — | **NÃO** | nova função com schema v3 esperado | JSON agregado com 7 idiomas + verificações | decisão arquitetural (A/B/C acima) |

---

## 17. Contratos implícitos identificados

Contratos que o sistema atual assume mas **não estão documentados** em código nem em schema:

1. **`_format_post_rc` assume ordem fixa dos campos** (h1→h2→h3→p1→p2→p3→cta→hashtags) com separador `•` em linha própria. Adicionar `save_cta` requer inserir campo + lógica nesse montador, **senão o campo fica no JSON mas invisível na string final**.

2. **`_process_overlay_rc` consome APENAS `response.get("legendas", [])`**. Outros campos top-level do JSON v3.1 (`fio_unico_identificado`, `pontes_planejadas`, `verificacoes.cortes_aplicados`) são **silenciosamente ignorados**. São persistidos em `overlay_json` (toda estrutura dentro de `legendas`), mas não no `verificacoes`. Para usar `cortes_aplicados` em algum downstream (ex: display para operador revisar cortes), é preciso: (a) alterar `_process_overlay_rc` para preservar campo, (b) persistir separadamente ou dentro de `project.overlay_json`, (c) expor via `ProjectOut`.

3. **`_enforce_line_breaks_rc` usa `max_chars_linha=33` como default posicional**. Mesmo que o prompt diga "38 chars", o re-wrap pós-LLM vai reformatar para 33 se o terceiro argumento não for passado. Callsites explícitos com `33` literal em [translate_service.py:555](app-redator/backend/services/translate_service.py:555), [translate_service.py:817](app-redator/backend/services/translate_service.py:817), e implícito em [claude_service.py:948](app-redator/backend/services/claude_service.py:948) (chamado em `_process_overlay_rc` sem passar o 3º arg).

4. **`ESTILOS_PADRAO.overlay_max_chars_linha = 35` no editor** (vs 33 no redator). Divergência de 2 chars. Se editor roda wrap próprio em runtime, legendas podem ser reformatadas visualmente na renderização final do vídeo. Isso já acontece hoje mas não foi identificado como bug.

5. **O parâmetro `post_text` em `build_rc_automation_prompt` é aceito mas ignorado no prompt.** Caller ([claude_service.py:1202-1204](app-redator/backend/services/claude_service.py:1202)) passa valor; prompt atual descarta. Anexo v3 corrige. Se algum outro chamador assumia que post_text era usado (não identificado), comportamento muda.

6. **O frontend assume que `post_text` é uma string montada pelo backend**, sem lógica de reconstrução. Se o banco tiver `post_text` null e só o JSON estruturado (hipotético), o frontend mostra vazio. Qualquer refactor que adicione campos separados precisa manter `post_text` como string válida OU adicionar frontend para montagem.

7. **`_build_translation_prompt` (inline) passa `post_text` ao LLM como string monolítica** e pede retorno como string. Se o prompt v3 esperar JSON estruturado de `descricao_aprovada`, e o caller continuar passando string, há mismatch. O pipeline NÃO decompõe `post_text` em campos automaticamente.

8. **Tradução chama `RC_CTA.get(lang, RC_CTA.get("en", t_text))`** — se um idioma não está no dict, cai para EN. Se adicionar novo idioma no futuro sem atualizar `RC_CTA`, silenciosamente usa inglês.

9. **Schema de hook `(hooks_json)` é `{ganchos[], descartados_e_motivos[]}`**, mas SKILL F₂ (`rc-hooks_SKILL.md`) menciona campo `analise_diversidade.todos_diferentes: boolean` que bloqueia retorno se false. Esse campo **não existe no prompt repo atual nem no consumo downstream** — se for adicionado, ninguém valida.

10. **Migrations DIY em `_run_migrations()` ([main.py:27](app-redator/backend/main.py:27))** — precisam ser atualizadas manualmente sempre que adicionar coluna. Não há hash/versão tracking, só `if col not in cols`. Adicionar coluna nova sem atualizar função = coluna nunca existe em prod.

---

## 18. Ambiguidades e lacunas

1. **Papel do `app-redator/frontend/` (SPA interno)** — Dockerfile constrói como parte do redator, mas o app-portal é o front "oficial" para RC. Não foi esclarecido se o frontend interno do redator ainda tem rotas ativas para RC ou só para BO/pipeline antigo. Fora de escopo desta investigação.

2. **Status real do SPEC-010 BLOCO 1** — checklist indica concluído, mas alguns itens (T4, T10, T11) foram removidos/simplificados. `overlay_cta` foi implementado mas "`brand_cta` nas traduções" foi removido. Precisa confirmação do operador se os CTAs hardcoded em `RC_CTA`/`RC_POST_CTA` são "canônicos" ou se o brand_config já tem esse texto.

3. **Contradição `hook_seo` (Lote B descartou) × anexo translation v3 (pressupõe)** — já levantada. Decisão pendente.

4. **Campo `cortes_aplicados` tem destino?** O anexo v3.1 exige registro, mas o frontend/banco não tem lugar para exibir ao operador. Sem destino, é apenas flag diagnóstica. PROMPT 2 deve definir se vai só persistir ou se deve exibir.

5. **Instrução na seção 9 do PROMPT_1_INVESTIGACAO.md** menciona "inversão da ordem para HOOK-SEO vir antes do header" como mudança antecipada do PROMPT 2. Isso **contradiz Lote B**. Provável que PROMPT 1 tenha sido escrito ANTES da decisão de descartar F4.2; relatórios posteriores resolveram. Registrar como "decisão superada" no briefing do PROMPT 2.

6. **Sem testes no repo** — impossível validar patches por regressão automatizada antes de executar. PROMPT 2 precisará de smoke tests manuais (cURL).

7. **Nenhum histórico de rollbacks** de prompts (sem `rc_overlay_prompt_v2.py` legado). Quem for reescrever precisa cuidar de não perder especificidade que já foi ganha.

8. **`app-editor/` tem cópia do prompt ou só consome artefato?** Glob encontrou zero `rc_*_prompt.py` em app-editor. Editor só consome `overlay_json` via HTTP. Sem duplicação de prompt — positivo.

---

## 19. Riscos identificados para o patch futuro

Classificação: **crítico** / **alto** / **médio** / **baixo**.

### CRÍTICO

- **R1. Assinatura do `build_rc_overlay_prompt` muda** — aplicar v3.1 sem ajustar [claude_service.py:1159-1163](app-redator/backend/services/claude_service.py:1159) quebra a chamada. Repo passa `brand_config=brand_config`; anexo espera `hook_tipo=""`. Exige ajuste simultâneo em prompt + callsite.

- **R2. `_enforce_line_breaks_rc` reimpõe 33 chars** mesmo se prompt pedir 38. Mudança de prompt sem mudança do default na função = efeito nulo. 4 callsites explícitos passam `33` literal e precisam ser atualizados **OU** a função precisa ter default atualizado.

- **R3. Contradição `hook_seo` entre translation v3 e post v3** — se translation for aplicada como está, precisa de `hook_seo` na input; se post mantém decisão Lote B (sem hook_seo), translation trata como vazio e pode gerar erros de layout ou traduções incorretas. **Decisão editorial prévia obrigatória** antes de patch.

### ALTO

- **R4. `_format_post_rc` não consome `save_cta`** — aplicar schema v3 do post sem atualizar `_format_post_rc` faz o campo virar fantasma. Operador verá JSON novo, mas string final idêntica à v2.

- **R5. `rc_translation_prompt.py` não tem caller** — adicionar o arquivo sem decidir OPÇÃO A/B/C (ver Seção 16.3) não muda nada. Exige decisão arquitetural.

- **R6. Novos campos de `verificacoes.cortes_aplicados` ficam órfãos** — sem consumidor downstream, equivale a trabalho do LLM descartado. Não quebra, mas defeat-the-purpose. Patch completo precisa definir destino.

- **R7. Warnings de 40 chars em `_validate_overlay_rc`** ([claude_service.py:1038](app-redator/backend/services/claude_service.py:1038)) continuariam disparando em legendas de 38 chars (limite v3.1), mas são warnings não-bloqueantes. Baixo risco funcional; ruído em logs.

### MÉDIO

- **R8. Tradução via `_build_translation_prompt` inline tem regras contraditórias ao v3.1** — "Maximum 33 characters per line" (linha 611 de translate_service.py) conflita com 38 chars do v3.1. Mesmo se o prompt RC overlay for atualizado para 38, traduções continuarão geradas em 33 porque o prompt de tradução é independente.

- **R9. Migrations DIY em main.py** — se novo campo precisar de coluna (provavelmente NÃO, dado blob JSON), lembrar de adicionar no `_run_migrations()`. Ou risco de produção falhar em deploy.

- **R10. Divergência CTA anexo vs repo** (Seção 10) — 6 idiomas têm diferenças de pontuação/texto entre anexo v3 e `RC_CTA`/`RC_POST_CTA`. Operador precisa decidir qual é "canônico" ou se anexo deve ajustar ao repo.

- **R11. Sem testes automatizados** — patches produzirão regressão sem detecção. Necessita smoke tests manuais em PROMPT 2.

### BAIXO

- **R12. Mudança de `genre_map` em automation v3** — anexo adiciona "do/da/de" nos rótulos. Operador pode ter preferência por uma forma ou outra. Trivial revisar.

- **R13. Exemplos canônicos trocados** (Mozart → Beethoven/Liszt) no overlay v3.1 — não afeta comportamento, só o que o LLM "estuda" in-prompt. Se mudou exemplos, tom do output pode derivar levemente.

- **R14. Estratégia A/B/C na automation v3 exige declaração explícita** — se LLM não declarar, `estrategia_diversidade_aplicada` vem vazio ou ausente. Persistido mas sem uso crítico.

---

## 20. Proposta de ordem de patches

Baseada nas dependências reais descobertas. Objetivo: minimizar sessões de regressão acumulada, permitir verificação parcial, e respeitar dependências de dados.

### Fase pré-patch (decisões editoriais necessárias)

1. **Resolver contradição `hook_seo`** (Lote B descartou × Translation v3 pressupõe). Decisão: descartar de Translation v3 também.
2. **Definir destino de `cortes_aplicados`** (só log? exibir ao operador no frontend?).
3. **Decidir arquitetura de Translation v3** (A: novo prompt + wrapper; B: mudar schema de persistência; C: adaptar `_build_translation_prompt` inline).
4. **Resolver divergência CTA anexo v3 vs `RC_CTA`/`RC_POST_CTA`** (Seção 10).

### Fase de patches (ordem proposta)

**P1. Atualizar `_enforce_line_breaks_rc` para suportar 38 chars** (preparatório)
- Arquivos: [app-redator/backend/services/claude_service.py:819](app-redator/backend/services/claude_service.py:819)
- Mudança: default `max_chars_linha` 33→38, ajustar margens verbosas se necessário.
- Ajustar callsites posicionais (33 literal): [translate_service.py:555](app-redator/backend/services/translate_service.py:555), [translate_service.py:817](app-redator/backend/services/translate_service.py:817), [routers/translation.py:189](app-redator/backend/routers/translation.py:189).
- Ajustar prompt inline: [translate_service.py:611](app-redator/backend/services/translate_service.py:611).
- Ajustar warning threshold: [claude_service.py:1038](app-redator/backend/services/claude_service.py:1038) (40→~45).
- **Razão de ser primeiro:** mudanças de prompt seguintes dependem que 38 chars seja a constante real do sistema; senão re-wrap desfaz.

**P2. Aplicar `rc_automation_prompt_v3.py`** (baixo risco, mudança isolada)
- Arquivos: substituir [app-redator/backend/prompts/rc_automation_prompt.py](app-redator/backend/prompts/rc_automation_prompt.py) pelo anexo.
- Callsite em [claude_service.py:1202](app-redator/backend/services/claude_service.py:1202) já passa os 3 args certos — sem mudança.
- Schema `automation_json` recebe `estrategia_diversidade_aplicada` — persistido em blob, nada quebra.
- **Verificação:** rodar `generate-automation-rc` num projeto-teste, verificar que `automation_json` contém `estrategia_diversidade_aplicada` e o bloco `DESCRIÇÃO APROVADA:` aparece no prompt log.

**P3. Aplicar `rc_overlay_prompt_v3_1.py` + ajustar callsite + _process_overlay_rc**
- Substituir [app-redator/backend/prompts/rc_overlay_prompt.py](app-redator/backend/prompts/rc_overlay_prompt.py) pelo anexo.
- Renomear arquivo para manter `rc_overlay_prompt.py` (não `_v3_1.py`) para não mudar import.
- Ajustar callsite [claude_service.py:1159-1163](app-redator/backend/services/claude_service.py:1159) — remover `brand_config=brand_config`, adicionar `hook_tipo` do hook selecionado.
- Atualizar `generate_overlay_rc` para buscar `hook_tipo` em `hooks_json.ganchos[i].tipo`.
- Opcional: atualizar `_process_overlay_rc` para ler `verificacoes.cortes_aplicados` e preservar em resultado final (se decisão pré-patch pedir).
- Também ajustar prompt hardcoded em [generation.py:210](app-redator/backend/routers/generation.py:210): `"Máximo 33 caracteres por linha"` → 38.
- **Verificação:** rodar `generate-overlay-rc` num projeto-teste, verificar que overlay tem 38 chars/linha, novos campos JSON presentes, e pipeline não quebra.

**P4. Aplicar `rc_translation_prompt_v3.py`** (dependente de decisão arquitetural)
- Se OPÇÃO A: adicionar arquivo novo em `app-redator/backend/prompts/rc_translation_prompt.py`, criar wrapper em `claude_service.py` (ou `translate_service.py`) que decompõe `post_text` string em dict via reverse-engineering do `_format_post_rc`, invoca o prompt, e processa resultado.
- Se OPÇÃO C: adaptar `_build_translation_prompt` inline para incorporar as regras (vocabulário banido, 38 chars, CTAs v3 atualizados).
- Atualizar `RC_CTA`/`RC_POST_CTA` para alinhar com decisão editorial (Seção 10).
- **Verificação:** rodar `/translate` em projeto-teste, verificar que todas as 6 traduções respeitam 38 chars e têm CTAs corretos por idioma.

**P5. Ajustes frontend (se decididos nas questões pré-patch)**
- Se `save_cta` for editável separadamente na UI: modificar [app-portal/components/redator/approve-post.tsx](app-portal/components/redator/approve-post.tsx).
- Se não: skip. Backend-only.

**P6. Teste de regressão E2E**
- Rodar pipeline completo em projeto-teste Beethoven/Roman Kim (referência de arcos-ouro).
- Verificar: research → hooks → overlay (38 chars, `cortes_aplicados`) → post (save_cta presente em `_format_post_rc` se aplicado) → automation (estratégia declarada) → translate (6 idiomas, CTAs v3).
- Validar que nenhum campo vaza/some.

### Justificativa da ordem

- **P1 primeiro** desacopla a mudança de chars de todos os patches seguintes. Sem P1, P3 seria parcialmente reverso por re-wrap.
- **P2 antes de P3** porque automation é mais baixo risco e isolado; serve como "warm-up" para garantir que o fluxo de commit/deploy/smoke test funciona antes de atacar overlay.
- **P3 antes de P4** porque translation consome `overlay_json` (pós-P3) e `post_text` (pós-P2 parcial). Overlay atualizado produz dados v3.1 que translation v3 espera.
- **P4 por último** porque depende das decisões arquiteturais e integra-se com o editor no final do pipeline (export R2 → SRT → burn-in).
- **P5 só se necessário** — backend-only é o caminho preferido; frontend só se precisar editar campos separadamente.

---

## Anexos

### Arquivos lidos durante investigação

Ver `mapa_paths.txt` (companion).

### Comandos read-only executados

- `Glob`, `Grep`, `Read` em cada path citado.
- `find app-redator -name "*.py"` — topologia.
- `sha256sum` dos 3 anexos v3/v3.1 e 2 arquivos do repo correspondentes.
- `diff -u` (contagem linhas) entre anexos e repo.
- `wc -l` para linha counts.
- Nenhuma chamada a LLM, nenhum `pip install`, nenhum acesso a banco de produção, nenhuma modificação fora de `docs/rc_v3_migration/RELATORIO_INVESTIGACAO.md` e `docs/rc_v3_migration/mapa_paths.txt` (este relatório + companion).

### Entregáveis desta sessão

1. `docs/rc_v3_migration/RELATORIO_INVESTIGACAO.md` (este arquivo)
2. `docs/rc_v3_migration/mapa_paths.txt` (lista plana de paths RC-relevantes)
3. Nenhum commit. Nenhum patch. Nenhuma mudança em código.

**Fim do relatório.**
