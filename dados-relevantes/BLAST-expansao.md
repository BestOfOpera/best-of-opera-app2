# BLAST v3 — Expansão do Pipeline: Variáveis e Status

**Data:** 09/03/2026
**Escopo:** Correções críticas do pipeline + novas integrações (cobalt, Sentry)

---

## Variáveis de Ambiente

| Variável | App | Obrigatória | Default | Descrição |
|---|---|---|---|---|
| `DATABASE_URL` | todos | sim | postgresql://... | Conexão PostgreSQL |
| `GEMINI_API_KEY` | editor | sim | "" | Transcrição e busca de letra |
| `GOOGLE_TRANSLATE_API_KEY` | editor | sim | "" | Tradução de letras (7 idiomas) |
| `ANTHROPIC_API_KEY` | redator | sim | "" | Geração de conteúdo (Claude) |
| `YOUTUBE_API_KEY` | curadoria | sim | "" | Busca YouTube |
| `R2_ACCOUNT_ID` | editor | sim | — | Cloudflare R2 |
| `R2_ACCESS_KEY_ID` | editor | sim | — | Cloudflare R2 |
| `R2_SECRET_ACCESS_KEY` | editor | sim | — | Cloudflare R2 |
| `R2_BUCKET_NAME` | editor | sim | — | Cloudflare R2 |
| `STORAGE_PATH` | editor | não | /tmp/editor_storage | Cache local de arquivos |
| `REDATOR_API_URL` | editor | não | prod URL | URL do app-redator |
| `CURADORIA_API_URL` | editor | não | prod URL | URL do app-curadoria |
| `COBALT_API_URL` | editor | não | api.cobalt.tools | Download via cobalt.tools |
| `GENIUS_API_TOKEN` | editor | não | "" | Busca de letras Genius |
| `SECRET_KEY` | editor | sim prod | dev-secret | Chave JWT/sessão |
| `CORS_ORIGINS` | editor | não | ["*"] | Origens permitidas CORS |
| `MAX_VIDEO_SIZE_MB` | editor | não | 500 | Limite de upload |
| `EXPORT_PATH` | editor | não | "" | Pasta iCloud/export local |
| `SENTRY_DSN` | editor | não | None | DSN do Sentry (desativado se vazio) |

## Correções Implementadas (BLAST v3)

| ID | Descrição | Status |
|---|---|---|
| ERR-056 | cobalt.tools como download primário (antes da curadoria) | ✅ |
| ERR-057 | Pacote ZIP migrado de BackgroundTasks para worker sequencial | ✅ |
| ERR-013 | Preview salvo no R2 (já estava correto — documentado) | ✅ |
| ERR-059 | Retry automático de tradução (2ª passada nos idiomas que falharam) | ✅ |
| ERR-060 | Sentry integrado (free tier, opcional via SENTRY_DSN) | ✅ |
| ERR-061 | UNIQUE constraints em traducao_letra e render | ✅ |
| ERR-062 | Namespaces no progresso_detalhe (traducao/render/pacote) | ✅ |

## Cascata de Download (após BLAST v3)

```
1. Arquivo local (EXPORT_PATH) — mais rápido
2. R2 existente — upload prévio da curadoria
3. cobalt.tools — download direto, alta qualidade
4. Curadoria API — prepare-video endpoint
5. yt-dlp — último fallback
6. ERRO — vídeo não disponível
```
