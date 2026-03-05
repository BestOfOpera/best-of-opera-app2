# Memória Viva — Best of Opera App2

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
