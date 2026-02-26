# CLAUDE.md — Best of Opera App2

> Guia de referência rápida para o Claude Code. Leia este arquivo antes de qualquer tarefa.

---

## Modo de Operação

- **Autonomia total.** Não pedir confirmação para ações de código funcional.
- **Deploy obrigatório.** Após qualquer alteração de código, SEMPRE fazer commit e push:
  ```bash
  git add <arquivos alterados>
  git commit -m "mensagem descritiva em português"
  git push origin main
  ```
  O Railway faz redeploy automático a cada push. Nunca deixar alterações sem deploy.
- Se houver erro de build/teste, resolver antes de fazer push.

---


## Visão Geral do Projeto

Monorepo com 4 apps + 1 pasta de scripts + shared, todos deployados no Railway.

```
best-of-opera-app2/
├── app-curadoria/     # Motor de busca YouTube (FastAPI)
├── app-editor/        # Pipeline de edição de vídeo (FastAPI + React)
├── app-redator/       # Gerador de conteúdo AI (FastAPI + React)
├── app-portal/        # Frontend unificado (Next.js)
├── app-scripts/       # Scripts utilitários
└── shared/            # Código compartilhado entre apps
```

**Fluxo principal:**
```
Portal → Curadoria (busca YouTube) → Redator (gera texto) → Editor (edita vídeo)
```

---

## Stack

| Camada | Tecnologia |
|--------|-----------|
| Backend | Python 3.11, FastAPI, SQLAlchemy, Pydantic |
| Banco | PostgreSQL (Railway prod) / SQLite (local dev) |
| Frontend Portal | Next.js 16, React 19, TypeScript, Tailwind CSS, shadcn/ui |
| Frontend Apps | React 18, Vite, TypeScript, Tailwind CSS |
| IA | Anthropic Claude (redator), Google Gemini 2.5 Pro (editor) |
| Vídeo | FFmpeg, yt-dlp, legendas ASS |
| YouTube | YouTube Data API v3 |
| Storage | Cloudflare R2 (arquivos/vídeos renderizados) |
| Deploy | Railway (Docker + Nixpacks) |
| Ícones | Lucide React |
| Idioma UI | Português PT-BR |

---

## Comandos de Desenvolvimento Local

### Curadoria Backend (porta 8002)
```bash
cd app-curadoria/backend
pip install -r requirements.txt
export YOUTUBE_API_KEY="..."
export DATABASE_URL="sqlite:///./curadoria.db"
uvicorn main:app --host 0.0.0.0 --port 8002 --reload
```

### Redator (porta 8000 + 5173)
```bash
# Backend
cd app-redator
pip install -r requirements.txt
export ANTHROPIC_API_KEY="..."
export DATABASE_URL="sqlite:///./best_of_opera.db"
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# Frontend
cd app-redator/frontend
npm install && npm run dev   # → localhost:5173
```

### Editor (porta 8001 + 5174)
```bash
# Backend
cd app-editor/backend
pip install -r requirements.txt
export GEMINI_API_KEY="..."
export DATABASE_URL="sqlite:///./editor.db"
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

# Frontend
cd app-editor/frontend
npm install && npm run dev   # → localhost:5174
```

### Portal (porta 3000)
```bash
cd app-portal
npm install && npm run dev   # → localhost:3000
# Usa automaticamente localhost:8000/8001/8002 para os backends
```

---

## Infraestrutura Railway (Produção)

| Serviço | Service ID | URL Pública |
|---------|-----------|-------------|
| app (redator) | `fade4ac2-8774-4287-b87d-7f2559898dcc` | https://app-production-870c.up.railway.app |
| editor-backend | `7e42a778-aa1e-4648-9ce1-07f5d6896fd5` | https://editor-backend-production.up.railway.app |
| editor-frontend | `35ec9116-a3ee-4f9a-ad90-feeec2383238` | https://editor-frontend-production.up.railway.app |
| portal (Next.js) | `73b20b58-eac5-44e8-a4f6-b9af94e74932` | https://portal-production-4304.up.railway.app |
| curadoria (portal antigo) | `b8fe934d-e3d7-4d30-a68a-4914e03cdb0a` | https://curadoria-production-cf4a.up.railway.app |
| curadoria-backend | `e3eb935a-7b11-44fd-889f-fbd45edb0602` | https://curadoria-backend-production.up.railway.app |
| Postgres | `1f423154-d150-46a3-a459-b62b55fe1004` | `postgres.railway.internal:5432` |

**IDs do projeto:**
- Project ID: `c4d0468d-f3da-4765-b582-42cf6ef5ff66`
- Environment ID: `4ec5a08f-d29e-4d7b-a54d-a3e161edd716`

**Token Railway (conta):** salvo em `~/.zshrc` como `$RAILWAY_TOKEN`
> ✅ É um **account token** — funciona para queries E mutations. Use sempre este token.
> Mutation correta para redeploy: `serviceInstanceDeploy` (NÃO `serviceInstanceRedeploy`).

### Deploy Manual via GraphQL API
> ⚠️ O Railway CLI NÃO funciona com tokens UUID. Use sempre a API GraphQL.
> ✅ Mutation de redeploy: `serviceInstanceDeploy` (não `serviceInstanceRedeploy`)

```bash
# Redeploy de um serviço
curl -s -X POST "https://backboard.railway.com/graphql/v2" \
  -H "Authorization: Bearer $RAILWAY_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"mutation { serviceInstanceRedeploy(serviceId: \"<SERVICE_ID>\", environmentId: \"4ec5a08f-d29e-4d7b-a54d-a3e161edd716\") }"}'

# Verificar status de todos os serviços
curl -s -X POST "https://backboard.railway.com/graphql/v2" \
  -H "Authorization: Bearer $RAILWAY_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"query { project(id: \"c4d0468d-f3da-4765-b582-42cf6ef5ff66\") { services { edges { node { name serviceInstances { edges { node { latestDeployment { status } } } } } } } } }"}'
```

---

## Banco de Dados

```
Host:     postgres.railway.internal (prod) | localhost (dev)
Port:     5432
User:     postgres
Password: bestofopera2024
Database: railway
```

- Tabelas criadas automaticamente no startup via `Base.metadata.create_all`
- Os 3 backends compartilham o **mesmo** banco PostgreSQL
- Dev local: cada app usa SQLite separado por padrão

---

## API Keys Necessárias

| Variável | Serviço | Onde obter |
|----------|---------|-----------|
| `ANTHROPIC_API_KEY` | app-redator | https://console.anthropic.com |
| `GEMINI_API_KEY` | app-editor | https://aistudio.google.com |
| `YOUTUBE_API_KEY` | app-curadoria | https://console.cloud.google.com |
| `GOOGLE_TRANSLATE_API_KEY` | app-redator | https://console.cloud.google.com |
| `RAILWAY_TOKEN` | Deploy | https://railway.app/account/tokens |
| `R2_*` | Storage | https://dash.cloudflare.com (Cloudflare R2) |

---

## Detalhes por App

### app-curadoria
**Função:** Busca e curadoria de vídeos de ópera no YouTube.

Arquivos-chave:
- `main.py` — Endpoints, scoring, download
- `database.py` — Conexão PostgreSQL + cache de quota
- `dataset_v3_categorizado.csv` — 105+ vídeos já postados (filtro de duplicatas)

Endpoints principais:
```
GET /api/health           → status + quota YouTube
GET /api/categories       → 6 categorias V7
GET /api/category/{key}   → busca por categoria (consome quota)
GET /api/search?q=        → busca livre
GET /api/ranking          → ranking cross-categoria
GET /api/quota/status     → cota restante
GET /api/download/{id}    → download streaming
```

Categorias V7: `icones`, `estrelas`, `hits`, `surpreendente`, `talent`, `corais`

Motor de scoring: `elite_hits +15`, `power_names +15`, `specialty +25`, `voice +15`
Anti-spam: remove karaoke, piano, tutorial, lesson, reaction, review

### app-redator
**Função:** Gera conteúdo textual para redes sociais via Claude AI.

Arquivos-chave:
- `backend/main.py` — FastAPI, serve frontend buildado como static
- `backend/services/claude_service.py` — Chamadas ao Anthropic
- `backend/prompts/` — Prompts para overlay, post, youtube, hook
- `backend/services/export_service.py` — Export ZIP

Pipeline:
1. Criar projeto (URL YouTube + metadata)
2. IA gera overlay → post → título+tags YouTube
3. Usuário aprova/edita cada etapa
4. Traduzir para 7 idiomas (en, pt, es, de, fr, it, pl)
5. Exportar ZIP

Build: **Nixpacks** (configurado em `railway.json` e `nixpacks.toml`)

### app-editor
**Função:** Pipeline de edição de vídeo com legendas sincronizadas.

Arquivos-chave:
- `backend/app/main.py`
- `backend/app/services/legendas.py` — Geração de legendas ASS
- `backend/app/services/` — FFmpeg, Gemini, download, transcrição

Pipeline de 9 etapas:
1. Download (yt-dlp)
2. Validar letra (Gemini ou manual)
3. Transcrição com timestamps (Gemini audio + letra)
4. Validação de alinhamento (fuzzy match, color-coded)
5. Aplicar corte (overlay window)
6. Traduzir letras (7 idiomas)
7. Render preview
8. Render final (FFmpeg + ASS)
9. Empacotar → R2

Build: **Dockerfile** (backend + frontend separados)

### app-portal
**Função:** Frontend unificado Next.js integrando os 3 apps.

Arquivos-chave:
- `lib/api/base.ts` — URL detection runtime (prod vs local)
- `lib/api/curadoria.ts`, `redator.ts`, `editor.ts` — Camadas de API
- `app/(app)/` — Pages por app

Detecção de ambiente (importante — NÃO usar rewrites Next.js):
```typescript
// base.ts — detecção runtime no browser
function isProduction() {
  return typeof window !== "undefined" &&
    window.location.hostname.includes("railway.app")
}
```
> ⚠️ Next.js standalone NÃO suporta rewrites para URLs externas. Sempre usar detecção de hostname.

---

## Railway — Regras de Acesso (OBRIGATÓRIO)

### ⛔ NUNCA usar Railway CLI
- NUNCA executar `railway run`, `railway up`, `railway login`, `railway variables`, `railway logs` ou qualquer subcomando do CLI
- O CLI tem bug com account tokens UUID — não funciona e desperdiça tempo

### ✅ Como fazer cada operação
| Operação | Como fazer |
|----------|-----------|
| **Deploy** | `git push origin main` → deploy automático |
| **Ver variáveis** | `./scripts/railway-env.sh list` |
| **Setar variável** | `./scripts/railway-env.sh set NOME valor` |
| **Ver logs** | Dashboard web ou log drain |
| **Forçar redeploy** | `./scripts/railway-env.sh redeploy` |

### Configuração
- IDs dos serviços estão em `.env.railway` na raiz (gitignored)
- Se `.env.railway` não existir, AVISAR o operador — não tentar criar

---

## Armadilhas Conhecidas (LEIA ANTES DE EDITAR)

1. **Railway CLI inutilizável** — Account Tokens são UUID, CLI não aceita. Use sempre a GraphQL API.

2. **Next.js Standalone + Rewrites** — Não funciona. O portal detecta ambiente via `window.location.hostname` em `base.ts`.

3. **CORS** — Editor-backend tem lista explícita em `CORS_ORIGINS`. Ao adicionar domínio, atualizar a variável. Redator e Curadoria usam `allow_origins=["*"]`.

4. **Storage R2** — Railway tem storage efêmero (arquivos perdidos no redeploy). Vídeos renderizados vão para Cloudflare R2.

5. **Quota YouTube** — Limite ~10.000 unidades/dia. Cada search = 100 unidades. Monitorar em `/api/quota/status`.

6. **Banco compartilhado** — 3 backends no mesmo PostgreSQL. Sem conflito de nomes hoje, mas atenção ao criar tabelas novas.

7. **Gemini Transcrição** — O prompt DEVE conter `"NÃO omita versos"` para evitar gaps nos timestamps.

8. **SQLite local** — O Redator usa `best_of_opera.db` relativo ao CWD. Rodar `uvicorn` do diretório correto (`app-redator/`, não `app-redator/backend/`).

9. **Build Redator** — Usa Nixpacks, não Dockerfile. O frontend React é buildado e servido como static pelo FastAPI.

---

## Arquitetura Multi-Projeto (Design Principle Fundamental)

> ⚠️ **Leia antes de criar qualquer prompt, configuração ou componente novo.**

Todo o código deste projeto deve ser desenvolvido como **plataforma reutilizável**, não como solução exclusiva para Best of Opera. A mesma estrutura, lógica e automação serão reusadas para outros canais — o primeiro candidato é o **Reels Classics** — com apenas customização de configuração, sem duplicação de código.

### Projetos planejados na plataforma

| Projeto | Canal | Nicho | Status |
|---------|-------|-------|--------|
| `best-of-opera` | Best of Opera | Ópera clássica | ✅ Produção |
| `reels-classics` | ReelsClassics (6M+ seguidores) | Música clássica ampla | 🔜 Próximo |
| _(futuros)_ | Outros canais | A definir | — |

### O que muda entre projetos (config)

Cada projeto novo é definido por um arquivo de configuração/perfil que sobrescreve os defaults:

```
shared/
└── profiles/
    ├── best-of-opera.json      # Prompts, categorias, idiomas, branding
    └── reels-classics.json     # Idem, personalizado para clássicos
```

Itens configuráveis por projeto:
- **Prompts** — overlay, post, hook, título YouTube, legenda (tom, estilo, vocabulário)
- **Categorias de curadoria** — seeds de busca, filtros anti-spam, pesos de scoring
- **Idiomas ativos** — subconjunto dos 7 idiomas suportados
- **Branding** — nome do canal, handles, hashtags padrão
- **Dataset de referência** — CSV de vídeos já postados (filtro de duplicatas por projeto)
- **Regras de legenda** — estilo ASS, fonte, posição, cores

### O que NÃO muda (core da plataforma)

- Engine de busca e scoring do YouTube
- Pipeline de edição (download → transcrição → alinhamento → render)
- Pipeline do redator (overlay → post → SEO → tradução → export)
- Infraestrutura Railway + R2
- Toda a camada de banco de dados e API

### Regras de implementação

1. **Nunca hardcode nome de projeto, canal ou prompt** em lógica de negócio. Sempre referenciar via perfil/config.
2. **Prompts vivem em arquivos separados** por projeto em `shared/profiles/` ou `app-*/prompts/{project}/`. Nunca inline no código.
3. **Componentes React** devem aceitar props de configuração (labels, textos, categorias) em vez de ter cópia por projeto.
4. **Ao criar nova feature**, perguntar: *"como isso funcionaria para Reels Classics com configuração diferente?"* — se não funcionar genericamente, refatorar antes de commitar.
5. **Variáveis de ambiente** devem incluir `PROJECT_ID` (ex: `best-of-opera`, `reels-classics`) para que backends possam carregar o perfil correto.

### Exemplo de uso do perfil no backend

```python
# app-curadoria/backend/main.py
PROJECT_ID = os.getenv("PROJECT_ID", "best-of-opera")
profile = load_profile(PROJECT_ID)  # carrega shared/profiles/{PROJECT_ID}.json

categories = profile["categories"]
anti_spam_terms = profile["anti_spam"]
scoring_weights = profile["scoring"]
```

```python
# app-redator/backend/services/claude_service.py
prompt_template = load_prompt(PROJECT_ID, prompt_type="overlay")
# Carrega shared/profiles/best-of-opera/prompts/overlay.txt
```

---

## Padrões de Código do Projeto

- **Python:** FastAPI com routers separados por domínio, SQLAlchemy ORM, Pydantic para schemas
- **TypeScript:** Strict mode, interfaces explícitas, sem `any`
- **CSS:** Tailwind CSS utilitário, sem CSS modules
- **Componentes:** shadcn/ui no portal, componentes customizados nos apps
- **Idioma:** Código em inglês, UI/comentários em português PT-BR
- **Logs:** `print()` aceitável para dev, estruturar com `logging` em produção

---

## Próximos Passos (Backlog Técnico)

- [ ] Domínio customizado (`app.bestofopera.com`)
- [ ] Schemas PostgreSQL separados por app
- [ ] CI/CD via GitHub Actions (testes antes do deploy)
- [ ] Autenticação no portal (atualmente aberto)
- [ ] Monitoramento/alertas (uptime, erros, quota)
- [ ] Dockerfiles para Redator (hoje usa Nixpacks)
- [ ] Projetos Railway legados para desativar: `blissful-education`, `skillful-respect`, `believable-communication`
- [ ] Estrutura `shared/profiles/` com `best-of-opera.json` como perfil de referência
- [ ] Migrar todos os prompts hardcoded para `shared/profiles/best-of-opera/prompts/`
- [ ] Criar `PROJECT_ID` como variável de ambiente em todos os backends
- [ ] Implementar `load_profile()` e `load_prompt()` como utilitários no `shared/`
- [ ] Validar arquitetura multi-projeto criando perfil `reels-classics.json` em paralelo
