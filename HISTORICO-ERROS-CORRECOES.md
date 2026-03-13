# Histórico Completo de Erros e Correções — App-Editor (Best of Opera)

**Gerado em:** 03 de março de 2026 (atualizado 09/03/2026 — BLAST v3)
**Projeto:** Best of Opera — App-Editor (APP3) + App-Redator (APP2)

---

## Fase 15 — 3 bugs: título Redator, instrumental, primarycolor (12/03/2026)

### ERR-067 · Título YouTube mostra "# Resposta:" em vez do título real

- **Sintoma:** Campo título na tela "Aprovar YouTube" exibia `# Resposta:` — header markdown do Claude
- **Causa raiz:** `generate_youtube()` em `claude_service.py` fazia `lines[0]` no response do Claude. Claude às vezes retorna markdown headers como preamble.
- **Arquivos corrigidos:** `app-redator/backend/services/claude_service.py` (adicionada `_strip_markdown_preamble()`), `app-redator/backend/prompts/youtube_prompt.py` (prompt reforçado)
- **Correção (12/03/2026):** Sanitização do output (remove `#` headers e labels) + reforço no prompt ("Do NOT use markdown")

### ERR-068 · Instrumental entra no pipeline de letra/transcrição/tradução

- **Sintoma:** Músicas instrumentais (Für Elise) passavam por busca de letra, transcrição, alinhamento. Gemini retornava "Esta peça é instrumental..." que era tratada como lyrics.
- **Causa raiz:** Flags `sem_lyrics` e `eh_instrumental` eram setadas no import mas ignoradas em todos os passos subsequentes (7 pontos pós-download, endpoints de letra, corte→tradução)
- **Arquivos corrigidos:** `app-editor/backend/app/routes/pipeline.py` (helper `_set_post_download_state()`, guards em letra, skip tradução), `app-portal/components/editor/validate-lyrics.tsx` (redirect)
- **Correção (12/03/2026):** Download → passo 5 (corte) direto. Guards em buscar/aprovar letra. Corte pula tradução → montagem. Frontend redireciona para conclusão.

### ERR-069 · KeyError 'primarycolor' no render de perfil com estilo vazio

- **Sintoma:** Render falhava com `'primarycolor'` para perfil Reels Classics
- **Causa raiz:** `_estilos_do_perfil()` usava `perfil.overlay_style or ESTILOS_PADRAO["overlay"]`. Dict vazio `{}` é truthy em Python, não caia no fallback. Depois `config["primarycolor"]` dava KeyError.
- **Arquivos corrigidos:** `app-editor/backend/app/services/legendas.py`
- **Correção (12/03/2026):** Merge: `ESTILOS_PADRAO` como base + `perfil_style.update()` sobrescreve. Dicts vazios, parciais ou None todos cobertos.

---

## Fase 14 — Sentry coverage + bugfix (11/03/2026)

### ERR-066 · NameError 'falhas' em _traducao_task

- **Sintoma:** `NameError: name 'falhas' is not defined` — task de tradução falhava no log final após retry
- **Causa raiz:** Linha 1379 de `pipeline.py` referenciava `falhas` (nome da variável em `_render_task`), mas em `_traducao_task` a variável se chama `falhas_finais`
- **Arquivos corrigidos:** `app-editor/backend/app/routes/pipeline.py:1379`
- **Correção (11/03/2026):** `len(falhas)` → `len(falhas_finais)` no log de conclusão da task de tradução
- **Detectado via:** Sentry PYTHON-FASTAPI-7 (4 ocorrências, 11/03/2026)

---

## Fase 13 — BLAST v3: Expansão do Pipeline (09/03/2026)

### ERR-056 · cobalt.tools ausente como fonte de download primária

- **Sintoma:** Pipeline dependia de yt-dlp diretamente (limitado por bloqueios do YouTube) e curadoria como segunda opção, sem aproveitar cobalt.tools que tem alta taxa de sucesso e qualidade
- **Causa raiz:** `_download_task` não incluía cobalt na cascata de fallbacks
- **Arquivos corrigidos:** `pipeline.py`, `config.py`, `.env.example`
- **Correção (09/03/2026):**
  - Adicionada variável `COBALT_API_URL` em `config.py` (default: `https://api.cobalt.tools`)
  - Implementada `_download_via_cobalt()`: `POST /` com `{"url": ..., "videoQuality": "1080"}`, suporta resposta `tunnel`/`redirect`
  - Implementada `_download_via_ytdlp()` como último fallback antes do erro
  - Cascata final: local → R2 → cobalt → curadoria → yt-dlp → erro
- **Status: ✅ CORRIGIDO**

### ERR-057 · Pacote ZIP rodava em BackgroundTasks (preso em background sem worker)

- **Sintoma:** `_gerar_pacote_background` era síncrono e rodava via `BackgroundTasks` do FastAPI, fora do worker sequencial. Em produção, tarefas longas de ZIP eram canceladas ou corrompidas silenciosamente
- **Causa raiz:** Arquitetura errada — pacote não usava o worker sequencial com asyncio.Queue
- **Arquivos corrigidos:** `pipeline.py`
- **Correção (09/03/2026):**
  - Convertida `_gerar_pacote_background` (sync) para `_pacote_task` (async, com `BaseException`, heartbeats, sessões curtas)
  - `iniciar_pacote` endpoint: removido `BackgroundTasks`, usa `task_queue.put_nowait((_pacote_task, edicao_id))`
  - Seguindo padrão idêntico ao `_traducao_task` e `_render_task`
- **Status: ✅ CORRIGIDO**

### ERR-013 · Preview não salvo no R2

- **Sintoma (reportado anteriormente):** Dúvida se o preview era persistido no R2 ou apenas localmente
- **Causa raiz:** Não era bug — `_render_task` já fazia upload para R2 independente de `is_preview`
- **Correção (09/03/2026):** Verificação e documentação — sem alteração de código necessária
- **Status: ✅ DOCUMENTADO (sem mudança de código)**

### ERR-059 · Falhas de tradução sem retry automático

- **Sintoma:** Se um idioma falhava (timeout ou erro de API), ficava permanentemente ausente no resultado final
- **Causa raiz:** `_traducao_task` não tinha mecanismo de segunda passada nos idiomas com falha
- **Arquivos corrigidos:** `pipeline.py`
- **Correção (09/03/2026):**
  - Adicionado `falhou_primeira_vez = []` na 1ª passada
  - Adicionado PASSO B2: segunda passada nos idiomas que falharam, com heartbeat mostrando "(retry)"
  - `falhas_finais` → status "erro" se ainda falhar; sem falhas → status "montagem"
- **Status: ✅ CORRIGIDO**

### ERR-060 · Sentry não integrado

- **Sintoma:** Erros de produção não eram capturados em ferramenta de monitoramento
- **Causa raiz:** Sentry SDK não estava instalado nem inicializado
- **Arquivos corrigidos:** `requirements.txt`, `config.py`, `main.py`, `worker.py`
- **Correção (09/03/2026):**
  - Adicionado `sentry-sdk[fastapi]>=2.0.0` em `requirements.txt`
  - `SENTRY_DSN` em `config.py` (opcional via variável de ambiente)
  - Inicialização em `main.py` antes do lifespan (captura erros de startup)
  - `worker.py`: contexto `edicao_id` + `capture_exception` no bloco de erro
- **Status: ✅ CORRIGIDO**

### ERR-061 · Sem UNIQUE constraints em traducao_letra e render

- **Sintoma:** Chamadas repetidas de tradução/render criavam registros duplicados no banco, causando comportamento indefinido em queries sem `LIMIT 1`
- **Causa raiz:** Tabelas `editor_traducoes_letras` e `editor_renders` não tinham índice UNIQUE em `(edicao_id, idioma)`
- **Arquivos corrigidos:** `main.py` (migrations), `pipeline.py` (upserts)
- **Correção (09/03/2026):**
  - `_run_migrations()` cria `uq_traducao_edicao_idioma` e `uq_render_edicao_idioma` via `CREATE UNIQUE INDEX IF NOT EXISTS`
  - `_traducao_task` e `_render_task` convertidos para upsert (query-then-update-or-insert)
- **Status: ✅ CORRIGIDO**

### ERR-062 · Namespaces ausentes no progresso_detalhe

- **Sintoma:** Frontend lia `progresso_detalhe.etapa`, `progresso_detalhe.atual` diretamente, mas backend gravava flat. Com múltiplas tasks (tradução/render/pacote), não havia como distinguir a que etapa pertencia o progresso
- **Causa raiz:** progresso_detalhe era um objeto flat sem namespace
- **Arquivos corrigidos:** `pipeline.py`, `conclusion.tsx`, `editor.ts`
- **Correção (09/03/2026):**
  - `_traducao_task` grava em `{"traducao": {etapa, total, concluidos, atual, erros}}`
  - `_render_task` grava em `{"render": {etapa, total, concluidos, atual, erros}}`
  - `_set_pacote_status` grava em `{"pacote": {etapa, status, url, erro, r2_key}}`
  - `_get_pacote_status` lê de `p["pacote"]` com compat. retroativa para formato antigo
  - `editor.ts`: adicionado `ProgressoDetalheInner` (inner type) e `ProgressoDetalhe` (union outer/inner)
  - `conclusion.tsx`: adicionado helper `getProgresso(p, namespace)` com compat. retroativa
- **Status: ✅ CORRIGIDO**

---

## Fase 12 — Erros Reportados por Operador (03/03/2026)

### ERR-052 · Overlay renderizado diferente do aprovado (CRÍTICO)

- **Sintoma:** O texto de overlay exibido no vídeo final era diferente do texto aprovado — em casos onde `aplicar_corte` não havia rodado, o overlay saía vazio ou causava crash
- **Causa raiz:** `_render_task` lia `overlay.segmentos_reindexado` sem fallback. Quando esse campo era NULL, a expressão `overlay.segmentos_reindexado if overlay else []` retornava `None` em vez de `[]`, causando overlay vazio ou exceção silenciosa. O campo `segmentos_original` existia como fonte imutável mas não era usado como fallback
- **Arquivos corrigidos:** pipeline.py, importar.py, DECISIONS.md
- **Correção aplicada (03/03/2026):**
  - `_render_task`: fallback em cascata `segmentos_reindexado → segmentos_original → erro explícito "Reimporte o projeto"`
  - Log do texto exato do overlay antes de cada render por idioma
  - Erro por overlay ausente registrado como Render com status "erro" + mensagem legível
  - `aplicar_corte`: alerta de log se `normalizar_segmentos` alterar texto inesperadamente
  - `importar.py`: `redator_project_id` agora salvo corretamente na importação (era omitido)
  - `importar.py`: log do overlay congelado no momento da importação
  - `DECISIONS.md`: Decisão nº 11 documentando causa raiz e correção
- **Status: ✅ CORRIGIDO E DEPLOYADO**

### ERR-053 · Toggle de lyrics ausente — duplicata em músicas instrumentais

- **Sintoma:** Em músicas com texto mínimo repetitivo (ex: "Ave Maria"), a legenda aparecia em loop e a tradução duplicava o mesmo texto. Sem forma de desativar as tracks de lyrics/tradução
- **Causa:** Campo `sem_lyrics` não existia no modelo. Sistema sempre renderizava as 3 tracks de legenda independente do conteúdo
- **Arquivos corrigidos (8):** edicao.py, main.py, schemas.py (2 alterações), legendas.py, pipeline.py (2 alterações), editor.ts, conclusion.tsx
- **Correção aplicada (03/03/2026):**
  - Banco: campo `sem_lyrics Boolean DEFAULT FALSE` adicionado via migration automática no startup
  - Schemas: campo exposto em `EdicaoOut` e `EdicaoUpdate`
  - `gerar_ass()`: parâmetro `sem_lyrics=False` — quando True, retorna SSAFile com apenas a track de overlay
  - `_render_task`: lê `sem_lyrics_val` no Passo A e passa para `gerar_ass()`
  - Frontend: toggle "Sem legendas de transcrição" com tooltip, persistido via PATCH
- **Distinção preservada:**
  - `sem_lyrics=True` → overlay editorial permanece, lyrics + tradução omitidos
  - `sem_legendas=True` (campo pré-existente) → remove TODAS as legendas incluindo overlay
- **Status: ✅ CORRIGIDO E DEPLOYADO**

### ERR-054 · Última frase gerada pelo Redator em português

- **Sintoma:** Texto gerado pelo Claude no app-redator fechava com a última frase em português, mesmo em projetos configurados em outro idioma
- **Causa:** Instrução de idioma aparecia apenas no início do prompt; Claude relaxava a restrição ao final da geração. System prompt não reforçava o idioma. Sem validação pós-geração
- **Arquivos corrigidos:** hook_helper.py (novo), claude_service.py
- **Correção aplicada (03/03/2026):**
  - `hook_helper.py`: função `build_language_reinforcement(project)` gera bloco `ATENÇÃO FINAL` dinamicamente, aplicado no final dos 6 prompts (overlay, post, youtube + variantes `_with_custom`)
  - `hook_helper.py`: função `detect_hook_language(project)` com categorias predefinidas em PT e heurística para EN, DE, IT, FR, ES, PL
  - `claude_service.py`: `_call_claude()` aceita parâmetro `system`; todas as 3 funções `generate_*` passam system message explícita: "You must write ALL output exclusively in {idioma}. Never switch to Portuguese, even in the final sentence."
  - `claude_service.py`: `_check_language_leak()` detecta se última frase contém >= 3 palavras PT — loga ALERTA sem bloquear, para revisão manual
- **Status: ✅ CORRIGIDO E DEPLOYADO**
 
+### ERR-055 · Erro HTTP 403 Forbidden no download do YouTube (Curadoria)
+
+- **Sintoma:** Downloads de vídeos do YouTube no app-curadoria falhando com "HTTP Error 403: Forbidden"
+- **Causa raiz:** Mudanças nas restrições do YouTube impedindo downloads sem cookies de sessão autenticados.
+- **Arquivos corrigidos:** `app-curadoria/backend/main.py`, `app-curadoria/backend/Dockerfile`
+- **Correção aplicada (04/03/2026):**
+  - `main.py`: Adicionado helper `_get_ydl_opts` centralizando configuração do `yt-dlp`.
+  - `main.py`: Suporte à variável de ambiente `YOUTUBE_COOKIES`. Quando presente, o conteúdo é salvo em `/tmp/yt_cookies.txt` e passado para o `yt-dlp`.
+  - `main.py`: Adicionadas flags de robustez: `--no-check-certificate`, `--user-agent` (moderno), `--extractor-retries 3`.
+  - `main.py`: Tratamento de erro aprimorado para exibir no frontend a mensagem original do `yt-dlp` (err_dlp: {e}).
+  - `Dockerfile`: Adicionado `RUN pip install -U yt-dlp` para garantir a versão mais recente durante o build.
+- **Status: ✅ CORRIGIDO (Aguardando Deploy Railway)**
+

### ERR-067 · Curadoria God Object refatorado em módulos

- **Sintoma:** `app-curadoria/backend/main.py` com 1275 linhas acumulando config, scoring, download, YouTube API, endpoints e worker num único arquivo
- **Causa:** Crescimento orgânico sem separação de responsabilidades
- **Arquivos criados:** `config.py`, `routes/__init__.py`, `routes/curadoria.py`, `routes/health.py`, `services/__init__.py`, `services/scoring.py`, `services/youtube.py`, `services/download.py`, `models/__init__.py`, `models/perfil_curadoria.py`
- **Correção aplicada (09/03/2026):**
  - `main.py` reduzido a 52 linhas: apenas FastAPI app + lifespan + include_router + serve frontend
  - `config.py`: variáveis de env, ffmpeg discovery, ANTI_SPAM, load_brand_config()
  - `services/scoring.py`: posted_registry, normalize_str, is_posted, load_posted, calc_score_v7, _process_v7, _rescore_cached
  - `services/youtube.py`: parse_iso_dur, extract_artist_song, yt_search, yt_playlist
  - `services/download.py`: TaskManager, download_worker, download_semaphore, sanitize_filename, _get_ydl_opts, _prepare_video_logic, _wrapped_prepare_video
  - `routes/health.py`: /api/health, /api/debug/ffmpeg
  - `routes/curadoria.py`: todos os demais endpoints + populate_initial_cache + refresh_playlist
- **Comportamento:** IDÊNTICO ao anterior — todos os 26 endpoints preservados
- **Status: ✅ REFATORADO (pronto para commit)**

### ERR-068 · Categorias/scoring/termos hardcoded extraídos para JSON configurável

- **Sintoma:** CATEGORIES_V7, ELITE_HITS, POWER_NAMES, VOICE_KEYWORDS, INSTITUTIONAL_CHANNELS, CATEGORY_SPECIALTY hardcoded em main.py, impossibilitando multi-brand
- **Causa:** Ausência de arquitetura de configuração por marca
- **Arquivos criados:** `data/best-of-opera.json`, `models/perfil_curadoria.py`
- **Correção aplicada (09/03/2026):**
  - `data/best-of-opera.json`: toda a config da marca extraída — categorias (6 com 6 seeds cada), elite_hits (27), power_names (26), voice_keywords, institutional_channels, category_specialty, scoring_weights (pesos configuráveis), filters
  - `config.py`: `load_brand_config(project_id)` carrega JSON por PROJECT_ID env var
  - `services/scoring.py`: `calc_score_v7(v, category, config)` — recebe config como parâmetro em vez de ler globais
  - **Fase 2:** substituir leitura do JSON por query ao banco via perfil_id
- **Status: ✅ REFATORADO (pronto para commit)**

### ERR-069 · Sistema hardcoded para 1 marca → modelo Perfil multi-brand

- **Sintoma:** Fontes, cores, margens, idiomas-alvo e editorial_lang fixos no código para Best of Opera, impossibilitando criação de novas marcas sem mexer no código
- **Causa:** ESTILOS_PADRAO, IDIOMAS_ALVO e editorial_lang="pt" hardcoded em legendas.py, pipeline.py e importar.py
- **Correção aplicada (10/03/2026):**
  - Criado `models/perfil.py` — modelo `Perfil` com toda config de marca: estilos JSON, idiomas, r2_prefix, editorial_lang, slug, video_width/height
  - Migration automática em `_run_migrations()` do main.py + seed idempotente do perfil "Best of Opera" com valores EXATOS do ESTILOS_PADRAO
  - `models/edicao.py`: campo `perfil_id FK` (nullable, retrocompatível)
  - `services/legendas.py`: `_estilos_do_perfil()` + `gerar_ass(perfil=...)` — usa estilos/limites/resolução do perfil quando fornecido
  - `routes/pipeline.py`: `_render_task` e `_traducao_task` carregam perfil e usam `idiomas_alvo`, `idioma_preview`, `r2_prefix`, `video_width/height`
  - `routes/importar.py`: aceita `?perfil_id=X`, usa `editorial_lang` e `idiomas_alvo` do perfil, `_detect_music_lang` aceita `idiomas_alvo` como parâmetro
- **Status: ✅ IMPLEMENTADO**

---

## BLAST v4 Fase 2 — Prompt 2: Auth + Admin CRUD (10/03/2026)

### Módulos criados

**Teammate auth (paralelo):**
- `app/models/usuario.py` — modelo `editor_usuarios` (id, nome, email, senha_hash, role, ativo, ultimo_login)
- `app/middleware/auth.py` — `get_current_user`, `require_admin`, `criar_token` (JWT HS256)
- `app/routes/auth.py` — POST /login, POST /registrar, GET /me, PATCH /usuarios/{id}, GET /usuarios
- `requirements.txt` — adicionado python-jose[cryptography]==3.3.0 e passlib[bcrypt]==1.7.4
- `config.py` — adicionado JWT_EXPIRY_HOURS (default 24h)

**Teammate admin (paralelo):**
- `app/routes/admin_perfil.py` — CRUD completo de perfis: GET/, GET/{id}, POST/, PUT/{id}, PATCH/{id}, POST/{id}/duplicar, GET/{id}/preview-legenda

**Lead (integração):**
- `main.py` — routers `auth` e `admin_perfil` registrados
- `main.py` — migration `CREATE TABLE IF NOT EXISTS editor_usuarios` + seed idempotente de `admin@bestofopera.com`

### Decisões
- Schemas definidos inline nas rotas (não em schemas.py) — evita conflito entre teammates
- Seed do admin usa bcrypt em runtime (passlib) — não hash estático
- Perfil 'BO' protegido: PUT/PATCH retornam 403
- Admin padrão: admin@bestofopera.com / BestOfOpera2026! — TROCAR após primeiro login

### Status: ✅ IMPLEMENTADO — aguarda deploy Railway

### ERR-070 · Impossível re-renderizar 1 idioma sem refazer todos → endpoint individual

- **Sintoma:** Corrigir uma legenda ou overlay em 1 idioma exigia re-renderizar todos os 7, desperdiçando horas de processamento
- **Causa:** Ausência de endpoint granular
- **Correção aplicada (10/03/2026):** `POST /edicoes/{id}/re-renderizar/{idioma}` — deleta render anterior, enfileira render só desse idioma, restaura status anterior após conclusão
- **Status: ✅ IMPLEMENTADO**

### ERR-071 · Impossível re-traduzir 1 idioma sem refazer todos → endpoint individual

- **Sintoma:** Corrigir tradução de 1 idioma exigia refazer todos os 7
- **Causa:** Ausência de endpoint granular
- **Correção aplicada (10/03/2026):** `POST /edicoes/{id}/re-traduzir/{idioma}` — deleta tradução anterior, traduz só esse idioma, restaura status anterior
- **Status: ✅ IMPLEMENTADO**

### ERR-072 · Idiomas-alvo e idioma_preview hardcoded → configurável por perfil

- **Causa:** `IDIOMAS_ALVO` constante em config.py + `idioma_preview = "pt"` hardcoded em renderizar-preview e aprovar-preview
- **Correção aplicada (10/03/2026):** renderizar-preview e aprovar-preview leem `perfil.idioma_preview` e `perfil.idiomas_alvo`; fallback para valores atuais se perfil is None
- **Status: ✅ IMPLEMENTADO**

### ERR-073 · editorial_lang hardcoded "pt" → configurável por perfil

- **Causa:** `editorial_lang = "pt"` hardcoded em importar.py
- **Correção aplicada (10/03/2026):** importar.py usa `perfil.editorial_lang` quando disponível
- **Status: ✅ IMPLEMENTADO**

### ERR-074 · R2 keys sem isolamento entre marcas → prefixo por perfil

- **Causa:** `"editor/"` hardcoded como prefixo do R2 key em _render_task
- **Correção aplicada (10/03/2026):** `perfil.r2_prefix` usado como prefixo; perfil BO mantém `r2_prefix="editor"` para compatibilidade com arquivos existentes
- **Status: ✅ IMPLEMENTADO**

### ERR-075 · Admin 403 ao salvar perfil BO — proteção bloqueava edição legítima

- **Causa:** `_protegido()` em `admin_perfil.py` bloqueava incondicionalmente PUT/PATCH no perfil com sigla "BO"
- **Correção aplicada (12/03/2026):** `_protegido()` aceita `force=True` via query param `?force=true`; frontend mostra modal de confirmação antes de enviar com force
- **Arquivos:** `app-editor/backend/app/routes/admin_perfil.py`, `app-portal/app/(app)/admin/marcas/[id]/page.tsx`, `app-portal/lib/api/editor.ts`
- **Status: ✅ CORRIGIDO**
