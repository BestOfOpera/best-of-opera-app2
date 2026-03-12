# Memorial — Revisão Arquitetural do App-Editor (Best of Opera)

**Data:** 25 de fevereiro de 2026
**Projeto:** Best of Opera — App-Editor (APP3)
**Stack:** Python/FastAPI + Next.js + PostgreSQL, deploy no Railway (containers efêmeros)
**Storage:** Cloudflare R2 para vídeos e assets persistentes

---

## 1. O que é o sistema

Pipeline de edição de vídeo musical (ópera e música clássica) para os canais de redes sociais do Bolivar (ReelsClassics 6M+ seguidores, Best of Opera). O fluxo de uma edição:

1. Download do vídeo do YouTube (yt-dlp) → salva no R2
2. Validar letra (Gemini ou manual)
3. Transcrição com timestamps (Gemini audio)
4. Validação de alinhamento (fuzzy match + revisão humana)
5. Aplicar corte (janela de overlay, FFmpeg)
6. Traduzir letra para 7 idiomas (Google Cloud Translation API)
7. Render preview (FFmpeg + legendas ASS, idioma PT)
8. Aprovação humana → Render final (FFmpeg × 7 idiomas)
9. Upload pro R2 + download local

Volume: 1-3 edições/dia. Concorrência = 1 (um vídeo por vez).

O sistema faz parte de um monorepo com outros apps: app-curadoria, app-redator, app-editor.

---

## 2. Problema original

As etapas 6, 7, 8 usavam `BackgroundTasks` do FastAPI (fire-and-forget). Quando o Gemini ou FFmpeg travavam, ou o container Railway reiniciava durante uma task, o status ficava preso no banco para sempre (ex: "traducao") sem processo ativo. O usuário não tinha como retentar sem intervenção manual no banco.

---

## 3. Decisões arquiteturais tomadas

- **Sem Celery/Redis** — complexidade não justificada para o volume
- **Worker único com asyncio.Queue** — consome uma task por vez, evita OOM Kill
- **Sessões curtas de banco** — nunca manter SessionLocal aberta durante I/O externo (Gemini, FFmpeg, APIs)
- **Heartbeat + progresso granular** — campo `task_heartbeat` (DateTime) e `progresso_detalhe` (JSON) na tabela Edicao
- **Idempotência** — toda task verifica o que já foi processado antes de fazer trabalho novo
- **Recovery no startup** — `requeue_stale_tasks` reenfileira TODAS as edições com status ativo no startup (sem checar heartbeat, porque no startup nada está rodando)
- **Google Cloud Translation API** em vez de Gemini para tradução (mesma API que o app-redator usa, responde em ~200ms vs ~30s do Gemini)
- **Preview em PT** — o preview renderiza em português (idioma da audiência principal), não no idioma da música
- **Download local** em vez de player embarcado para preview — usuário baixa e assiste no QuickTime/VLC

---

## 4. O que foi implementado (6 blocos)

### Bloco 1 — Modelo e migração
- Adicionados campos `task_heartbeat` (DateTime, nullable) e `progresso_detalhe` (JSON, default={}) à tabela `editor_edicoes`
- Migration via `_run_migrations()` no startup (ALTER TABLE manual, não Alembic)

### Bloco 2 — Worker e lifespan
- **app/worker.py** criado com:
  - `task_queue` — asyncio.Queue global
  - `worker_loop()` — consome tasks sequencialmente, nunca morre (except Exception ao redor do while True)
  - `requeue_stale_tasks()` — reenfileira TODAS as edições com status ativo no startup, sem checar heartbeat
  - `is_worker_busy()` — consulta banco para verificar se há edição em processamento
- **app/main.py** modificado: worker inicia no lifespan, requeue no startup, cancel no shutdown

### Bloco 3 — Task de tradução refatorada
- `_traducao_task` com padrão de sessões curtas (Passo A: ler estado, Passo B: loop sem sessão, Passo C: finalização)
- Heartbeat antes de cada idioma
- Idempotência: verifica idiomas já traduzidos
- `asyncio.wait_for` com timeout=180 em cada chamada
- Try/except BaseException (para capturar CancelledError no shutdown)
- Imports DENTRO do try-except (bug crítico que causava travamento silencioso)
- Endpoint `POST /edicoes/{id}/traducao-lyrics` com check-and-set atômico (HTTP 409 se status não permite)
- `_STATUS_PERMITIDOS_TRADUCAO = {"traducao", "montagem", "erro"}`

### Bloco 4 — Task de render refatorada
- Mesmo padrão de sessões curtas da tradução
- FFmpeg com `asyncio.wait_for(processo.communicate(), timeout=600)` + `processo.kill()` em timeout
- Idempotência: verifica renders já concluídos
- `renders_ok > 0` para setar status "concluido" ou "preview_pronto"; se zero → "erro"
- Limpeza de arquivo local após upload pro R2
- Endpoints com check-and-set atômico:
  - `POST /renderizar` — `_STATUS_PERMITIDOS_RENDER = {"montagem", "preview_pronto", "erro"}`
  - `POST /renderizar-preview` — `_STATUS_PERMITIDOS_PREVIEW = {"montagem", "revisao", "erro"}`
  - `POST /aprovar-preview` — transição atômica de "preview_pronto" → "renderizando"

### Bloco 5 — Endpoints auxiliares
- `GET /fila/status` — retorna se worker está ocupado, edicao_id, etapa, progresso
- `POST /edicoes/{id}/desbloquear` — recovery manual que infere status correto baseado no que já existe no banco (renders → "preview_pronto", traduções → "montagem", senão → "alinhamento")
- `POST /admin/reset-total` — endpoint temporário que zera todos os dados do editor (REMOVER APÓS TESTES)

### Bloco 6 — Frontend
- `useAdaptivePolling` substituiu `usePollingWithTimeout` — começa em 3s, desacelera para 15s após 2min, sem timeout
- Progresso granular com `progresso_detalhe` do backend
- Banner de "sistema ocupado" quando outro vídeo está processando
- Tela de conclusão mostra lista de 7 idiomas com bandeiras e status (Pendente/Baixar)

---

## 5. Bugs encontrados e corrigidos durante implementação

### Bug: Import fora do try-except (CRÍTICO)
- `_traducao_task` tinha imports nas linhas 652-653 FORA do try-except
- Se o import falhasse, a exceção escapava para o worker_loop que só logava sem atualizar o banco
- Status ficava preso em "traducao" para sempre
- **Fix:** imports movidos para dentro do try-except

### Bug: Worker não setava status="erro" em falha não tratada
- O worker_loop capturava exceções mas não atualizava o banco
- **Fix:** worker agora tenta setar status="erro" no banco quando task falha

### Bug: CancelledError não capturado
- `except Exception` não captura `CancelledError` (é BaseException)
- Quando container reiniciava durante task, status ficava preso
- **Fix:** trocado para `except BaseException`, com tratamento específico para CancelledError

### Bug: requeue_stale_tasks checava heartbeat no startup
- No startup nada está rodando, heartbeat fresco é mentira
- **Fix:** reenfileira TODAS as edições com status ativo, sem checar heartbeat

### Bug: progresso_detalhe e task_heartbeat não expostos na API
- EdicaoOut (schemas.py) não incluía os campos novos
- Diagnóstico era cego pela API
- **Fix:** campos adicionados ao schema

### Bug: Idioma hardcoded como "it"
- `_detect_music_lang` em importar.py tinha fallback "it" que falhava para músicas não-italianas
- **Fix:** tenta campos explícitos do projeto do Redator, fallback retorna None e frontend pede ao usuário via modal

### Bug: Preview renderizava no idioma da música
- Preview usava `edicao.idioma` fazendo `idioma_versao == idioma_musica`, então `precisa_traducao = False`
- **Fix:** preview renderiza em "pt" (idioma da audiência principal)

### Bug: Legenda fantasma no segundo 0
- `recortar_lyrics_na_janela` incluía segmentos que começavam antes da janela, clipando para start=0 com texto completo
- **Fix:** exclui segmentos cujo início é anterior à janela

### Bug: Timeout de tradução muito curto
- timeout=30 causava falsos timeouts em óperas longas
- **Fix:** aumentado para timeout=180

---

## 6. Estado atual do sistema

### Funcionando:
- Worker sequencial com recovery no startup
- Tradução via Google Cloud Translation API (rápida, ~5s total)
- Preview em PT com download local
- Detecção de idioma com fallback interativo (modal no frontend)
- Heartbeat + progresso granular
- Endpoint de desbloqueio manual
- Banner de sistema ocupado
- Check-and-set atômico em todos os endpoints (anti double-click)

### Em andamento / pendente:
- **Render final dos 7 idiomas** — botão "Aprovar e Renderizar Todos" precisa de ajustes no frontend
- **Upload pro R2 após render** — confirmar que cada vídeo renderizado é salvo no R2 na estrutura `{artista} - {musica}/{idioma}/video_{idioma}.mp4`
- **Vídeo PT do preview precisa ir pro R2** — hoje pode estar só no disco efêmero
- **Download individual por idioma** — botões "Baixar" com link direto pro R2
- **Download de todos** — botão "Baixar Todos" (sequencial ou zip)
- **Remover player embarcado** — substituir por "Baixar Preview"
- **Remover endpoint temporário** `/admin/reset-total` após testes
- **Problema 2 (posição das legendas)** — não foi testado após correção do problema 1, pode ter se resolvido junto

---

## 7. Estrutura de arquivos relevantes

### Backend (app-editor/backend/app/)
- `main.py` — lifespan com worker + requeue
- `worker.py` — task_queue, worker_loop, requeue_stale_tasks, is_worker_busy
- `routes/pipeline.py` — _traducao_task, _render_task, todos os endpoints de pipeline
- `routes/importar.py` — importação do Redator, _detect_music_lang
- `routes/edicoes.py` — CRUD de edições
- `models/edicao.py` — modelo Edicao com task_heartbeat e progresso_detalhe
- `models/traducao_letra.py` — TraducaoLetra (idioma + segmentos JSON)
- `models/render.py` — Render (idioma + status + arquivo)
- `services/translate_service.py` — Google Cloud Translation API (traduzir_letra_cloud)
- `services/regua.py` — recortar_lyrics_na_janela, alinhamento
- `services/legendas.py` — geração de legendas ASS para FFmpeg
- `schemas.py` — EdicaoOut com task_heartbeat e progresso_detalhe

### Frontend (app-editor/frontend/)
- `lib/hooks/use-polling.ts` — useAdaptivePolling (3s → 15s)
- `lib/api/editor.ts` — editorApi com filaStatus(), tipos ProgressoDetalhe e FilaStatus
- `components/editor/conclusion.tsx` — tela de conclusão com progresso, banner, botões

### App-Redator (referência)
- `services/claude_service.py` — gera overlays/posts via Claude Sonnet 4.5
- `services/translate_service.py` — tradução via Google Cloud Translation REST API (requests.post síncrono)

---

## 8. Ferramentas e workflow

- **Claude Code** no terminal do VS Code para implementação bloco a bloco
- **Plano de implementação** em `PLANO-IMPLEMENTACAO-WORKER.md` na raiz do repo
- **Deploy automático** via git push pro Railway
- **Fluxo de trabalho:** ler plano → pedir bloco específico → revisar aqui → aprovar → push → testar
- **Importante:** Claude Code não tem memória entre sessões — sempre pedir para ler o plano e os arquivos relevantes antes de trabalhar

---

## 9. Próximo prompt sugerido para nova conversa

```
Leia PLANO-IMPLEMENTACAO-WORKER.md e o memorial MEMORIAL-REVISAO-EDITOR.md
na raiz do repo.

Contexto: acabamos de refatorar o app-editor com worker sequencial, sessões
curtas de banco, heartbeat, e idempotência. A tradução e o preview estão
funcionando. O próximo passo é finalizar o fluxo de renderização:

1. Garantir que o vídeo PT do preview é salvo no R2
2. Botão "Aprovar e Renderizar Todos" dispara render dos 6 idiomas faltantes
3. Cada vídeo renderizado vai pro R2 e arquivo local é limpo
4. Frontend mostra progresso por idioma e botão "Baixar" conforme cada um conclui
5. Remover player de vídeo embarcado — substituir por "Baixar Preview"
6. Botão "Baixar Todos" quando os 7 estiverem prontos

Leia pipeline.py e conclusion.tsx antes de começar.
```
