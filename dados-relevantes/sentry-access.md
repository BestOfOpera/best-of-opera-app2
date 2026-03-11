# Sentry — Credenciais de Acesso

## Organização
- **Org slug**: `arias-conteudo-k2`
- **Project slug**: `python-fastapi`
- **SENTRY_ORG_URL**: `https://arias-conteudo-k2.sentry.io/issues/`
- **DSN**: `https://371687e1fed2e6a70e7fb84e679ac171@o4511017083928576.ingest.us.sentry.io/4511017096577024`

## Personal Token (API)
- **Token**: `<ver ~/.claude/settings.json → mcpServers.sentry.env.SENTRY_AUTH_TOKEN>`
- **Scopes**: `alerts:read`, `alerts:write`, `event:read`, `event:write`, `org:read`, `project:read`
- **Criado**: 2026-03-11

## Uso via API REST
```bash
# Listar issues abertas (substituir <TOKEN> pelo valor em ~/.claude/settings.json)
curl -H "Authorization: Bearer <TOKEN>" \
  "https://sentry.io/api/0/projects/arias-conteudo-k2/python-fastapi/issues/?query=is:unresolved&limit=10"
```

## Variáveis Railway por serviço
| Serviço | Variável | Valor |
|---------|---------|-------|
| editor-backend | `SENTRY_DSN` | DSN acima |
| editor-backend | `SENTRY_ORG_URL` | URL acima |
| curadoria-backend | `SENTRY_DSN` | DSN acima |
| app (redator) | `SENTRY_DSN` | DSN acima |
| curadoria (portal) | `NEXT_PUBLIC_SENTRY_DSN` | DSN acima |
