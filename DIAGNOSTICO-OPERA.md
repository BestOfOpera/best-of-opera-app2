# DIAGNÓSTICO ARCHITETURAL: BEST OF OPERA (APP-EDITOR)

Este documento descreve o funcionamento interno, as habilidades de resiliência e as decisões arquiteturais do pipeline de vídeo da plataforma Best of Opera, com foco no `app-editor` e sua comunicação com os outros serviços do monorepo.

O objetivo desta análise é prover contexto de alto nível para agentes autônomos e desenvolvedores futuros. A fonte da verdade técnica é o próprio código (`app/worker.py`, `app/routes/pipeline.py`, `shared/storage_service.py`), este documento atua como mapa.

---

## 1. Visão Geral: Habilidade Anti-Falha (The Resilient Worker)

O app-editor lida com processamento pesado de vídeos (download via yt-dlp, IA via Whisper/Gemini, codificação de vídeo via FFmpeg). Historicamente, rodar tarefas assim diretamente nos nós de uma API usando `BackgroundTasks` do FastAPI causa problemas sérios de "Out of Memory" (OOM) e concorrência (vários requests disparando renders mortais ao mesmo tempo).

**A Solução (O "Worker Sequencial"):**
Substituímos o disparo não acoplado pelo padrão de fila (`asyncio.Queue`) acoplada a um loop de trabalho isolado num processo (`app/worker.py` -> `worker_loop`).

### Como a proteção funciona:
- **`asyncio.Queue` (Serialização):** O worker tira *uma tarefa por vez* da fila, executa-a do início ao fim e pega a próxima. Se 10 usuários pedirem renders juntos, os vídeos não matarão a RAM da máquina; eles esperarão civilizadamente a sua vez.
- **Tabela de `Edicao` e o "Check-and-Set":** No banco de dados MySQL (`models.edicao`), não mudamos um status cegamente. Mudamos validando o estado anterior (`where(status='PENDENTE')`). Isso garante que uma tarefa duplicada não ultrapasse o estado atual e corrompa o arquivo local.
- **Heartbeats (Proteção anti "Tarefa Zumbi"):** O campo `task_heartbeat` (uma coluna `DateTime`) é atualizado periodicamente a cada passo lento que o worker conclui (ou sempre que avança no progresso no campo `progresso_detalhe`). Se um container Crashar no meio do download ou do ffmpeg, a API "morre" ali e o heartbeat congela. 
- **Recuperação Limpa no Startup (`requeue_stale_tasks`):** Como não queremos que um container que acabe de iniciar volte imediatamente a rodar um render problemático (que pode ter causado o crash), o evento `@asynccontextmanager` roda ao ligar do servidor. Ele busca qualquer tarefa deixada "Pendente/Renderizando" com heartbeat antigo e marca o status oficial dela como `ERROR`. Isso destrava o sistema e permite que o usuário decida se retenta ou se descarta o vídeo pelo frontend (`/desbloquear`).

---

## 2. O Gargalo do YouTube e a Integração com o Apify

A captação de vídeos virais e de alta qualidade requer táticas agressivas de rede. O `yt-dlp` sofre constantemente bloqueios 403 HTTP Error (ERR-055).

**O Paradigma Atual (`app-editor` <-> `app-curadoria`):**
O `app-editor` é um cliente "burro" para o download. Ele primeiro pergunta ao `R2` (Cloudflare Storage) se o vídeo cru (baseado no YouTube ID) já está no balde de metadados. Se não estiver, ele delega o problema chamando a API do `app-curadoria` (`/v1/videos/download/force`), que o enfileira no seu próprio `download_worker`. O `app-editor` apenas faz polling esperando o `app-curadoria` terminar o download para então baixar do `R2` para sua pasta `tmp` local no container.

**Preparando Terreno para o Apify (Instagram / TikTok Scraping):**
Se precisarmos trazer Reels do IG ou TikTok, a arquitetura atual é um modelo perfeito para espelhar:
1. **Delegar (Isolamento):** Não devemos engordar o `app-editor` com libs de Scraping ou Headless Chrome. O `app-editor` continua focando na edição.
2. **Nova Conexão:**  Criaremos uma "App-Scraper" (ou estenderemos a infra da curadoria) que escutará webhooks ou atuará fazendo proxy chamando "Actores" do Apify SDK.
3. **O Acordo R2:** O Apify Actor baixa o Reels do TikTok, e através de nosso novo endpoint da infra de scraping, o upload final vai para o mesmo bucket R2 compartilhado (`shared/storage_service.py`).
4. **Acoplamento no Editor:** No `app-editor`, na área do "garantir_video", em vez de procurar por `youtube_id`, criaremos um campo agnóstico `source_id_origin`. Se for `tiktok_`, o app-editor chama a nova API do Scraper e aguarda o vídeo aparecer magicamente no seu R2. Nenhuma confusão com `yt-dlp` quebra o rendering.

---

## 3. O Pipeline Físico e Segurança dos Arquivos

O core business ocorre no arquivo `pipeline.py` e `legendas.py`. Tratar mídia requer jogar os lixos num cesto após cada tarefa.

**O Ciclo Perigoso (`render_task`):**
1. O backend pega as 7 linguagens desejadas para aquele shorts.
2. Loop FOR por linguagem. Retorno antecipado se o status do processo de tradução cair para Erro de IA.
3. Geração de Textos Físicos `.ass`: As funções geram três `SubStation Alpha` separados para o FFmpeg: O *overlay/título*, e se não vier ordem `sem_legendas`, o *lyrics_track* e a correta sincronia *translations_track*.
4. FFmpeg: Transcodificação do vídeo combinada aos três .ass e ao .wav re-compilado do audio.
5. Upload: Manda p/ o Cloudflare R2 com a chave de nome `${id}_pt.mp4`.

**O Limpador no Fim do Túnel (`finally block`):**
Todas as escritas perigosas no SSD acontecem dentro de `/tmp` ou no mapeamento `/app/storage`. Dentro do método de renderização da pipeline, há blocos `finally` explícitos por iteração. Assim que a língua francesa foi upada para o R2, o arquivo `fr.mp4` e todos os arquivos `.ass` relativos daquela iteração que foram colocados em subpastas com prefixos do RequestID **são marcados com `os.remove`**.
*O Risco:* Se a máquina inteira sofrer um desligamento forçado da nuvem pelo próprio host e o evento "limpa" for pulado, eles se tornam lixo morto. Mas na reinicialização o `tmp` natural do servidor limpa, e cada edição usa GUIDs para as sessões do projeto, nunca reescrevendo por cima de arquivos de projetos antigos não terminados.

**O Padrão Fallback R2 / Local:**
A estrutura `StorageService` permite rodar o Best Of Opera app no computador local de um estagiário na Starbucks conectando em `/storage_local` mas atuando perfeitamente igual à nuvem distribuída (quando `R2_ACCESS_KEY` está habilitada no `.env`).

---

## 4. O Cérebro do Front-end: Polling Inteligente ("Conclusion.tsx")

Em um sistema assíncrono, a pior prática UI/UX é fazer o usuário clicar "F5" para saber se o render das 7 linguagens do vídeo já terminou ou pior, usar WebSockets e derrubar conexões NGINX atoa.

A nossa interface de acompanhamento usa **Polling Adaptativo** pelo React Hook customizado ou o `SWR/react-query` da página (`conclusion.tsx`).

**Como Funciona o Fluxo Visual (`Adaptive Polling`)*:**
- Começa em alta frequência (ex: requisição no backend `GET /fila/status` e `/video/{id}/status` a cada 2000ms).
- A API retorna os metadados brutos (Progressão % e o texto da string humana: *“Processando Áudio...”*).
- Se as duas requisições consecutivas retornaram exatamente o mesmo progresso (indicando tarefa bloqueada momentaneamente em processamento de nuvem FFmpeg em vez de texto leve via Geminni rápido). **O UI relaxa**: Diminui devagarinho de 2 segundos para 4s, depois para 8s, o que economiza picos na infraestrutura sem fazer o FrontEnd dormir com informações legadas desprotais.
- Isso traz o poder de exibir a fila total: o status consegue ler no `worker_loop` do Python quantos passos estão sobrando. Se estiver em >1 , o Front-end apresenta gentilmente ("Sistema Ocupado") informando que a renderização do pipeline demorará um pouco mais. O erro também é propagado imediatamente (Pula Status Vermelho Erro) informando o programador que deve acessar e "desbloquear/limpar logs" direto pelo clique que faz o restart limpo pelo frontend sem ter que invadir o Mongo/MySQL.
