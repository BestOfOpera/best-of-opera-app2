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
