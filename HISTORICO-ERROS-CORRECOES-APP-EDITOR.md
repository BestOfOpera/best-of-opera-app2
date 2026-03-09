# Histórico Completo de Erros e Correções — App-Editor (Best of Opera)

**Gerado em:** 03 de março de 2026 (atualizado 09/03/2026 — BLAST v3)
**Projeto:** Best of Opera — App-Editor (APP3) + App-Redator (APP2)

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
