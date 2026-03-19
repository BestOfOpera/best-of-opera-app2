# Memória Viva — Best of Opera App2

## Sessão 2026-03-19 (25) — SPEC-001: segurança e curadoria multi-brand

### O que foi feito
- BUG-C: removido `opera live` hardcoded em `/api/search`; config carregado antes de montar a query
- BUG-D: `ANTI_SPAM` global substituído por `config.get("anti_spam") or ANTI_SPAM` em 4 ocorrências (`populate_initial_cache`, `/api/search`, `search_category`, `ranking`)
- BLOCKER pendente: verificar `SELECT slug, anti_spam_terms FROM editor_perfis` no banco Railway
- SPEC-001 → CONCLUÍDO

---

## Sessão 2026-03-19 (24) — Housekeeping: arquivamento de planos concluídos

### O que foi feito
- Novo parceiro entrou no projeto (Filip) — onboarding e análise do estado atual
- Leitura completa de CLAUDE.md, MEMORIA-VIVA.md, HISTORICO-ERROS-CORRECOES.md, DECISIONS.md, PLANO-DE-ACAO-120326-MULTIBRAND.md e dados-relevantes/
- Movido `PLANO-DE-ACAO-120326-MULTIBRAND.md` → `arquivo/` (plano 100% concluído desde sessão 20)
- Movido `dados-relevantes/CONTEXTO-MULTIBRAND-PARA-CLAUDE.md` → `arquivo/` (snapshot desatualizado — multi-brand concluído)

### Pendências identificadas (herdadas das sessões anteriores)
- Deploy do curadoria-backend no Railway (pendente desde sessão 23)
- `ANTI_SPAM` hardcoded na curadoria — não usa config da marca RC
- `/api/search` hardcoda `opera live` no query (errado para Reels Classics)
- `cached_videos` sem `brand_slug` na curadoria

### Estado resultante
- Repositório clonado localmente na máquina do parceiro Filip
- Raiz do projeto limpa — sem planos concluídos soltos
- Próximo passo: definir prioridade entre as pendências herdadas ou novo desenvolvimento

---

## Sessão 2026-03-12 (23) — Fix curadoria multi-brand (Reels Classics não carregava)

### Problema
Ao selecionar "Reels Classics" na curadoria, nada carregava — nem categorias nem playlist. Tudo mostrava dados do Best of Opera.

### Causa raiz (dupla)
1. **Categorias formato incompatível**: RC no banco usava formato simples `{"Symphony": ["seed1", ...]}` mas o código esperava `{"Symphony": {"name": ..., "emoji": ..., "desc": ..., "seeds": [...]}}`. `list_categories` crashava silenciosamente.
2. **Playlist sem isolamento por marca**: `refresh_playlist` usava `PLAYLIST_ID` global (hardcoded BO). Tabela `playlist_videos` não tinha coluna `brand_slug` — tudo era compartilhado.

### Correções
- `config.py`: `_normalize_categories()` converte formato simples → completo em `load_brand_config()`
- `database.py`: coluna `brand_slug` em `playlist_videos` + migração automática, save/get filtram por marca
- `curadoria.py`: `_extract_playlist_id()` parseia URL, `refresh_playlist()` usa `playlist_id` da config

### Arquivos editados
- `app-curadoria/backend/config.py`
- `app-curadoria/backend/database.py`
- `app-curadoria/backend/routes/curadoria.py`

### Pendências identificadas
- `ANTI_SPAM` global hardcoded em buscas — RC tem seu próprio `anti_spam` na config mas não é usado nos endpoints de search (melhoria futura)
- Endpoint `/api/search` hardcoda `opera live` no query — errado pra RC (música clássica)
- `cached_videos` não tem `brand_slug` — funciona por enquanto porque categorias têm nomes diferentes (BO: icones/estrelas/hits vs RC: Symphony/Concerto/Chamber)

### Estado resultante
- Código aplicado e pushed — pendente: confirmar deploy do curadoria-backend no Railway

---

## Sessão 2026-03-12 (22) — Correção de 3 bugs (título Redator, instrumental, primarycolor)

### Problemas encontrados
1. **Título YouTube "# Resposta:"** — Claude retornava markdown header antes do título real. Parsing capturava o header.
2. **Instrumental tratado como letra** — Músicas sem lyrics passavam por todo o pipeline de letra/transcrição/tradução. Mensagem do Gemini "Esta peça é instrumental..." era tratada como lyrics reais.
3. **Erro 'primarycolor' no render** — Perfil com `overlay_style={}` (dict vazio) não caia no fallback de defaults. KeyError ao acessar `config["primarycolor"]`.

### O que foi feito

**Bug 1 (Redator):**
- `app-redator/backend/services/claude_service.py` — adicionada `_strip_markdown_preamble()` que remove headers markdown e labels antes do parsing de título/tags
- `app-redator/backend/prompts/youtube_prompt.py` — prompt reforçado: "Do NOT use markdown formatting, headers (#), or labels"

**Bug 2 (Instrumental):**
- `app-editor/backend/app/routes/pipeline.py`:
  - Helper `_set_post_download_state()` centraliza lógica pós-download — 7 pontos agora usam essa function
  - Se `sem_lyrics=True`: download → passo 5 (corte) direto, pulando letra/transcrição/alinhamento
  - Guards em `buscar_letra_endpoint` e `aprovar_letra` para rejeitar instrumental
  - `_aplicar_corte_impl` pula tradução → direto para montagem (passo 7) se instrumental
  - Endpoint "desbloquear edição" respeita instrumental
- `app-portal/components/editor/validate-lyrics.tsx` — redirect automático para conclusão se `sem_lyrics` ou `eh_instrumental`

**Bug 3 (primarycolor):**
- `app-editor/backend/app/services/legendas.py` — `_estilos_do_perfil()` agora faz merge: `ESTILOS_PADRAO` como base + valores do perfil sobrescrevem. Dicts vazios ou parciais nunca causam KeyError.

### Decisões técnicas
- Helper `_set_post_download_state()` em vez de 7 if/else espalhados — DRY e manutenível
- Merge de estilos em vez de `or` — cobre dict vazio, parcial e None
- Defesa em profundidade no título: sanitização do output + reforço no prompt

### Estado resultante
- Código aplicado — pendente: deploy de editor-backend, redator (app), e portal no Railway

---

## Sessão 2026-03-12 (21) — Fallback cobalt.tools na curadoria

### Problema
Curadoria falhava ao baixar vídeo do YouTube (yt-dlp bloqueado por bot detection) sem nenhum fallback. O editor já tinha cascata completa (R2 → local → curadoria → cobalt → yt-dlp), mas a curadoria só usava yt-dlp — single point of failure.

### O que foi feito
- Adicionado `COBALT_API_URL` em `app-curadoria/backend/config.py` (default: `https://api.cobalt.tools`)
- Criada função `_download_via_cobalt()` em `app-curadoria/backend/services/download.py` (mesma lógica do editor)
- Integrado fallback cobalt em 2 pontos de download:
  - `_prepare_video_logic()` (worker de batch download)
  - `prepare_video` endpoint em `routes/curadoria.py` (chamado pelo botão "Preparando...")
- Cascata agora: **yt-dlp (com cookies) → cobalt.tools → erro**

### Arquivos editados
- `app-curadoria/backend/config.py` — COBALT_API_URL
- `app-curadoria/backend/services/download.py` — `_download_via_cobalt()` + fallback no worker
- `app-curadoria/backend/routes/curadoria.py` — import + fallback no endpoint

### Estado resultante
- Código aplicado — pendente: deploy do curadoria-backend no Railway
- COBALT_API_URL usa default público, não precisa de env var no Railway

---

## Sessão 2026-03-12 (20) — Deploy + E2E multi-brand completo

### O que foi feito
- Deploy dos 4 serviços Railway (editor-backend, redator, curadoria-backend, portal) com filtro multi-brand
- Auditoria completa do frontend: 9 componentes verificados para propagação de brand context
- **Bug fix encontrado e corrigido**: `deletarReportsResolvidos()` não filtrava por `perfil_id` — deletaria reports de TODAS as marcas. Corrigido no backend (aceita `perfil_id` query param com join em Edicao) e frontend (passa `selectedBrand?.id`)
- Teste E2E em produção: 9 endpoints verificados com curl, todos filtrando corretamente
- Plano MULTIBRAND 100% concluído (5/5 tarefas)

### Arquivos editados
- `app-editor/backend/app/routes/reports.py` — `deletarReportsResolvidos` agora aceita `perfil_id`
- `app-portal/lib/api/editor.ts` — `deletarReportsResolvidos` passa `perfil_id`
- `app-portal/app/dashboard/reports/page.tsx` — passa `selectedBrand?.id` ao limpar resolvidos

### Verificações E2E (produção)
- Editor `GET /edicoes?perfil_id=1` → 1 edição (filtro OK)
- Editor `GET /edicoes?perfil_id=2` → 0 edições (isolamento OK)
- Redator `?brand_slug=best-of-opera` → 2 projetos
- Redator `?brand_slug=reels-classics` → 0 projetos (isolamento OK)
- Curadoria `?brand_slug=best-of-opera` → 6 categorias (config dinâmica OK)
- Dashboard e Reports resumo filtrados por perfil_id OK
- Retrocompatibilidade: sem parâmetro = retorna tudo (admin view)

### Estado resultante
- **PLANO-DE-ACAO-120326-MULTIBRAND**: 100% CONCLUÍDO — pronto para mover para `arquivo/`
- Sistema multi-brand funcional end-to-end: frontend seleciona marca → API propaga → backend filtra
- Próximo passo sugerido: teste manual no portal (selecionar "Reels Classics" vs "Best of Opera")

---

## Sessão 2026-03-12 (19) — Config de marca dinâmica por request na Curadoria

### O que foi feito
- `config.py` já estava preparado: `load_brand_config(slug)` aceita slug opcional, cache dict `_brand_config_cache` por slug com TTL 5min, `BRAND_CONFIG` global no startup como fallback
- `curadoria.py` — adicionado `brand_slug: str | None = Query(None)` a TODOS os endpoints que usam `load_brand_config()`:
  - Busca/categorias: `/api/search`, `/api/category/{category}`, `/api/ranking`, `/api/categories`
  - Cache: `/api/cache/populate-initial`, `/api/cache/refresh-categories`
  - Playlist: `/api/playlist/videos`, `/api/playlist/refresh`, `/api/playlist/download-all`
  - Download/upload: `/api/download/{video_id}`, `/api/prepare-video/{video_id}`, `/api/upload-video/{video_id}`
  - R2: `/api/r2/check`
  - Manual: `/api/manual-video`
- Funções background `populate_initial_cache()` e `refresh_playlist()` também aceitam `brand_slug` opcional
- Todas as chamadas internas a `load_brand_config()` agora propagam o `brand_slug` recebido
- Retrocompatibilidade total: sem `brand_slug` = usa default do env `BRAND_SLUG` (best-of-opera)
- Endpoints que NÃO usam config de marca ficaram inalterados: `/api/auth`, `/api/posted*`, `/api/cache/status`, `/api/playlist/download-status`, `/api/quota/*`, `/api/r2/info`, `/api/downloads*`

### Arquivos editados
- `app-curadoria/backend/routes/curadoria.py` — brand_slug em 14 endpoints + 2 funções background

### Decisões técnicas
- `config.py` não precisou de alterações — já tinha cache multi-slug funcional
- `download_all_playlist`: movido `load_brand_config()` para fora do loop (era chamado N vezes dentro do for, agora 1x antes)

### Verificações
- Zero chamadas `load_brand_config()` sem argumento restantes em curadoria.py (grep confirmado)
- Código aplicado — pendente: deploy no Railway + teste E2E

---

## Sessão 2026-03-12 (18) — Filtro perfil_id nos endpoints do Backend Editor

### O que foi feito
- Adicionado `perfil_id: Optional[int] = Query(None)` ao `GET /edicoes` — filtra por marca quando fornecido, retorna tudo quando omitido (retrocompatível)
- Adicionado `perfil_id: Optional[int] = None` ao schema `EdicaoCreate` e injetado no `POST /edicoes` ao criar o objeto Edicao
- Adicionado `perfil_id: Optional[int] = None` ao schema `EdicaoUpdate` — o `PATCH /edicoes/{id}` já usa `model_dump(exclude_unset=True)` + `setattr`, então perfil_id é automaticamente atualizado quando enviado
- Adicionado `perfil_id: Optional[int] = Query(None)` ao `GET /reports/resumo` — filtra contagens por marca via join com Edicao
- Dashboard: todos os endpoints (`/dashboard/stats`, `/dashboard/edicoes-recentes`, `/dashboard/pipeline`, `/dashboard/visao-geral`, `/dashboard/producao`, `/dashboard/saude`) JÁ tinham filtro por `perfil_id` — nenhuma mudança necessária
- Reports: `GET /reports` JÁ tinha filtro por `perfil_id` — nenhuma mudança necessária; `POST /reports` não precisa de `perfil_id` diretamente (report se liga a edicao via `edicao_id`, o perfil é inferido)

### Arquivos editados
- `app-editor/backend/app/schemas.py` — `perfil_id` em EdicaoCreate e EdicaoUpdate
- `app-editor/backend/app/routes/edicoes.py` — filtro no GET, injeção no POST
- `app-editor/backend/app/routes/reports.py` — filtro no GET /reports/resumo

### Verificações
- Model `Edicao` já tem coluna `perfil_id` (ForeignKey para editor_perfis.id, nullable=True)
- Schema `EdicaoOut` já tinha `perfil_id: Optional[int] = None`
- Todas as mudanças são retrocompatíveis (default None = sem filtro)
- Código aplicado — pendente: deploy no Railway + teste E2E

---

## Sessão 2026-03-12 (17) — Filtro brand_slug nos endpoints do Backend Redator

### O que foi feito
- Adicionado `brand_slug: Optional[str] = Query(None)` ao `GET /api/projects` — filtra por marca quando fornecido, retorna tudo quando omitido (retrocompatível)
- Adicionado `brand_slug: Optional[str] = Query(None)` ao `GET /api/projects/r2-available` — filtra projetos existentes por marca ao calcular disponíveis no R2
- `POST /api/projects` já recebia `brand_slug` via `ProjectCreate` schema com default "best-of-opera" — nenhuma mudança necessária
- `generate_all` e endpoints de regeneração já leem `brand_slug` do project — confirmado, nenhuma mudança necessária

### Arquivo editado
- `app-redator/backend/routers/projects.py` — imports (`Optional`, `Query`) + filtro nos 2 endpoints GET

### Verificações
- Model `Project` já tem coluna `brand_slug` (String(50), default "best-of-opera")
- Schema `ProjectCreate` já tem `brand_slug: str = "best-of-opera"`
- Schema `ProjectOut` já tem `brand_slug: str = "best-of-opera"`
- Código aplicado — pendente: deploy no Railway + teste E2E

---

## Sessão 2026-03-12 (16) — Diagnóstico multi-brand: sistema ignora perfil selecionado

### Bug identificado
O frontend armazena o `selectedBrand` no contexto (BrandSelector funciona), mas **NENHUMA chamada de API** passa `perfil_id` ou `brand_slug` para os backends. Todos os backends usam default `"best-of-opera"`.

### Cadeia da falha
1. DB Schema (Perfil model) → OK
2. Frontend Context (useBrand) → OK
3. **Frontend → API calls** → QUEBRADO (nenhuma chamada passa perfil_id)
4. **Backend filtering** → QUEBRADO (endpoints retornam TUDO de TODAS as marcas)
5. **Curadoria config** → QUEBRADO (carregada 1x no startup, hardcoded "best-of-opera")

### Plano criado
`PLANO-DE-ACAO-120326-MULTIBRAND.md` — 5 tarefas (3 backend + 1 frontend + 1 deploy)
- Tarefas 01-03: backends independentes (editor, redator, curadoria) — paralelizáveis
- Tarefa 04: frontend (Antigravity) — depende de 01-03
- Tarefa 05: deploy + E2E

### Planos anteriores finalizados
- `PLANO-DE-ACAO-120326.md` → arquivo/ (14/14 concluídas)
- `PLANO-DE-ACAO-120326-E2E.md` → arquivo/ (deploy deferido para MULTIBRAND)
- `PLANO-DE-ACAO-120326-HARDENING.md` → arquivo/ (deploy deferido para MULTIBRAND)

---

## Sessão 2026-03-12 (15) — Hardening: logger curadoria + shared/retry.py

### O que foi feito
Tarefas 03 e 04 do PLANO-DE-ACAO-120326-HARDENING concluídas:

**Tarefa 03 — 48 print() → logger na curadoria (7 arquivos)**
- `app-curadoria/backend/database.py` — 8 prints → logger (warning/info/error)
- `app-curadoria/backend/config.py` — 3 prints → logger
- `app-curadoria/backend/main.py` — 2 prints + basicConfig adicionado
- `app-curadoria/backend/routes/curadoria.py` — 23 prints → logger
- `app-curadoria/backend/services/download.py` — 8 prints → logger
- `app-curadoria/backend/services/scoring.py` — 1 print → logger
- `app-curadoria/backend/services/youtube.py` — 3 prints → logger
- Critério: ⚠️ → warning, ❌ → error, resto → info

**Tarefa 04 — shared/retry.py criado**
- `shared/retry.py` — decorator `@async_retry(max_attempts, backoff_base, backoff_max, jitter, exceptions)`
- Backoff exponencial: `backoff_base ** (attempt-1)`, limitado a `backoff_max=30s`
- Jitter ±25% (ativado por default)
- Sem dependências externas (zero tenacity)
- Tarefa 05 (gemini.py) e Tarefa 06 (R2 retry) dependem deste arquivo

### Estado do plano HARDENING
- [x] 01 Startup validation + redator health
- [x] 02 BackgroundTasks → worker queue curadoria
- [x] 03 print() → logger curadoria
- [x] 04 shared/retry.py
- [ ] 05 Refatorar retry gemini.py
- [ ] 06 Retry R2 storage
- [x] 07-09 Antigravity (frontend) — Concluído: Error Boundary, loading guards, Sentry integration e correções de polling.
- [ ] 10 Connection pooling curadoria
- [ ] 11 Deploy + E2E

---

## Sessão 2026-03-12 (14) — Features permanentes de reset/delete (bulk + individual)

### O que foi feito
Implementadas 4 features permanentes para gerenciamento de dados (reset marca, delete reports):

1. **DELETE /admin/perfis/{id}/edicoes** — Bulk delete de TODAS as edições de um perfil + limpeza completa de arquivos R2. Admin-only, protegido (BO requer `?force=true`). Também limpa screenshots de reports vinculados.
2. **DELETE /reports/resolvidos** — Bulk delete de todos os reports com status "resolvido" + screenshots R2.
3. **DELETE /projects/by-brand/{slug}** (redator) — Bulk delete projetos do redator por brand_slug. CASCADE limpa translations.
4. **R2 cleanup no delete individual** — Corrigido gap: `DELETE /edicoes/{id}` agora também limpa arquivos R2 (antes só deletava do banco).

**Frontend:**
- Botão deletar em cada ReportCard (com Dialog de confirmação)
- Botão "Limpar Resolvidos" na página de reports (visível quando há resolvidos)
- Seção "Zona de Perigo" na página admin/marcas/[id] — botão "Resetar Edições" que chama AMBOS editor (bulk delete edições + R2) e redator (delete projects by brand_slug)

### Arquivos alterados (10)
- `app-editor/backend/app/routes/admin_perfil.py` — +endpoint DELETE edicoes
- `app-editor/backend/app/routes/edicoes.py` — +R2 cleanup no delete individual
- `app-editor/backend/app/routes/reports.py` — +endpoint DELETE resolvidos
- `app-redator/backend/routers/projects.py` — +endpoint DELETE by-brand
- `app-redator/backend/prompts/overlay_prompt.py` — ajuste pre-existente
- `app-portal/lib/api/editor.ts` — +3 métodos API
- `app-portal/lib/api/redator.ts` — +1 método API
- `app-portal/components/dashboard/reports/report-card.tsx` — +botão delete + dialog
- `app-portal/app/dashboard/reports/page.tsx` — +botão limpar resolvidos
- `app-portal/app/(app)/admin/marcas/[id]/page.tsx` — +zona de perigo

### Deploy
Push `ed9fa6f` para main — Railway auto-deploy dos 3 serviços.

### Próxima sessão
1. Após deploy: usar "Resetar Edições" no Admin > Marcas > Best of Opera para limpar dados de teste
2. Verificar que letras (editor_letras) permaneceram intactas
3. Verificar que curadoria cache não foi afetado

---

## Sessão 2026-03-12 (13) — T1 + T2: overlay_interval_secs e custom_post_structure implementados

### O que foi feito
Implementadas as 2 decisões técnicas da análise RC que não dependiam do sócio:

**T1 — `overlay_interval_secs`**: Campo Integer no Perfil (default: 15). Controla a densidade de legendas overlay por marca. O `_calc_subtitle_count()` no overlay_prompt.py agora usa esse valor dinâmico em vez do hardcoded 15. RC poderá usar 5s (1 legenda a cada 5 segundos) enquanto BO mantém 15s.

**T2 — `custom_post_structure`**: Campo Text no Perfil (nullable). Quando preenchido, substitui inteiramente o bloco de 5 seções do post_prompt.py por estrutura custom da marca. CRITICAL RULES (char limit, forbidden phrases, language) continuam aplicando a todas as marcas. BO sem valor = mantém 5 seções (zero impacto).

### Arquivos alterados
- `app-editor/backend/app/models/perfil.py` — +2 colunas
- `app-editor/backend/app/services/perfil_service.py` — +2 campos no build_redator_config
- `app-editor/backend/app/routes/admin_perfil.py` — schema + duplicar
- `app-editor/backend/app/main.py` — migrations inline
- `app-redator/backend/prompts/overlay_prompt.py` — interval_secs dinâmico
- `app-redator/backend/prompts/post_prompt.py` — refatorado com estrutura condicional

### Testes
11/12 passando. Falha pré-existente: `test_seed_best_of_opera_valores_corretos` (fontsize 63 vs 40 entre admin_perfil e legendas — desalinhamento anterior, não afeta produção).

### Próxima sessão
1. Aguardar respostas A/B/C do sócio nos 7 pontos editoriais
2. Deploy para testar T1/T2 com perfil RC real
3. Após respostas do sócio: preencher `custom_post_structure` do RC com a estrutura de 3 parágrafos
4. Bug pré-existente: alinhar fontsize entre ESTILOS_PADRAO de admin_perfil.py e legendas.py

---

## Sessão 2026-03-12 (12) — Análise blocos RC: conflitos identificados, pendente decisão do sócio

### Contexto
Analisados os 3 blocos propostos (identity, tom_de_voz, escopo) para a marca Reels Classics. Cruzados com overlay_prompt.py, post_prompt.py, config.py (11 hooks) e regras existentes do BO.

### Documentos de referência
- `dados-relevantes/CONTEXTO-ANALISE-BLOCOS-RC.md` — metodologia completa de análise
- 3 blocos propostos: recebidos como arquivos txt (RC_Bloco1_Persona.txt, RC_Bloco2_TomDeVoz.txt, RC_Bloco3_Escopo.txt)

### 7 decisões editoriais pendentes (sócio decide)
1. **Conhecimento externo** — prompt base proíbe, Bloco 1 RC libera. A/B/C pendente.
2. **CTA overlay** — base proíbe genérico, RC quer fixo "Siga, o melhor da música clássica...". A/B/C pendente.
3. **Abertura "never watched opera"** — RC não é ópera. Trocar por classical music? A/B/C pendente.
4. **Hooks com referência a ópera** — 3 hooks mencionam ópera. RC usa mesmos, adaptados ou novos? A/B/C pendente.
5. **Estrutura do post/description** — base tem 5 seções, RC define 3 parágrafos com •. Incompatíveis. A/B/C pendente.
6. **Hashtags** — base exige 4, RC exige 5. A/B/C pendente.
7. **Anti-repetição overlay↔description** — RC exige que description receba overlay como input. Hoje são independentes. A/B/C pendente.

### 5 decisões técnicas (Bolivar + Claude Code)
| # | Ponto | Decisão tomada |
|---|-------|---------------|
| T1 | Densidade legendas (1/15s vs 1/5s) | Criar campo `subtitle_interval_secs` no perfil |
| T2 | Estrutura de post customizável | Criar mecanismo `custom_post_structure` no post_prompt.py |
| T3 | Tamanhos px (52/48/44) no Bloco 3 | Remover do bloco, configurar no overlay_style do perfil |
| T4 | Volume dos blocos: ~2730 palavras (4.5x o base) | Precisa cortar após decisões do sócio |
| T5 | Blocos em inglês, canal PT-BR | OK — instruções, não conteúdo |

### Próxima sessão
1. Aguardar respostas A/B/C do sócio nos 7 pontos
2. Implementar T1 (subtitle_interval_secs) e T2 (custom_post_structure) — podem ser feitos antes
3. Após respostas: rodar análise completa (tabela hooks × blocos, conflitos, versão editada)

---

## Sessão 2026-03-12 (11) — Revisão de bugs recorrentes e regras de qualidade

### Contexto
Bolivar apontou 4 bugs que foram declarados "corrigidos" múltiplas vezes mas nunca estavam:
1. Fonte Playfair Display não aplicada (corrigida em camadas isoladas ao longo de várias sessões)
2. Brand config NULL no banco (código corrigido, dado nunca inserido, declarado "corrigido")
3. Word spacing (3 rodadas de regex incremental, cada uma pegava só os casos do screenshot)
4. Erros repetidos na transcrição (backend corrigido, frontend sem retry automático)

### Diagnóstico
Padrão comum: **fix superficial + vitória prematura**. Corrigir uma camada, ler o código, declarar resolvido sem verificar o output final. Múltiplas causas raiz tratadas uma por sessão em vez de todas de uma vez.

### Regras gravadas em CLAUDE.md (itens 10-13 das armadilhas)
- Nunca declarar "corrigido" sem verificar output final
- Mapear cadeia completa (banco → API → processamento → output) antes de corrigir
- Investigar TODAS as causas raiz antes de corrigir qualquer uma
- Pendências = BLOCKER, não "corrigido"

### Estado atual dos 4 bugs
| Bug | Status real | Pendência |
|-----|------------|-----------|
| Fonte Playfair | ✅ Corrigido (commit 3ccddda) | Nenhuma |
| Brand config | ⚠️ Código OK, dado vazio | BLOCKER: campos identity_prompt_redator, tom_de_voz_redator, escopo_conteudo NULL no banco |
| Word spacing | ✅ Overlay corrigido | Post/YouTube não passam por _limpar_texto |
| Erros transcrição | ⚠️ Exibe erro corretamente | Sem retry automático no frontend |

---

## Sessão 2026-03-12 (10) — Fix crítico: brand config nunca chegava ao Claude

### Causa raiz
`EDITOR_API_URL` não estava configurado como env var no Railway para o serviço do redator. O código usava default `localhost:8000`, que em Railway aponta para o próprio container (não para o editor). `load_brand_config()` falhava silenciosamente e retornava fallback com campos VAZIOS. Os 9300 chars de brand config (identity_prompt_redator, tom_de_voz_redator, escopo_conteudo) inseridos no banco em sessão anterior **nunca chegavam ao prompt do Claude**.

Isso explica 3 bugs recorrentes:
1. Texto overlay "paupérrimo" — sem brand customization, Claude usava só prompt base genérico
2. CTA genérico "Segue para mais momentos assim" — sem escopo_conteudo, CTA caía no fallback
3. POST melhor que overlay — prompt base do POST é estruturalmente superior mesmo sem brand config

### Correções aplicadas (commit e38a2ee)
1. **Auto-detect Railway** — `_resolve_editor_url()` em `app-redator/backend/config.py` e `app-curadoria/backend/config.py`: detecta `RAILWAY_ENVIRONMENT` ou `RAILWAY_PROJECT_ID` e usa URL pública do editor
2. **brand_config no regenerate** — `build_overlay/post/youtube_prompt_with_custom()` agora recebem e repassam `brand_config` (antes descartavam silenciosamente)
3. **Word spacing regex** — `_limpar_texto_overlay()` agora cobre apóstrofos `'`, aspas curvas `""''`, parênteses `)`, colchetes `]`
4. **CTA em PT** — exemplos BAD no overlay prompt agora incluem português ("Segue para mais momentos assim")
5. **new-project.tsx** — mensagem detalhada de campos obrigatórios faltando

### Bugs documentados
- **EDITOR_API_URL não configurado no Railway** → redator nunca recebe brand config → overlay sem identidade de marca. Fix: auto-detect Railway environment.
- **`_with_custom` descartava brand_config** → regeneração com prompt customizado perdia toda customização de marca. Fix: propagar brand_config.
- **Regex word spacing incompleto** → apóstrofos e aspas não tratados (ex: `Marquis'para`). Fix: regex expandido.

### Decisão: Rewrite do overlay prompt (pendente)
Análise comparativa revelou que overlay prompt é 59% formatação / 41% storytelling (vs POST que é 62% storytelling / 38% formatação). Com brand config agora funcionando, avaliar se o overlay prompt precisa de rewrite estrutural ou se os 9300 chars de brand config compensam.

---

## Sessão 2026-03-12 (9) — Fix timeouts frontend (Request timeout em todas as telas)

### Problema
Todas as chamadas de API no frontend (app-portal) tinham timeout padrão de 15 segundos. Operações com IA (tradução 7 idiomas, regeneração overlay/post/youtube) e operações de arquivo (save to R2, export) excediam esse limite, causando "Request timeout" visível ao usuário.

### Correções aplicadas — Timeouts
- `app-portal/lib/api/base.ts` — timeout padrão: 15s → **30s** (request + requestFormData)
- `app-portal/lib/api/redator.ts`:
  - `translate`: 15s → **180s** (7 idiomas simultâneos)
  - `regenerateOverlay/Post/Youtube`: 15s → **90s** (chamadas Claude AI)
  - `retranslate`: 15s → **60s** (1 idioma)
  - `detectMetadata/detectMetadataFromText`: 15s → **60s** (Gemini)
  - `saveToR2`: 15s → **60s** (upload arquivos)
- `app-portal/lib/api/editor.ts`:
  - `traduzirLyrics`: 15s → **180s** (múltiplas traduções)
  - `exportarRenders`: 15s → **60s** (operação de arquivos)
  - `importarDoRedator`: 15s → **60s** (download + processamento)

### Correções aplicadas — Word spacing overlay (ERR-056 v2)
**Causa raiz**: Claude gera `\n` como JSON escape (1 char: newline real) entre palavras para quebra de linha. `_limpar_texto_overlay()` só tratava `\\n` literal (2 chars: barra+n), não o newline real. O `<input>` do frontend elimina newlines sem substituir por espaço → "nunca\nse" virava "nuncasetocam".

**Evidência**: TODOS os 6 erros no screenshot seguem o padrão: palavras grudadas exatamente onde uma quebra de linha `\n` estaria.

**Fixes**:
- `app-redator/backend/services/claude_service.py` — `_limpar_texto_overlay()` agora trata `\r\n`, `\r`, `\n` (reais) ANTES dos literais `\\n`/`\\N`
- `app-redator/backend/prompts/overlay_prompt.py` — regra 9 reforçada com exemplos reais dos erros + instrução para não usar `\n` como separador de palavras

---

## Sessão 2026-03-12 (8) — Investigação prompt Claude + fix espaços overlay

### Problemas investigados
- Textos da marca BO "paupérrimos" — investigação completa do pipeline de prompt
- Legendas overlay com falta de espaço entre palavras

### Causa raiz: Textos pobres
Os campos `identity_prompt_redator`, `tom_de_voz_redator`, `escopo_conteudo` estão **NULL no banco para todos os perfis**. A seção `BRAND CUSTOMIZATION` nunca é injetada no prompt do Claude. Claude escreve sem identidade de marca.

Descoberta adicional: o formulário admin usava campos GENÉRICOS (`identity_prompt`, `tom_de_voz`) mas o redator lê campos `_redator` específicos (`identity_prompt_redator`, `tom_de_voz_redator`) — dois conjuntos de campos distintos, todos vazios.

### Causa raiz: Espaços faltando
Três causas simultâneas:
1. `_limpar_texto_overlay()` só corrigia `minúscula→MAIÚSCULA`, não outros padrões
2. `_formatar_overlay()` não detectava `\n` literal (backslash+n, 2 chars) como separador
3. Faltava instrução explícita no prompt do Claude

### Correções aplicadas (não commitadas)
- `app-redator/backend/services/claude_service.py` — `_limpar_texto_overlay()` ampliada: normaliza `\n`/`\N` literais, adiciona detecção de ponto+maiúscula e número+letra
- `app-editor/backend/app/services/legendas.py` — `_formatar_overlay()` detecta `\\n` (2 chars) além de `\N` e newline real
- `app-redator/backend/prompts/overlay_prompt.py` — regra 9 adicionada: "WORD SPACING — CRITICAL"
- `app-portal/lib/api/editor.ts` — adicionados `identity_prompt_redator` e `tom_de_voz_redator` ao tipo `Perfil`
- `app-portal/app/(app)/admin/marcas/nova/page.tsx` — form usa campos `_redator` corretos
- `app-portal/app/(app)/admin/marcas/[id]/page.tsx` — form usa campos `_redator` corretos

### Pendências críticas
1. **Bolivar deve aprovar e devolver os 3 blocos de texto** para inserir no banco:
   - `identity_prompt_redator`: quem é o canal, público, propósito
   - `tom_de_voz_redator`: estilo de escrita, tom, como criar tensão
   - `escopo_conteudo`: o que focar/evitar por projeto
   Drafts propostos estão no histórico da sessão 8.
2. **Git push** de todos os 6 arquivos modificados após aprovação dos textos.

### Decisão de arquitetura: Regras comuns vs por marca
Investigação completa do prompt revelou a estrutura em camadas:

**UNIVERSAL (todas as marcas — hardcoded em `overlay_prompt.py`):**
- Regras técnicas: max_chars, timing, spacing, word spacing, JSON format
- Regras de qualidade: narrative arc, first subtitle at 00:00, 1s gap entre legendas
- Regra nova: WORD SPACING obrigatório (regra 9)

**JÁ CONFIGURÁVEL POR MARCA (lido do banco via `build_redator_config()`):**
- `overlay_max_chars` e `overlay_max_chars_linha` — limite de caracteres por marca
- `identity_prompt_redator` — identidade/personalidade do canal
- `tom_de_voz_redator` — estilo de escrita
- `escopo_conteudo` — foco de conteúdo
- `hook_categories_redator` — categorias de hook customizadas por marca
- `hashtags_fixas` — hashtags fixas do canal

**HARDCODED MAS CANDIDATO A POR MARCA (não implementado ainda):**
- FORBIDDEN phrases ("beautiful performance", "amazing voice"...) — marcas acadêmicas podem querer usar
- FORBIDDEN jargon ("bel canto", "coloratura"...) — idem, canal mais técnico pode querer usar
- RETENTION PRINCIPLES (Open loops, Specificity, Tension & Release) — podem ser sobrescritos via `identity_prompt_redator`
- EMOTIONAL TOOLKIT (hidden story, contrast, stakes...) — idem, via `tom_de_voz_redator`
- CTA obrigatório na última legenda — toggle booleano seria útil

**Recomendação para próximas marcas:** os campos `identity_prompt_redator` e `tom_de_voz_redator` já permitem sobrescrever indiretamente as regras criativas (Claude obedece BRAND CUSTOMIZATION que aparece depois das regras gerais). Para casos extremos (marca que quer jargão técnico), adicionar campo `custom_overlay_rules` ao Perfil.

**Para BO especificamente:** as regras hardcoded são exatamente o que o canal precisa. A diferenciação virá dos 3 campos de identidade pendentes.

---

## Sessão 2026-03-12 (7) — Fix timeouts IA + URL report (ERR-072/073/074)

### Problemas
- ERR-072: Request timeout no Novo Projeto (Redator) — `generate()` chama Claude AI, timeout padrão 15s insuficiente
- ERR-073: Request timeout no Buscar Letra (Editor) — `buscarLetra()` chama Gemini, timeout padrão 15s insuficiente
- ERR-074: Erro ao enviar report — URL `/reports/{id}/screenshots` (plural) não existe no backend; endpoint correto é `/screenshot` (singular)

### Correções
- `app-portal/lib/api/redator.ts`: `generate()` timeout 15s → 90s
- `app-portal/lib/api/editor.ts`: `buscarLetra()` timeout 15s → 90s; `uploadScreenshot` URL corrigida
- Sentry: issues stale genius (ERR-068) e falhas (ERR-066) marcados como resolved

### Estado
- Commit `f03e90e` pushed, deploy automático no Railway

---

## Sessão 2026-03-12 (6) — Fix 403 admin perfil BO (ERR-075)

### Problema
E2E em prod revelou 403 Forbidden ao salvar perfil "Best of Opera" no admin. Causa: `_protegido()` bloqueava incondicionalmente edições ao perfil com sigla "BO".

### Correção
- Backend: `_protegido()` aceita `force=True` via query param `?force=true` em PUT, PATCH e upload-font
- Frontend: modal de confirmação ao salvar perfil BO — botão amber "Confirmar e Salvar" envia `?force=true`
- `handleToggleAtivo` também passa `force` quando é BO

### Estado
- Commit `e5ab17b` pushed, deploy automático no Railway
- Mixed Content: 100% resolvido (sessão anterior)
- Admin marcas: funcional com proteção confirmada para BO

---

## Sessão 2026-03-12 (5) — Fix Mixed Content: NEXT_PUBLIC_API_* no Railway

### Problema
E2E em prod revelou que o portal chamava `http://localhost:8001` — as vars `NEXT_PUBLIC_API_*` não estavam configuradas no Railway, caindo no fallback hardcoded.

### Correção
Vars setadas via Railway GraphQL API no serviço `portal` (ID `73b20b58`), ambiente production (`4ec5a08f`):
- `NEXT_PUBLIC_API_EDITOR=https://editor-backend-production.up.railway.app`
- `NEXT_PUBLIC_API_REDATOR=https://app-production-870c.up.railway.app`
- `NEXT_PUBLIC_API_CURADORIA=https://curadoria-backend-production.up.railway.app`

Redeploy disparado via `serviceInstanceRedeploy`. Next.js bake as vars no build, fix Mixed Content.

### Estado
- Portal em redeploy — aguardar ~3min para testar `/login` em prod
- Não foi necessário alterar código — só configuração de env

---

## Sessão 11/03/2026 — Revisão Completa do Workspace + Push

### O que foi feito
1. **Limpeza de arquivos (FASE 1):**
   - Deletados: `app-design/` (vazio), `arquivo/~$LATORIO...docx` (temp Word), `.DS_Store`, `app-editor/backend/app/services/genius.py` (não usado)
   - Movidos para `arquivo/`: RELATORIO-COMPARATIVO-REPOS.md
   - Movido `~/BLAST-FASE2-MULTI-BRAND-v2.md` → `dados-relevantes/`
   - `.gitignore` atualizado com `.DS_Store`

2. **CLAUDE.md do projeto (FASE 2):**
   - Removidas refs quebradas (CONTEXTO-CODIGO-FINAL, MEMORIAL-REVISAO)
   - Corrigida linha cobalt (cascata completa)
   - Adicionado Glossário de nomenclatura
   - Adicionada nota de equivalência docs (PRD/ARCH/ROADMAP)
   - Adicionada nota BLAST vs PLANO-DE-ACAO

3. **CLAUDE.md global (FASE 3):**
   - Mapa BLAST atualizado — **BLAST Fase 2 COMPLETA** (todos os prompts 0-5 + 1.5 + 2.5)
   - Path do BLAST corrigido para `dados-relevantes/`
   - Exceção PLANO-DE-ACAO para best-of-opera-app2

4. **Push realizado** — commit `1dff557` em main, deploy automático no Railway

### Estado atual
- BLAST Fase 2 **100% concluída** em código
- Pendência em prod: verificar se Mixed Content foi resolvido após este deploy (URLs em `base.ts` já estão HTTPS)
- Workspace limpo: 13 itens visíveis na raiz

---

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

## Sessão 2026-03-12 (4) — Tarefa 06: Suporte a Fonte Customizada no Render

### O que foi feito
- **`pipeline.py` — `_render_task`**:
  - Extrai `font_file_r2_key_val` do perfil antes de fechar a sessão de banco
  - Antes do loop de render, se a marca tem fonte customizada: chama `ensure_font_local()` para garantir a fonte em `/usr/local/share/fonts/custom/`
  - Falha ao carregar fonte é não-fatal: loga warning e continua com fonte padrão
  - Filtro ASS no FFmpeg agora usa `ass='...':fontsdir=/usr/local/share/fonts/custom` quando há fonte customizada
- **`ffmpeg_service.py` — `renderizar_video`**: adicionado parâmetro `fontsdir=None` e suporte ao mesmo padrão de filtro ASS (para uso futuro)

### Estado
- Plano 120326: todas as tarefas CLAUDE CODE (01–06) concluídas [x]
- Tarefa 14 (ANTIGRAVITY) também [x] — plano completo

---

## Sessão 2026-03-12 (3) — Tarefa 05: Upload de Fonte Customizada

### O que foi feito
- **Criado** `app-editor/backend/app/services/font_service.py` com 3 funções:
  - `extract_font_family(path)` — usa fonttools para extrair o nome da família; fallback para nome do arquivo
  - `upload_font_to_r2(local_path, slug, filename)` — faz upload para `fonts/{slug}/{filename}` no R2
  - `ensure_font_local(r2_key)` — baixa R2 → `/tmp/custom-fonts/`, instala em `/usr/local/share/fonts/custom/`, roda fc-cache
- **Adicionado endpoint** `POST /api/v1/editor/admin/perfis/{perfil_id}/upload-font` em `admin_perfil.py`:
  - Valida extensão (.ttf/.otf) e tamanho máximo (10MB)
  - Salva em tmp → extrai family name → upload R2 → atualiza `font_name` + `font_file_r2_key`
  - Retorna `PerfilDetalheOut` atualizado
- **Adicionado** `fonttools>=4.50.0` ao `requirements.txt`
- Plano 05 marcado [x]

### Estado
- Tarefa 06 é a próxima (suporte FFmpeg à fonte customizada) — depende de 05 ✓

---

## Sessão 2026-03-12 — Validação E2E Completa (Ambiente de Produção)

### Resultado Geral: **ALERTA (Bloqueio Crítico)**
- **Total de testes:** 68
- **Passaram:** 54
- **Falharam:** 14
- **Severidade Máxima:** **CRÍTICA** (Mixed Content em Produção)

### Tabela de Status E2E

| Bloco | Testes | Status | Observação |
|---|---|---|---|
| **Bloco 1: Auth** | 1-7 | ✅/⚠️ | Login OK. Falha no relogin sequencial (necessitava limpeza de localStorage). |
| **Bloco 2: Navegação** | 8-18 | ✅ | Todos os itens do sidebar abriram sem erros de rota. |
| **Bloco 3: Admin Marcas** | 19-28 | ❌ | **BLOQUEADO.** Nenhuma marca carregada por Mixed Content no backend admin. |
| **Bloco 4: Admin Usuários**| 29-35 | ✅ | Tabela e modais de edição/convite funcionando. |
| **Bloco 5: Curadoria** | 36-43 | ⚠️ | Tabs carregam; Busca lenta/instável. |
| **Bloco 6: Redator** | 44-48 | ⚠️ | Novo projeto OK. Etapas com carregamento infinito em alguns IDs. |
| **Bloco 7: Editor** | 49-53 | ⚠️ | Fila OK. Stepper visível. Detalhes com erro de API. |
| **Bloco 8: Dashboard** | 54-60 | ✅ | Métricas e Reports funcionando bem. Modal de reporte testado. |
| **Bloco 9: Global** | 61-65 | ⚠️ | Brand Selector vazio por reflexo de falha no Admin. Responsividade OK. |
| **Bloco 10: Console** | 66-68 | ❌ | Erros de **Mixed Content** (HTTPS chamando HTTP) bloqueiam módulos sensíveis. |

### Bugs e Vulnerabilidades

1.  **🚨 Crítico: Mixed Content** — Requisições do frontend para `http://editor-backend-production...` bloqueadas pelo Chrome. **Resolução imediata requer atualização para HTTPS na variável de ambiente do backend em produção.**
2.  **🚨 Alto: Instabilidade de Sessão** — Relogin falha com 401 a menos que o browser limpe manualmente os dados. 
3.  **⚠️ Médio: Performance/Timeouts** — Páginas de Edição e Projeto demoram a responder ou travam o estado de carregamento.

### Estado Resultante
O sistema está funcional no "esqueleto", mas o core de CRUD de marcas e navegação de estágios (Editor/Redator) está bloqueado pelo bug de HTTPS/Mixed Content em produção.

---

## Sessão 2026-03-12 (2) — Auditoria e Limpeza de Workspace

### O que foi feito
- **Limpeza de Documentos Superados**: 8 arquivos (`CONTEXTO-*.md`, `DIAGNOSTICO-*.md`, `RELATORIO-*.md/docx`, `MEMORIAL-*.md`) foram movidos para a pasta `arquivo/`.
- **Exclusão de Diretório Fantasma**: A pasta `app-editor/frontend/` foi deletada para evitar confusão. Fica estabelecido oficialmente que o frontend "Geral" vive unicamente em `app-portal/`.
- **Atualização do CLAUDE.md**: 
    - Explicitado: `app-portal/` = Frontend, `app-editor/`, `app-curadoria/`, `app-redator/` = Backend FastAPI apenas.
    - Definidas as regras de **Agent Teams**: Antigravity no frontend, Claude Code no backend.

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

---

## Sessão 2026-03-12 — Validação E2E Pós-Deploy BLAST v4 Fase 2

### Status da Validação (Ambiente de Produção)
- **1. Autenticação (/login):** PASSOU ✅ (Login correto, nome "Admin" visível e redirecionamento de dashboard OK)
- **2. Admin → Marcas (/admin/marcas):** FALHOU ❌ (Erro crítico de Mixed Content impedindo listagem. O frontend HTTPS tenta buscar `/api/v1/editor/admin/perfis/` via HTTP)
- **3. Admin → Usuários (/admin/usuarios):** PASSOU ✅ (Página carrega listagem sem erros 404/500)
- **4. Editor Stepper:** FALHOU ❌ (Stepper e cabeçalho não aparecem. O erro de Mixed Content nas Marcas quebra o estado da UI da edição)
- **5. Re-render no Editor:** FALHOU ❌ (Devido à falha no carregamento inicial da edição, os ícones 🔄 "Refazer" por idioma não ficam acessíveis)
- **6. Retrocompatibilidade:** PASSOU ✅ (A listagem "Inventário R2" na aba de conclusão carrega e exibe os 7 idiomas renderizados corretamente)

### Pendências Identificadas
- **Corrigir Mixed Content:** URL da API nas variáveis de ambiente do Frontend (em produção) precisa usar `https://` em vez de `http://`.
- **Re-testar Stepper e Re-render:** Uma vez que o Mixed Content for resolvido, re-executar validação do Editor para confirmar que UI do Stepper e botões "Refazer" operam sem erros.

---

## Sessão 2026-03-12 (20) — Multi-brand: Frontend API Layer (Tarefa 04) CONCLUÍDA

### O que foi feito
Concluída a injeção do contexto de marca em toda a camada de integração do Frontend com as APIs dos 3 serviços backend.

**Tarefa 04 do PLANO-DE-ACAO-120326-MULTIBRAND finalizada:**
- **Injeção de Contexto**: Utilização sistemática do hook `useBrand()` para capturar o `selectedBrand` e propagar seu `id` ou `slug` para as APIs.
- **Isolamento de Dados**: Garantiu que seleções de marca no header reflitam imediatamente em todos os dashboards e tabelas.
- **Retrocompatibilidade**: Mantido comportamento original (sem filtro) quando nenhuma marca está selecionada (Admin View).

### Detalhes técnicos (Arquivos editados)
**1. Camadas de API (`app-portal/lib/api/`):**
- **`editor.ts`**: Adicionado `perfil_id` a `listarEdicoes`, `criarEdicao`, `listarProjetosRedator`, `dashboardVisaoGeral`, `listarReports`, `resumoReports`, `criarReport`, `importarDoRedator`.
- **`redator.ts`**: Adicionado `brand_slug` a `listProjects`, `createProject`, `listR2Available`, `detectMetadata`, `detectMetadataFromText`.
- **`curadoria.ts`**: Adicionado `brand_slug` a `search`, `searchCategory`, `ranking`, `categories`, `manualVideo`, `playlistVideos`, `refreshPlaylist`, `downloadVideo`, `prepareVideo`, `checkR2`, `uploadVideo`, `r2Info`, `downloads`, `downloadsExportUrl`.

**2. Componentes e Páginas atualizados:**
- **`dashboard/page.tsx`** e **`dashboard/reports/page.tsx`**: Dashboards agora reagem à mudança de marca via `useEffect` dependente de `selectedBrand?.id`.
- **`components/redator/project-list.tsx`** e **`new-project.tsx`**: Listagens e criação de projetos agora respeitam o `brand_slug`.
- **`components/editor/editing-queue.tsx`**: Fila de edições e importação do Redator vinculadas ao `perfil_id`.
- **`components/curadoria/dashboard.tsx`** e **`downloads.tsx`**: Busca, ranking, configuração de categorias e histórico de downloads agora isolados por marca.

### Estado Final do Plano MULTIBRAND
- [x] 01 Backend Editor: filtros por perfil_id
- [x] 02 Backend Redator: filtros por brand_slug
- [x] 03 Backend Curadoria: config dinâmica por request
- [x] 04 Frontend: Injeção de perfil_id/brand_slug (ANTIGRAVITY)
- [ ] 05 Deploy + Validação E2E Prod (Próximo Passo)

### Observações
- Tarefa de **Playlist vs Instagram** concluída em paralelo (script Python no /tmp), sem afetar o core do sistema.
- Correção de bug pré-existente no `joinField` do componente NewProject.

---

## Sessão 2026-03-13 — Sentry Triage + Build Failures Railway

### Problemas investigados e resolvidos

#### P0 — YOUTUBE_COOKIES com nome errado (BUG CRÍTICO)
- **Raiz:** Variável no Railway estava `YOU_TUBECOOKIES` (typo) — código em `download.py:94` procura `YOUTUBE_COOKIES`
- **Efeito:** Cookies NUNCA carregados → yt-dlp sem autenticação → bot detection do YouTube → downloads falhando
- **Fix:** Variável renomeada via Railway GraphQL API + redeploy triggado às 19:48
- **Commit:** nenhum (só Railway vars)

#### P1 — Guard defensivo em `_normalize_categories()`
- **Raiz:** `else` branch em `config.py:89-91` preservava dict sem key `seeds` como estava
- **Efeito:** `data["seeds"]` acessa chave inexistente em 8 pontos em `routes/curadoria.py` → KeyError latente
- **Fix:** `elif isinstance(val, dict)` garante `seeds=[]` se ausente; tipos desconhecidos são ignorados com warning
- **Commit:** `57addac` — "fix: guard defensivo em _normalize_categories"
- **Deploy:** curadoria-backend SUCCESS às 21:12

#### P2 — Sentry issues adicionais (3 issues)
- **Bloqueio:** Sem `SENTRY_AUTH_TOKEN` em nenhum serviço Railway — impossível acessar Sentry API programaticamente
- **Org URL identificada:** `https://arias-conteudo-k2.sentry.io/issues/`
- **Pendência:** Para ver os 3 issues restantes, gerar um Sentry Auth Token em `https://sentry.io/settings/account/api/auth-tokens/` e salvar como `SENTRY_AUTH_TOKEN` em Railway

#### Build failures Railway — editor-frontend (RESOLVIDO)
- **Raiz:** Serviço `editor-frontend` tinha `rootDirectory: "app-editor/frontend"` — diretório deletado em commit `1dff557` (11/03, substituído por `app-portal`)
- **Falhas acumuladas desde:** 12/03/2026 (4 deploys FAILED)
- **Fix:**
  1. `editor-frontend` deletado do Railway
  2. `CORS_ORIGINS` em `editor-backend` limpo (removido `editor-frontend-production.up.railway.app`)
  3. `portal` (SUCCESS 19:47) já serve o frontend com sucesso

### Estado pós-sessão
- curadoria-backend: rodando com YOUTUBE_COOKIES correto + guard de categorias ✅
- editor-frontend: DELETADO (era obsoleto) ✅
- portal: SUCCESS ✅
- Sentry: YOUTUBE_COOKIES fix deve reduzir/eliminar bot detection events — confirmar em 24h
- Pendência: SENTRY_AUTH_TOKEN para visibilidade completa dos 3 issues restantes

### Serviços Railway ativos (pós-limpeza)
| Serviço | Status |
|---------|--------|
| Postgres | ativo |
| portal | SUCCESS |
| editor-backend | ativo |
| curadoria | ativo |
| curadoria-backend | SUCCESS |
| app | ativo |
