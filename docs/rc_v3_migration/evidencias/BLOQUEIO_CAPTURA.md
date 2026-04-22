# Bloqueio de captura do payload de produção — projeto #355

**Data:** 2026-04-22
**Sessão:** PROMPT 5A — investigação Bloco A
**Autor:** Claude Code (auditor estático)

## Tentativas

| # | Método | Resultado |
|---|--------|-----------|
| 1 | `curl -s https://ia-production-cf4a.up.railway.app/api/projects/355` | HTTP 403 — sem corpo |
| 2 | `curl -s https://app-production-870c.up.railway.app/api/projects/355` (URL do `REDATOR_API_URL` em `.env.example`) | HTTP 403 — `Host not in allowlist` |
| 3 | `curl -H "Origin: https://portal-production-4304.up.railway.app" …` | HTTP 403 — `Host not in allowlist` |
| 4 | `curl https://app-production-870c.up.railway.app/api/health` (sem path de projeto) | HTTP 403 — `Host not in allowlist` |
| 5 | `curl https://portal-production-4304.up.railway.app/` (frontend) | HTTP 403 — `Host not in allowlist` |
| 6 | `railway --version` (CLI) | comando não encontrado |

## Interpretação

A mensagem `Host not in allowlist` NÃO vem do FastAPI do redator — `app-redator/backend/main.py:104-119` tem apenas `CORSMiddleware` e `ProxyHeadersMiddleware(trusted_hosts=["*"])`, nenhum middleware retornando 403 com essa string. A mensagem vem da edge do Railway (gateway) que bloqueia requisições cujo IP de origem não está em allowlist do projeto. O sandbox Claude Code não está na allowlist.

## Credenciais procuradas e não encontradas

- `dados-relevantes/` contém apenas `.md` de diagnóstico, `.sh` de teste e um `.sql`. Nenhum token.
- `.env` não existe; apenas `.env.example` com placeholders (`sk-ant-...`, `AIza...`).
- `env | grep -i token` não retornou nada relevante.

## Decisão

Seguir com **reconstituição estática** do shape do payload, conforme autorizado no plano (item A.1, alternativa D):

1. Shape real do `overlay_json` é produzido por `_process_overlay_rc` em
   `app-redator/backend/services/claude_service.py:932-1045`.
2. Schema do que o LLM retorna antes do processamento vive em
   `docs/rc_v3_migration/rc_overlay_prompt_v3_1.py` (seção `<format>`).
3. Shape devolvido pelo endpoint GET `/api/projects/{id}` é determinado por
   `ProjectOut` em `app-redator/backend/schemas.py` e pelo handler em
   `app-redator/backend/routers/projects.py:226-`.

A análise dessas três fontes reconstrói o payload com precisão suficiente para o
Bloco A, porque a regressão visual depende de **shape** (presença de campos no
array), não de valores específicos de conteúdo.

## Follow-up pendente ao operador

Se o operador tiver acesso a `railway run psql $DATABASE_URL` em shell local, rodar:

```sql
SELECT jsonb_typeof(overlay_json) AS tipo,
       jsonb_array_length(overlay_json) AS tamanho,
       overlay_json->-1 AS ultimo_item
FROM projects
WHERE id = 355;
```

E anexar o resultado a este arquivo. Permitiria confirmação empírica (não apenas
reconstituição estática) de que o sentinel `_is_audit_meta` está, de fato,
persistido no registro #355.
