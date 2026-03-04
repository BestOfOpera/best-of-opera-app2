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
