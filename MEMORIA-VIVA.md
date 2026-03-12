# Memória Viva — Best of Opera App2

## Referências de Infra (Railway + Postgres)
- Git remote: `https://github.com/BestOfOpera/best-of-opera-app2.git`
- Railway project ID: `c4d0468d-f3da-4765-b582-42cf6ef5ff66`
- Railway env ID: `4ec5a08f-d29e-4d7b-a54d-a3e161edd716`
- Editor backend service ID: `7e42a778-aa1e-4648-9ce1-07f5d6896fd5`
- Editor backend URL prod: `https://editor-backend-production.up.railway.app`
- Postgres service ID: `1f423154-d150-46a3-a459-b62b55fe1004`
- Postgres internal: `postgres.railway.internal:5432` (user: postgres, pass: bestofopera2024, db: railway)
- Postgres TCP proxy: `caboose.proxy.rlwy.net:49324` (pode mudar — verificar se ainda válido)
- Conectar: `python3 -c "import psycopg2; conn = psycopg2.connect(host='caboose.proxy.rlwy.net', port=49324, user='postgres', password='bestofopera2024', dbname='railway'); ..."`
- Railway token válido (2025-02): `5d70b3e4-85cf-43d9-893c-38578a90b8e9` (Code Token 2502)
- psql não disponível no Mac — usar python3 com psycopg2

## Sessão 2026-03-11 (2) — Bugfix ERR-066 via Sentry

### O que foi feito
- **ERR-066 corrigido**: `NameError: name 'falhas'` em `_traducao_task` (pipeline.py:1379) → `len(falhas)` → `len(falhas_finais)`
- **Sentry limpo**: FASTAPI-1 a FASTAPI-6 marcados como resolved (eram bugs já corrigidos na sessão 10/03)

### Pendências
- Fazer git push + deploy para que a correção chegue ao Railway

## Sessão 2026-03-11 — Sentry cobertura total (4 serviços)

### O que foi feito
- **editor-backend**: `_capture_sentry()` helper em pipeline.py + 5 chamadas nos handlers (download, transcricao, traducao, render, pacote); `SENTRY_ORG_URL` em config.py e dashboard.py; `attach_stacktrace=True` + `server_name="editor-backend"` em main.py
- **curadoria-backend**: `sentry-sdk[fastapi]>=2.0.0` em requirements.txt; `sentry_sdk.init(server_name="curadoria-backend")` em main.py; `capture_exception` no download_worker em services/download.py
- **redator**: `sentry-sdk[fastapi]>=2.0.0` em requirements.txt; `sentry_sdk.init(server_name="redator-backend")` em backend/main.py
- **app-portal**: `@sentry/nextjs ^8.0.0` em package.json; `sentry.client.config.ts` e `sentry.server.config.ts` criados; `next.config.ts` atualizado com `withSentryConfig`
- **Railway vars**: SENTRY_DSN + SENTRY_ORG_URL adicionados aos 4 serviços via GraphQL API (todos retornaram `variableUpsert: true`)
- **MCP Sentry**: configurado em `~/.claude/settings.json` com `@sentry/mcp-server@latest`
- **sentry-access.md**: criado em `dados-relevantes/` com token e DSN

### IDs de serviço Railway (completos)
- portal (73b20b58-eac5-44e8-a4f6-b9af94e74932) — serviço extra identificado, não tocado
- curadoria (b8fe934d-e3d7-4d30-a68a-4914e03cdb0a) — Next.js portal: NEXT_PUBLIC_SENTRY_DSN adicionada
- curadoria-backend (e3eb935a-7b11-44fd-889f-fbd45edb0602) — SENTRY_DSN adicionada
- editor-backend (7e42a778-aa1e-4648-9ce1-07f5d6896fd5) — SENTRY_DSN + SENTRY_ORG_URL adicionadas
- app/redator (fade4ac2-8774-4287-b87d-7f2559898dcc) — SENTRY_DSN adicionada

### Pendências
- Reiniciar sessão do Claude Code para ativar MCP Sentry
- Fazer push + deploy para que Railway aplique as variáveis
- Verificação pós-deploy: forçar erro em editor-backend → confirmar issue no Sentry com tag `server_name: editor-backend`

## Padrões técnicos do projeto
- Timestamps internos: `MM:SS,mmm` (função `seconds_to_timestamp`)
- ASS gerado por `app/services/legendas.py:gerar_ass()`
- Preview sempre em "pt" (exceto músicas em PT)
- `idioma` da edição = idioma da MÚSICA (não da versão/overlay)
- Modelos FK order para delete: Render → TraducaoLetra → Alinhamento → Overlay → Post → Seo → Edicao
- R2 key para renders: `{r2_prefix}/{r2_base}/{idioma}/video_{idioma}.mp4`
- `_get_r2_base(edicao)` em pipeline.py retorna a base R2 do projeto

## Sessão 2026-03-10 — Fix login editor-backend

### Bugs corrigidos
- **ERR-063** `passlib[bcrypt]==1.7.4` incompatível com `bcrypt>=4.0`. Startup crashava ao fazer hash da senha do admin (detect_wrap_bug passa senha >72 bytes, bcrypt 4.x lança ValueError). Fix: `bcrypt<4.0.0` em requirements.txt.
- **ERR-064** Migration `editor_edicoes.perfil_id` nunca comitava: ALTER TABLE e CREATE UNIQUE INDEX estavam na mesma transação. Se o INDEX falhava (dados duplicados), PostgreSQL abortava a transação inteira silenciosamente, revertendo o ALTER TABLE também. Fix: cada operação em seu próprio `with engine.begin()`.
- **ERR-065** Frontend enviava login com `username/password` form-urlencoded; backend espera `email/senha` JSON. Fix em `editorApi.login` e `login/page.tsx`.

### Estado resultante
- Editor backend rodando (SUCCESS no Railway, deploy `5413b785`)
- Login funcionando: `admin@bestofopera.com / BestOfOpera2026!`
- `editor_edicoes.perfil_id` adicionado ao banco de produção

### Armadilha nova (adicionar ao CLAUDE.md)
- **Transactions parciais**: nunca misturar ALTER TABLE + CREATE UNIQUE INDEX na mesma transação. Se o INDEX falha (silenciosamente capturado com try/except), PostgreSQL aborta a transação e reverte o ALTER TABLE. Cada operação falível = transação própria.

## TODO pendentes
- Remover endpoint `admin/reset-total` de `app-editor/backend/app/routes/` por segurança (criado no commit `96d45ea`, nunca usado — substituído por cleanup psql direto)

## Sessão 2026-03-09 — BLAST v3

### O que foi feito
- **BLOCO 0:** Configuradas variáveis `SENTRY_DSN` e `COBALT_API_URL` em `config.py`; atualizado `.env.example` com 4 grupos; criado `dados-relevantes/BLAST-expansao.md`
- **BLOCO 1 (ERR-056):** cobalt.tools integrado como 3ª fonte na cascata de download (após R2, antes da Curadoria). Funções `_download_via_cobalt()` e `_download_via_ytdlp()` adicionadas em `pipeline.py`
- **BLOCO 2 (ERR-057):** Pacote ZIP migrado de `BackgroundTasks` para worker sequencial. `_gerar_pacote_background` virou `_pacote_task` async com `BaseException` e heartbeats
- **BLOCO 3 (ERR-013):** Verificado que preview já era salvo no R2 — sem alteração de código
- **BLOCO 4 (ERR-059):** Retry automático de tradução: 2ª passada em idiomas que falharam na 1ª. Status "erro" só se ainda falhar no retry
- **BLOCO 5 (ERR-060):** Sentry integrado via `sentry-sdk[fastapi]>=2.0.0`; opcional via `SENTRY_DSN`; captura exceções no worker com contexto `edicao_id`
- **BLOCO 6 (ERR-061/ERR-062):** UNIQUE indexes em `editor_traducoes_letras` e `editor_renders`; upserts em `_traducao_task` e `_render_task`; namespaces `"traducao"/"render"/"pacote"` no `progresso_detalhe`; `conclusion.tsx` atualizado com helper `getProgresso()` com compat. retroativa

### Decisões
- `_get_pacote_status`: lê `p["pacote"]` no novo formato; fallback `p.etapa === "pacote"` para compat. com dados antigos no banco
- `ProgressoDetalhe` em `editor.ts` virou union type: `Record<string, ProgressoDetalheInner> | ProgressoDetalheInner | null`
- `getProgresso(p, namespace)` em `conclusion.tsx`: tenta namespace novo, fallback flat `etapa ===`

### Pendências
- Nenhuma — todos os 7 blocos concluídos e commitados

## Sessão 2026-03-03

### O que foi feito
- **Fix: URL duplicada no YouTube** — Link "Abrir no YouTube" no pipeline do Editor (Passos 2, overview e conclusão) estava com URL duplicada no href (ex: `https://youtube.com/watch?v=XYZhttps://youtube.com/watch?v=XYZ`)
- Criada função utilitária `getYoutubeUrl(youtubeUrl, videoId)` em `app-portal/lib/utils.ts` que normaliza a URL: se já é URL completa, usa como está; se é apenas video_id, constrói a URL
- Aplicada em 3 componentes: `validate-lyrics.tsx`, `overview.tsx`, `conclusion.tsx`
- Build OK, deploy feito via push

### Decisões
- Fix defensivo no frontend (normalização) em vez de corrigir dados no banco — mais seguro e cobre futuros edge cases

### Pendências
- Nenhuma

## Sessão 2026-03-04

### O que foi feito
- **Input manual de YouTube URL adicionado na Curadoria**
- Criado endpoint `POST /api/manual-video` no backend para extração de metadados via YouTube Data API (com fallback oEmbed)
- Adicionado campo de input manual no Dashboard da Curadoria, permitindo colar links diretos do YouTube
- Vídeos adicionados manualmente aparecem no topo da lista com badge visual "Manual"
- Persistência dos vídeos manuais durante a sessão no frontend
- Implementada lógica de score e verificação de "posted" também para vídeos manuais

### Decisões
- Vídeos manuais não são salvos no banco de dados (cache) para evitar poluição, permanecendo apenas no estado da sessão do frontend
- Badge "Manual" adicionada na thumbnail para fácil identificação

### Pendências
- Nenhuma

## Sessão 2026-03-04 (Continuação)

### O que foi feito
- **Bug A Fix: Precisão do corte (FFmpeg)** — Corrigido offset de 4-5s no início dos vídeos. O comando FFmpeg em `ffmpeg_service.py` agora usa busca precisa (`-ss` antes do `-i`), re-encodagem compulsória dos clips e filtros de ajuste de PTS (`setpts=PTS-STARTPTS`) para garantir que o primeiro frame seja exatamente o ponto de corte escolhido.
- **Bug B Fix: Timestamps de Overlay (Sincronia)** — Corrigida falha grave onde overlays apareciam em momentos aleatórios e ordem invertida.
    - **Causa:** Timestamps do Redator (em milissegundos) eram interpretados como segundos (ex: 6000ms → 6000s).
    - **Solução:** Implementada heurística em `timestamp_to_seconds` para detectar e converter milissegundos automaticamente. Adicionada ordenação obrigatória por tempo nos segmentos de overlay antes da geração do ASS.
    - **Efeito:** Overlays agora seguem rigorosamente o schedule do Redator e aparecem na ordem correta.

### Decisões
- Re-encodagem adotada no `cortar_na_janela_overlay` para garantir 100% de precisão, aceitando o trade-off de tempo de CPU em troca de qualidade e exatidão.
- Heurística de milissegundos (>3600) adotada como solução pragmática para lidar com a ambiguidade dos dados vindos de diferentes fontes (Gemini em s/srt, Redator em ms/int).

### Pendências
- Nenhuma

## Sessão 2026-03-04 (Continuação 2)

### O que foi feito
- **Mover Toggle Instrumental para Importação** — O toggle "Este vídeo tem letra / é instrumental" foi movido da tela final para o modal de importação do Redator.
- **Backend**: Endpoint `POST /api/v1/editor/redator/importar/{project_id}` agora aceita `eh_instrumental`. Ao criar a edição, tanto `eh_instrumental` quanto `sem_lyrics` são setados.
- **Frontend (API)**: `importarDoRedator` atualizada para enviar o novo parâmetro.
- **Frontend (UI)**:
    - O modal de importação agora aparece sempre ao clicar em "Importar", permitindo escolher o idioma (com opção "Detectar automaticamente") e o toggle "🎵 Este vídeo tem letra cantada" (checked por padrão).
    - Removido o toggle redundante da tela `conclusion.tsx`.
    - Garantido que `eh_instrumental=true` faz o pipeline pular as etapas de letra/transcrição e omitir legendas no render final.

### Decisões
- O toggle foi invertido visualmente para "Tem letra cantada" (default true) para ser mais intuitivo para o operador, mas mapeia para `eh_instrumental=false` no banco.
- O modal de importação agora é o ponto central de decisão antes de iniciar o pipeline, evitando processamentos desnecessários em vídeos instrumentais.

### Pendências
- Nenhuma

## Sessão 2026-03-04 (Continuação 3)

### O que foi feito
- **Escolha Obrigatória de Lyrics na Importação** — Substituída a lógica automática/toggle simples por uma decisão manual e obrigatória no modal de importação.
- **Frontend (UI)**:
    - O modal agora apresenta dois cards visuais: **"🎵 Com Lyrics"** e **"🎼 Sem Lyrics"**.
    - O botão "Iniciar Importação" fica desabilitado até que uma das opções seja clicada (escolha consciente).
    - Adicionada sugestão visual sutil baseada na categoria do Redator (ex: sugere "Com Lyrics" para Aria/Chorus, e "Sem Lyrics" para Overture).
- **Backend (Workflow)**:
    - Removida toda a lógica de "pulo automático" de etapas (skip steps) baseada em `eh_instrumental`.
    - Todos os vídeos agora seguem o mesmo fluxo linear (Garantir Vídeo → Letra → Transcrição → ...).
    - O campo `eh_instrumental` (e `sem_lyrics`) agora atua exclusivamente no renderizador final, omitindo as faixas de legenda se marcado como instrumental.
- **Frontend (Workflow)**:
    - Removidos redirects baseados em `eh_instrumental` nas telas de validação.

### Decisões
- Decisão editorial prevalece sobre automação: o operador decide se quer legendas mesmo em vídeos instrumentais (ex: para vocalizes simples).
- Fluxo unificado: simplifica a manutenção do código ao tratar todos os projetos com a mesma esteira, apenas variando o conteúdo renderizado no final.

### Pendências
- Nenhuma

## Sessão 2026-03-04 (Continuação 4)

### O que foi feito
- **Correção da Confusão Visual do Botão de Tradução (Editor)**
- **Mudança na UI do Passo de Conclusão**:
    - Removido o botão "Traduzir Lyrics x7 idiomas" durante a operação normal (status `traducao`, `montagem`, etc.) e estados posteriores (`concluido`).
    - Substituído por um indicador de status visual:
        - Durante a tradução: **"🌍 Tradução em andamento... {x}/{7} idiomas"** (azul).
        - Após a tradução: **"✅ Tradução concluída — 7/7 idiomas"** (verde).
    - O botão só torna-se visível em caso de **ERRO** na tradução, renomeado para **"🔄 Tentar novamente"** (vermelho).
    - Removido o botão redundante de "Refazer Tradução" da seção "Resolver problemas" (exceto em caso de erro), seguindo a regra de não induzir cliques desnecessários.

### Decisões
- Ocultação agressiva: para evitar que o operador sinta necessidade de clicar em botões que já rodam em background, o botão principal foi removido do fluxo de sucesso. O retry em erro é mantido como única interação manual necessária.
- Visibilidade persistente: o indicador de "Concluído" permanece visível mesmo após o sucesso da tradução, oferecendo feedback claro sobre o estado da pipeline automática.

### Pendências
- Nenhuma

## Sessão 2026-03-05

### O que foi feito
- **ERR-057 corrigido: curadoria agora busca playlist completa com paginação**
- Implementada paginação (nextPageToken loop) no backend da Curadoria (`yt_playlist`) para buscar todos os vídeos da playlist (~150).
- Adicionado botão "Atualizar Playlist" no Dashboard para disparar a busca completa manualmente.
- O carregamento padrão da Playlist agora lê exclusivamente do banco, economizando API quota.
- Log detalhado no backend informando o total de vídeos encontrados.

### Decisões
- Busca escalonada em batches de 50 para os detalhes dos vídeos (videos.list) visando eficiência.
- Timeout aumentado para 30s na chamada da API para lidar com playlists maiores.
- Interface ganhou feedback visual durante o processo de atualização (Loader e mensagens de status).

### Pendências
- Nenhuma

## Sessão 2026-03-05 (Continuação)

### O que foi feito
- **ERR-056 corrigido: truncamento de overlay agora respeita limites de palavra**
- Bug: O overlay cortava o texto no 30º caractere exato, adicionando "..." no meio de palavras (ex: "faz" -> "f...").
- **Backend (Editor)**:
    - Atualizada constante `OVERLAY_MAX_CHARS_LINHA` de 30 para 35 em `legendas.py`.
    - Atualizada constante `OVERLAY_MAX_CHARS` de 60 para 70.
    - Reescrevida a função `_truncar_texto` para buscar o último espaço antes do limite (max 35), garantindo que nenhuma palavra seja cortada.
    - `_formatar_overlay` agora utiliza `_truncar_texto` em todos os fluxos de quebra de linha.
    - Símbolo de elipse alterado de `…` (Unicode) para `...` (3 pontos) conforme solicitado.
- **Backend (Redator)**:
    - Atualizados os prompts em `overlay_prompt.py` para refletir os novos limites (35 por linha, 70 no total), orientando o Claude a gerar textos mais ricos que aproveitem o espaço disponível.
- **Testes**:
    - Criado script `verify_fix.py` que validou com sucesso strings longas garantindo o corte apenas em espaços.

### Decisões
- Limite de 35 caracteres adotado como padrão oficial para overlays em ambas as aplicações.
- Truncamento conservador: prioriza sempre o espaço antes do limite para evitar cortes de palavras.
- Unificação de limites: Prompt do Redator e Lógica do Editor sincronizados para evitar inconsistências.

### Pendências
- Nenhuma

## Sessão 2026-03-05 (Continuação 2)

### O que foi feito
- **ERR-055 corrigido: filtro de segmentos inválidos no track lyrics**
- Corrigido bug onde as legendas "lyrics" sumiam em determinados momentos do vídeo.
- **Causa:** O sistema estava tentando renderizar segmentos com duração zero (`start == end`) ou negativa, o que fazia as legendas serem ignoradas pelo formato ASS.
- **Solução:**
    - Implementado filtro em `gerar_ass` (serviço `legendas.py`) para descartar segmentos onde `end <= start` ou texto está vazio.
    - Adicionado log detalhado que imprime cada segmento válido e avisa quando um é descartado.
    - Melhorada a função `corrigir_timestamps_sobrepostos` para garantir que o ajuste de fim de segmento não crie durações inválidas (garante min 0.1s entre start e end em caso de colisão).
- **Efeito:** Track de lyrics agora é robusto contra dados de timing corrompidos e log facilita debug de sincronismo.

### Decisões
- Optou-se por filtrar silenciosamente os segmentos inválidos no nível do gerador de ASS (com log de warning) para garantir que o render continue sem crashar ou sumir com a track toda.

### Pendências
- Nenhuma

## Sessão 2026-03-05 (Continuação 3)

### O que foi feito
- **ERR-052 e ERR-056 corrigidos — prompts de overlay reescritos por categoria + limpeza ortográfica**
- **Prompts Criativos**: Substituídos os prompts genéricos de 10 categorias no `app-redator/backend/config.py` por instruções ricas e específicas (Hook/angle) escritas pelo Diretor de TI. As novas instruções focam em narrativas surpreeendentes, abertura de loops de curiosidade e fuga de clichês.
- **Limpeza Ortográfica**: Implementada a função `_limpar_texto_overlay` em `claude_service.py` para corrigir automaticamente erros de digitação e formatação do Claude:
    - Adição de espaço faltante após pontuação (`,;:!?`).
    - Separação de palavras "grudadas" (CamelCase acidental).
    - Remoção de espaços duplos.
- **Fluxo de Geração**: A limpeza é aplicada automaticamente a todas as legendas do overlay antes da persistência no banco de dados.

### Decisões
- Os prompts do Diretor de TI foram implementados ipsissima verba para garantir a qualidade editorial desejada.
- A limpeza ortográfica ocorre no nível de serviço (`claude_service.py`), garantindo que tanto a geração inicial quanto a regeneração manual sejam beneficiadas.

### Pendências
- Nenhuma
## Sessão 2026-03-05 (Continuação 5)

### O que foi feito
- **ERR-053 e ERR-054 corrigidos: CTA fixo na última legenda + validação de timing**
- **Backend (Redator)**:
    - Atualizado `overlay_prompt.py` com instrução obrigatória para que a ÚLTIMA legenda do array seja sempre um CTA de engajamento (Follow, Save, etc.), adaptado ao contexto da música.
    - Implementada função de validação pós-geração em `claude_service.py` que garante que a última legenda termine pelo menos 5s antes do fim do vídeo (calculado via `cut_start/cut_end` ou `original_duration`).
    - Se o timestamp ultrapassar o limite (duracao - 5s), ele é automaticamente recalculado para (duracao - 8s) para garantir margem de segurança.
- **Testes**:
    - Criado script de regressão `test_overlay_fix.py` que validou com sucesso o ajuste automático de timestamps.

### Decisões
- Timestamp de 8s (recalculado) adotado para garantir que o CTA seja lido com folga antes do fade-out do vídeo.
- Lógica de timing centralizada no `generate_overlay` para benefício de todas as gerações (inicial e manual/custom).

### Pendências
- Nenhuma

## Sessão 2026-03-09 — Refactor Curadoria: God Object → Módulos

### O que foi feito
- **ERR-067 + ERR-068: app-curadoria/backend/main.py (1275 linhas) refatorado em 11 arquivos**

### Estrutura nova de `app-curadoria/backend/`
```
config.py                    # env vars, ffmpeg, ANTI_SPAM, load_brand_config()
data/best-of-opera.json      # toda a config da marca (categorias, scoring, termos)
models/perfil_curadoria.py   # Pydantic model para config por marca
services/scoring.py          # posted_registry + calc_score_v7(v, cat, config) + _process_v7 + _rescore_cached
services/youtube.py          # yt_search(q, n, api_key) + yt_playlist + helpers
services/download.py         # TaskManager + download_worker + _get_ydl_opts + _prepare_video_logic
routes/health.py             # /api/health, /api/debug/ffmpeg
routes/curadoria.py          # todos os outros 24 endpoints + populate_initial_cache + refresh_playlist
main.py                      # 52 linhas: app + lifespan + include_router + static
```

### Pontos-chave para Fase 2 (multi-brand)
- `PROJECT_ID` env var seleciona qual JSON carregar (default: `best-of-opera`)
- `calc_score_v7(v, category, config)` recebe config como parâmetro — substituir BRAND_CONFIG por query ao banco
- `data/{project_id}.json` → criar `data/reels-classics.json` para o próximo projeto
- Todos os 26 endpoints preservados com comportamento idêntico

### Pendências
- Nenhuma nesta sessão

---

## Sessão 10/03/2026 — BLAST v4 Fase 2: Prompt 1 executado

### O que foi implementado

**Multi-brand backend** completo — Prompt 1 da Fase 2:

1. **`models/perfil.py`** — modelo `Perfil` (`editor_perfis`): estilos JSON (overlay/lyrics/traducao), idiomas, r2_prefix, editorial_lang, slug, video_width/height
2. **`models/edicao.py`** — campo `perfil_id FK` (nullable, retrocompatível)
3. **`main.py`** — migration cria `editor_perfis` + seed idempotente do perfil "Best of Opera" com valores exatos do ESTILOS_PADRAO + migration de `perfil_id` nas edições existentes
4. **`services/legendas.py`** — `_estilos_do_perfil()` + `gerar_ass(perfil=...)` usa estilos/limites/resolução do perfil
5. **`routes/pipeline.py`** — `_render_task` e `_traducao_task` brand-aware (idiomas, preview, r2_prefix, video_width/height); endpoints `re-renderizar/{idioma}` e `re-traduzir/{idioma}`
6. **`routes/importar.py`** — aceita `?perfil_id=X`, usa `editorial_lang` e `_detect_music_lang` com idiomas do perfil
7. **`schemas.py`** — `PerfilCreate`, `PerfilUpdate`, `PerfilOut`; `EdicaoOut` com `perfil_id` e `perfil_nome`
8. **`tests/test_multi_brand.py`** — 8 testes, todos passando

### Retrocompatibilidade garantida
- perfil_id=None → comportamento IDÊNTICO ao anterior (IDIOMAS_ALVO, "pt" hardcoded, "editor/" R2 prefix)
- Edições existentes migradas para perfil_id = id do perfil "BO"

### Próximo passo (atualizado 10/03/2026)
- ~~Prompt 2: Auth backend + Admin CRUD~~ ✅ CONCLUÍDO
- Prompt 3: Frontend Admin + Stepper + Auth UI (Antigravity)
- Fazer deploy no Railway + testar migrations em produção

---

## Estado Atual: Prompt 2 CONCLUÍDO (10/03/2026)

### O que foi implementado
- **Auth backend:** `models/usuario.py` + `middleware/auth.py` + `routes/auth.py`
  - JWT HS256, 24h expiry, roles admin/operador
  - Endpoints: POST /login, POST /registrar (admin only), GET /me, PATCH /usuarios/{id}, GET /usuarios
- **Admin CRUD:** `routes/admin_perfil.py`
  - Endpoints: GET/, GET/{id}, POST/, PUT/{id}, PATCH/{id}, POST/{id}/duplicar, GET/{id}/preview-legenda
  - Perfil BO protegido (403 em write)
- **Migration:** `editor_usuarios` criada no startup, seed admin@bestofopera.com
- **Novas deps:** python-jose[cryptography], passlib[bcrypt]

### Credencial admin padrão
- Email: `admin@bestofopera.com`
- Senha: `BestOfOpera2026!` — **TROCAR após 1º login em produção**

### Arquitetura de auth
- Token JWT no header `Authorization: Bearer {token}` (não cookie)
- `SECRET_KEY` de `config.py` (env var em Railway)
- `require_admin` = Dependency do FastAPI, protege rotas admin

---

## Sessão 10/03/2026 — Prompt 1.5-B CONCLUÍDO

### O que foi implementado

**Unificar Perfil editor+curadoria — sessão B (rotas + endpoint interno + testes):**

1. **`duplicar_perfil`** corrigido: agora copia todos os campos de curadoria (curadoria_categories, elite_hits, power_names, voice_keywords, institutional_channels, category_specialty, scoring_weights, curadoria_filters, anti_spam_terms). playlist_id sempre resetado para `""` na cópia (nova marca começa sem playlist própria).

2. **`GET /{id}/curadoria-config`** (admin, com auth): novo endpoint em `routes/admin_perfil.py` que retorna somente campos de curadoria de um perfil.

3. **`GET /api/internal/perfil/{slug}/curadoria-config`** (sem auth): endpoint interno em `router_internal` para a curadoria consumir. Registrado em `main.py` via `app.include_router(admin_perfil.router_internal)`.

4. **`app/services/perfil_service.py`** criado: função `build_curadoria_config(perfil)` isolada sem dependência de auth. Permite import nos testes sem precisar de python-jose.

5. **`app-curadoria/backend/config.py`** atualizado:
   - Novas env vars: `EDITOR_API_URL` (default: `http://localhost:8000`), `BRAND_SLUG` (default: `best-of-opera`)
   - `load_brand_config(slug)` agora tenta `GET {EDITOR_API_URL}/api/internal/perfil/{slug}/curadoria-config` com timeout 3s
   - Cache in-memory com TTL 5min (`_brand_config_cache`)
   - Fallback para JSON local se editor offline
   - `BRAND_CONFIG` global mantido para compatibilidade de startup

6. **`routes/curadoria.py`** atualizado: todos os usos de `BRAND_CONFIG` global substituídos por `load_brand_config()` por request (beneficia do cache). Mudanças no admin refletem na curadoria sem restart.

7. **`models/perfil_curadoria.py`** deletado: modelo Pydantic avulso removido (era placeholder pre-Fase2). Não havia imports externos.

8. **`tests/test_perfil_unificado.py`**: 4 testes, todos passando (12/12 na suite completa).

### Arquitetura do endpoint interno
- URL: `GET /api/internal/perfil/{slug}/curadoria-config`
- Sem auth (comunicação interna entre serviços)
- Retorna: `{name, project_id, categories, elite_hits, power_names, voice_keywords, institutional_channels, category_specialty, scoring_weights, filters, anti_spam, playlist_id}`

### Próximo passo
- Prompt 3: Frontend Admin + Stepper + Auth UI (Antigravity)
- Deploy no Railway + testar migrations e endpoint interno em produção

---

## Sessão 10/03/2026 — Prompt 2.5-A: Fundação + Storage Layer (Multi-Brand)

### O que foi implementado

**5 campos redator + storage R2 prefixado por marca:**

1. **`models/perfil.py`** — 5 campos novos: `hook_categories_redator` (JSON), `identity_prompt_redator` (Text), `tom_de_voz_redator` (Text), `logo_url` (VARCHAR 500), `font_name` (VARCHAR 100)

2. **`main.py`** — CREATE TABLE e ALTER TABLE migrations incluem os 5 novos campos

3. **`routes/admin_perfil.py`** — `PerfilDetalheOut` inclui 5 campos; `duplicar_perfil` copia todos; PUT/PATCH já dinâmicos via `hasattr`; novo endpoint `GET /api/internal/perfil/{slug}/redator-config` (sem auth)

4. **`shared/storage_service.py`** — `check_conflict()` e `save_youtube_marker()` aceitam `r2_prefix=""` param. Marker keys agora usam `{r2_prefix}/{base}/video/.youtube_id`. Retorno sempre BARE.

5. **`routes/pipeline.py`** — `_get_perfil_r2_prefix(edicao, db)` helper criado. Call sites atualizados:
   - `upload_video` (sync): prefixo aplicado a `r2_key`
   - `_download_task` (PASSO B/C/E/F): prefix carregado na sessão inicial, aplicado em todos os passos
   - `_exportar_renders`: `lang_prefix` prefixado com `r2_prefix`
   - `_pacote_task`: textos e ZIP key prefixados
   - `download_pacote`: fallback key prefixado

6. **`services/perfil_service.py`** — `build_curadoria_config` agora inclui `r2_prefix`; nova função `build_redator_config(perfil)` retorna config completa do redator

### Regras de storage
- `r2_base` no DB é SEMPRE bare (sem prefixo)
- Prefixo aplicado em runtime via `_get_perfil_r2_prefix()`
- `r2_prefix=""` = comportamento antigo (backward compatible)
- Renders (`_render_task`) JÁ usavam `{r2_prefix}/{r2_base}/...` — sem mudança

### Testes
- 12/12 passando (sem novos testes neste prompt)

### Próximo passo
- Prompt 2.5-B (se houver): testes específicos de storage prefixado
- Prompt 3: Frontend Admin + Stepper + Auth UI (Antigravity)

---

## [2.5-B] Redator Multi-Brand — 2026-03-10
- Adicionado `perfil_id` (nullable int) e `brand_slug` (varchar 50, default "best-of-opera") ao model Project
- Migration automática em `_run_migrations()` no main.py
- Schemas atualizados: ProjectCreate, ProjectUpdate, ProjectOut com os novos campos
- Criado `load_brand_config(slug)` em config.py: cache 5min, fallback hardcoded, HOOK_CATEGORIES preservado
- Env vars: `EDITOR_API_URL` (default localhost:8000) e `BRAND_SLUG` (default best-of-opera)
- Prompts atualizados com `brand_config=None`: overlay_prompt, post_prompt, youtube_prompt, hook_helper
- `claude_service.py`: generate_overlay/post/youtube aceitam `brand_config=None`
- `generation.py`: carrega brand_config via `load_brand_config(brand_slug)` e propaga em todos os endpoints
- Backward compatible: brand_config=None = comportamento antigo (Best of Opera hardcoded)

## [2.5-C] Dashboard & Reports Filtro por Marca — 2026-03-10
- Adicionado `perfil_id: Optional[int] = None` em todos os endpoints de `dashboard.py` (stats, edicoes-recentes, pipeline, visao-geral, producao, saude)
- Todas as queries em Edicao filtradas condicionalmente via `base_q` pattern
- Adicionado `perfil_id` filter via join em `reports.py` (listar_reports e resumo_reports)
- Import de `Edicao` adicionado em reports.py para o join
- Backward compatible: sem perfil_id = retorna tudo (comportamento idêntico ao anterior)
- Lógica de negócio não alterada — apenas filtro condicional adicionado

## [2.5-D] Curadoria R2 Prefix + Script Migração — 2026-03-10
- Pré-requisito 2.5-A confirmado: `shared/storage_service.py` já tinha `r2_prefix` em check_conflict/save_youtube_marker
- `curadoria.py`: todos os call sites de check_conflict e save_youtube_marker passam `r2_prefix` via `load_brand_config()`
- `download.py`: mesma pattern — `load_brand_config()` + `r2_prefix` aplicado em check_conflict e construção de r2_key
- Criado `scripts/migrate_r2_to_brand_prefix.py` (203 linhas): idempotente, manifesto JSON, dry-run/execute/verify
- Script classifica objetos: BO/* → skip, reports/* → skip, editor/* → copia para BO/, bare → copia para BO/
- NÃO deleta originais — cleanup manual posterior
- `load_brand_config` em app-curadoria importado do próprio `config.py` da curadoria


## [2.6] Editor UI Refinement & Prod E2E Tests — 2026-03-10
- Refinado o visual das páginas de Admin de Marcas e Admin de Usuários no portal Frontend:
  - Adicionado Skeleton Loaders e States Vazios compatíveis com o Design System.
  - Implementação de Collapsible Sections e Pickers de Cores refinados nos forms das marcas.
  - Sidebar refatorada com Separador do Admin e Avatar no User Card.
  - Preview visual 9:16 (Wireframe de texto/legendas) nas configurações das Marcas.
  - Indicadores semânticos de Status com estilos modernos e faixas laterais coloridas nos cards de marca e no Brand Selector do Header.
- Stepper do Workflow com glowing vermelho e pulsing para in-progress.
- Realizado Teste E2E via Browser Autônomo na URL (curadoria-production-cf4a.up.railway.app):
  - Fluxo paralisado logo no login devido a erro silencioso CORS/net::ERR_FAILED na chamada ao backend de auth (`/api/v1/editor/auth/login`).
  - Interface visual em prod não contava com o refinamento efetuado nesta sessão localmente (deploy pendente).

---

## Sessão 11/03/2026 — Antigravity: Hotfixes Cirúrgicos Pós-E2E

### O que foi corrigido

1. **Visibilidade de Toasts** — `<Toaster />` adicionado ao layout global. Testado com falha de login intencional — toast "Email ou senha incorretos" aparece corretamente.

2. **Navegação Dashboard → Projeto** — Links corrigidos de `/editor/{id}` para `/editor/edicao/{id}/overview`. Resolve erro 404 ao abrir projetos.

3. **Color Picker em Marcas** — Bug de concatenação hexadecimal corrigido (ex: `#ff0000#ff0000`). Input visual e input de texto sincronizam um único valor. JSONs de estilo (`overlay_style`, etc.) migraram de `defaultValue` para `value` controlado — agora exibem corretamente os dados do banco.

4. **Trailing slashes nas chamadas de API** — Barras finais removidas de todos os endpoints críticos (ex: `/admin/perfis/` → `/admin/perfis`) para alinhar com o roteador FastAPI em produção. Possível causa do "Application Error" na página `/admin/marcas`.

### Arquivos alterados (pelo Antigravity)
- `app/routes/editor.ts` — trailing slashes removidas
- `app-portal/app/(app)/editor/edicao/[id]/page.tsx` — links corrigidos
- `app-portal/app/(app)/admin/marcas/page.tsx` — color picker + JSON inputs corrigidos
- Layout global — `<Toaster />` adicionado

### Status dos testes (reteste pós-fix)
| Cenário | Status |
|---|---|
| Abertura de Projeto (Dashboard → `/overview`) | ✅ PASSOU |
| Criar Marca (color picker + inputs) | ✅ PASSOU |
| Configurar Marca (JSONs carregam do banco) | ✅ PASSOU |
| Toasts / Feedback Visual | ✅ PASSOU |
| Stepper do Editor | ✅ PASSOU |
| Re-Render | ⚠️ Acessível via ícone 🔄 em Dialogs na tela de Conclusão |

### Pendência de deploy
- Correções de trailing slashes e color picker precisam de deploy processado pela Railway para que `/admin/marcas` volte a funcionar 100% sem exception client-side.

### Próximos passos
1. Verificar no portal Railway se `/admin/marcas` está acessível após o deploy das correções.
2. Testar criação de marca real com os novos inputs de cor para confirmar integridade dos dados no banco.
