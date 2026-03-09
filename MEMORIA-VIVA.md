# Memória Viva — Best of Opera App2

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
