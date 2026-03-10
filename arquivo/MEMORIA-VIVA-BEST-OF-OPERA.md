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
