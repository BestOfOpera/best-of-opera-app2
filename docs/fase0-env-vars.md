# Fase 0 BO V2 — Variáveis de Ambiente (Railway)

A Fase 0 introduz duas variáveis de ambiente no serviço `app-redator`. Devem ser declaradas manualmente no dashboard da Railway **antes do próximo deploy** da branch `f0/bo-v2-fundacoes`. Sem elas, o backend sobe com defaults seguros (v1 para todos os projetos), mas o operador perde controle explícito do estado.

## Onde setar

Railway → Project → Service `app-redator` → Settings → Variables → Add Variable.

## Variáveis

| Variável | Valor | Propósito |
|---|---|---|
| `PIPELINE_V2_ENABLED` | `false` | Feature flag global que controla se novos projetos BO (`brand_slug='best-of-opera'`) nascem com `pipeline_version='v2'`. RC e demais brands sempre v1, independente da flag. |
| `USE_ANTHROPIC_WEB_SEARCH` | `true` | Seleciona Ramo A — tool nativa `web_search_20250305` da Anthropic. Confirmada funcional em 2026-04-23 via `scripts/verify_web_search.py` (server_tool_use: web_search_requests=1). |

## ⚠️ Não alterar `PIPELINE_V2_ENABLED=true` até a Fase 5.3

A flag fica `false` até a ativação controlada pós-auditoria do pipeline completo. Fazer antes quebra o princípio de coexistência v1/v2: serviços V2 (prompts, rotas, lookup do perfil `best-of-opera-v2`) ainda não existem nas Fases 0–4. Flipar a flag prematuramente cria projetos `v2` órfãos que nenhum serviço sabe processar.

## Posteridade — se `web_search_20250305` parar de funcionar

Se um dia a tool for descontinuada ou deixar de funcionar neste tier:

1. Rodar `python scripts/verify_web_search.py` novamente para reconfirmar o status.
2. Se falhar, solicitar implementação do fallback Google CSE (Ramo B). Requer:
   - `GOOGLE_CSE_API_KEY` — obter em Google Cloud Console → API Keys (habilitar Custom Search API)
   - `GOOGLE_CSE_CX` — obter em Google Programmable Search Engine → criar engine → Search Engine ID
3. Setar `USE_ANTHROPIC_WEB_SEARCH=false` na Railway + adicionar as 2 credenciais acima.
4. O código de fallback (`app-redator/backend/services/bo/web_search_fallback.py`) é criado sob demanda em commit adicional, conforme §3 Passo 0.6 do `BO_PLANO_V2.md`.
