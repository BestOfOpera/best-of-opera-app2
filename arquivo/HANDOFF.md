# Best of Opera — Documento de Handoff Tecnico

**Repositorio:** https://github.com/BestOfOpera/best-of-opera-app2.git
**Data:** 2026-02-15

---

## 1. Visao Geral da Arquitetura

O projeto e um **monorepo** com 3 apps independentes + 1 portal unificado, todos deployados no Railway.

```
best-of-opera-app2/
├── app-redator/          # Gerador de conteudo (overlays, posts, SEO)
│   ├── backend/          # FastAPI (Python) — porta 8000
│   └── frontend/         # React + Vite — porta 5173 (local)
├── app-editor/           # Pipeline de edicao de video
│   ├── backend/          # FastAPI (Python) — porta 8001
│   └── frontend/         # React + Vite — porta 5174 (local)
├── app-curadoria/        # Motor de busca YouTube
│   └── backend/          # FastAPI (Python) — porta 8002 (local)
├── app-portal/           # Frontend unificado (Next.js)
│   ├── app/              # Pages (App Router)
│   ├── components/       # UI components (shadcn/ui)
│   └── lib/api/          # Camada de API (client-side)
└── README.md
```

### Fluxo de trabalho do usuario

```
Portal (app-portal) → Curadoria → Busca videos no YouTube
                     → Redator  → Gera conteudo (overlay, post, SEO)
                     → Editor   → Edita video (legendas, corte, render)
```

---

## 2. Stack Tecnologico

| Camada | Tecnologia |
|--------|-----------|
| Backend (todos) | Python 3.11, FastAPI, SQLAlchemy, Pydantic |
| Banco de dados | PostgreSQL (Railway) / SQLite (local) |
| Frontend Redator/Editor | React 18, Vite, TypeScript, Tailwind CSS |
| Frontend Portal | Next.js 16, React 19, TypeScript, Tailwind CSS, shadcn/ui |
| IA | Anthropic Claude (redator), Google Gemini 2.5 Pro (editor) |
| Video | FFmpeg, yt-dlp, ASS subtitles |
| YouTube API | YouTube Data API v3 |
| Deploy | Railway (Docker + Nixpacks) |
| Icones | Lucide React |
| UI Language | Portugues (PT-BR) |

---

## 3. Railway — Infraestrutura

### Projeto e Ambiente

| Item | Valor |
|------|-------|
| Projeto | `best-of-opera-app2` |
| Project ID | `c4d0468d-f3da-4765-b582-42cf6ef5ff66` |
| Environment | `production` |
| Environment ID | `4ec5a08f-d29e-4d7b-a54d-a3e161edd716` |
| Workspace | `bestofopera's Projects` |
| Workspace ID | `af0a2cc7-e912-4326-a1b6-83ba4280c34d` |

### Servicos (6 total)

| Servico | Service ID | Root Dir | URL Publica | Build |
|---------|-----------|----------|-------------|-------|
| app (redator) | `fade4ac2-8774-4287-b87d-7f2559898dcc` | `app-redator` | https://app-production-870c.up.railway.app | Nixpacks |
| editor-backend | `7e42a778-aa1e-4648-9ce1-07f5d6896fd5` | `app-editor/backend` | https://editor-backend-production.up.railway.app | Dockerfile |
| editor-frontend | `35ec9116-a3ee-4f9a-ad90-feeec2383238` | `app-editor/frontend` | https://editor-frontend-production.up.railway.app | Dockerfile (nginx) |
| curadoria (portal) | `b8fe934d-e3d7-4d30-a68a-4914e03cdb0a` | `app-portal` | https://curadoria-production-cf4a.up.railway.app | Dockerfile (Next.js standalone) |
| curadoria-backend | `e3eb935a-7b11-44fd-889f-fbd45edb0602` | `app-curadoria/backend` | https://curadoria-backend-production.up.railway.app | Dockerfile |
| Postgres | `1f423154-d150-46a3-a459-b62b55fe1004` | — | `postgres.railway.internal:5432` | Managed |

### Variaveis de Ambiente por Servico

#### app (Redator Backend)
```
ANTHROPIC_API_KEY = sk-ant-api03-hc_86KMXU...
DATABASE_URL = postgresql://postgres:bestofopera2024@postgres.railway.internal:5432/railway
GOOGLE_TRANSLATE_API_KEY = AIzaSyAi9eAu...
```

#### editor-backend
```
DATABASE_URL = postgresql://postgres:bestofopera2024@postgres.railway.internal:5432/railway
GEMINI_API_KEY = AIzaSyAQIB2H...
PORT = 8000
SECRET_KEY = editor-prod-secret-2026
STORAGE_PATH = /storage
CORS_ORIGINS = ["http://localhost:5174","http://localhost:3000","https://curadoria-production-cf4a.up.railway.app","https://editor-frontend-production.up.railway.app"]
```

#### editor-frontend
```
PORT = 80
VITE_API_URL = https://editor-backend-production.up.railway.app
```

#### curadoria-backend
```
DATABASE_URL = postgresql://postgres:bestofopera2024@postgres.railway.internal:5432/railway
YOUTUBE_API_KEY = AIzaSyBbVufo...
DATASET_PATH = ./dataset_v3_categorizado.csv
STATIC_PATH = ./static
PORT = 8000
```

#### curadoria (Portal Frontend)
```
PORT = 3000
NEXT_PUBLIC_CURADORIA_API_URL = https://curadoria-backend-production.up.railway.app
NEXT_PUBLIC_REDATOR_API_URL = https://app-production-870c.up.railway.app
NEXT_PUBLIC_EDITOR_API_URL = https://editor-backend-production.up.railway.app
```

> **IMPORTANTE:** O portal Next.js **NAO** usa rewrites para proxy. As URLs dos backends sao resolvidas em runtime no browser via deteccao de hostname (`window.location.hostname.includes("railway.app")`). Veja `app-portal/lib/api/base.ts`.

### Banco de Dados (PostgreSQL)

```
Host: postgres.railway.internal
Port: 5432
User: postgres
Password: bestofopera2024
Database: railway
```

Tabelas sao criadas automaticamente pelo SQLAlchemy (`Base.metadata.create_all`) em cada backend no startup. Os 3 backends compartilham o mesmo banco.

---

## 4. Detalhes de Cada App

### 4.1 App Curadoria (`app-curadoria/backend/`)

**Funcao:** Busca e curadoria de videos de opera no YouTube.

**Arquivos principais:**
- `main.py` — FastAPI app, endpoints de busca, scoring, download
- `database.py` — PostgreSQL connection, tabelas de cache/quota
- `dataset_v3_categorizado.csv` — Registry de 105+ videos ja postados

**Endpoints chave:**
| Metodo | Rota | Descricao |
|--------|------|-----------|
| GET | `/api/health` | Status + quota YouTube |
| GET | `/api/categories` | 6 categorias V7 com seed info |
| GET | `/api/category/{key}` | Busca por categoria (consome quota) |
| GET | `/api/search?q=` | Busca livre no YouTube |
| GET | `/api/ranking` | Ranking cross-categoria |
| GET | `/api/quota/status` | Cota restante YouTube API |
| GET | `/api/playlist/videos` | Videos da playlist em cache |
| GET | `/api/download/{video_id}` | Download de video (streaming) |
| GET | `/api/downloads` | Historico de downloads |

**Motor V7 — Features:**
- **Scoring:** Sistema de pontos (elite_hits +15, power_names +15, specialty +25, voice +15, etc.)
- **Seed Rotation:** 6 categorias x 6 seeds cada, rotaciona a cada query
- **Anti-Spam:** Remove karaoke, piano, tutorial, lesson, reaction, review
- **Duplicate Filter:** Normalizacao fuzzy de artista+musica vs posted list
- **Quota Tracking:** Log de consumo da YouTube API (10 units/search, 1 unit/details)

**Categorias V7:**
1. `icones` — Lendas (Pavarotti, Callas, Domingo)
2. `estrelas` — Modernas (Bocelli, Netrebko, Kaufmann)
3. `hits` — Arias populares (Nessun Dorma, Ave Maria)
4. `surpreendente` — Virais (flash mobs, talentos)
5. `talent` — Shows de talentos (Got Talent, auditions)
6. `corais` — Corais e a cappella

### 4.2 App Redator (`app-redator/`)

**Funcao:** Gera conteudo textual para redes sociais usando Claude AI.

**Backend (`app-redator/backend/`):**
- `main.py` — FastAPI app, serve frontend buildado
- `models.py` — SQLAlchemy models (Project, Translation)
- `services/claude_service.py` — Chamadas ao Anthropic Claude
- `services/translate_service.py` — Google Translate API
- `services/export_service.py` — Exportacao de projetos
- `prompts/` — Prompts para overlay, post, youtube, hook

**Frontend (`app-redator/frontend/`):**
- React + Vite + TypeScript
- Pages: Dashboard, NewProject, ApproveOverlay, ApprovePost, ApproveYoutube, Export

**Pipeline do Redator:**
1. Criar projeto (URL YouTube + metadata)
2. IA gera overlay (textos sobre o video)
3. IA gera post (texto para redes sociais)
4. IA gera titulo + tags YouTube
5. Usuario aprova/edita cada etapa
6. Traduzir para 7 idiomas (en, pt, es, de, fr, it, pl)
7. Exportar pacote (ZIP ou pasta)

**Build:** Nixpacks (definido em `railway.json` e `nixpacks.toml`). Builda o frontend React e serve como static files pelo FastAPI.

### 4.3 App Editor (`app-editor/`)

**Funcao:** Pipeline de edicao de video com legendas sincronizadas.

**Backend (`app-editor/backend/`):**
- `app/main.py` — FastAPI app
- `app/models/edicao.py` — Model Edicao, Render
- `app/routes/` — edicoes, letras, pipeline, health, importar
- `app/services/legendas.py` — Geracao de legendas ASS
- `app/services/` — FFmpeg, Gemini, download, transcricao

**Frontend (`app-editor/frontend/`):**
- React + Vite + TypeScript
- Comunicacao via `VITE_API_URL`

**Pipeline do Editor (9 etapas):**
1. Download video (yt-dlp)
2. Validar letra (Gemini search ou manual)
3. Transcricao (Gemini audio + letra → timestamps)
4. Validacao de alinhamento (fuzzy match, color-coded)
5. Aplicar corte (overlay window)
6. Traduzir letras (7 idiomas)
7. Render preview
8. Render final (FFmpeg + ASS subtitles)
9. Empacotar/exportar

**IMPORTANTE:** Railway tem **storage efemero** — renders sao perdidos quando o container reinicia.

### 4.4 Portal (`app-portal/`)

**Funcao:** Frontend unificado Next.js que integra os 3 apps.

**Estrutura:**
```
app-portal/
├── app/(app)/
│   ├── curadoria/        # Dashboard, Downloads
│   ├── redator/          # Projetos, Novo, Aprovar, Exportar
│   └── editor/           # Fila, Letra, Alinhamento, Conclusao
├── components/
│   ├── curadoria/        # dashboard, video-card, video-detail-modal
│   ├── redator/          # project-list, new-project, approve-*
│   ├── editor/           # editing-queue, validate-*, conclusion
│   └── ui/               # shadcn/ui components
├── lib/api/
│   ├── base.ts           # Request helpers + API_URLS (runtime detection)
│   ├── curadoria.ts      # curadoriaApi
│   ├── redator.ts        # redatorApi
│   └── editor.ts         # editorApi
└── Dockerfile            # Multi-stage (build + standalone)
```

**Deteccao de ambiente (base.ts):**
```typescript
// Detecta produccao pelo hostname do browser
function isProduction() {
  return typeof window !== "undefined" && window.location.hostname.includes("railway.app")
}
// Getters lazy para evitar problemas com SSR
export const API_URLS = {
  get curadoria() { return isProduction() ? "https://curadoria-backend-production..." : "http://localhost:8002" },
  get redator() { return isProduction() ? "https://app-production-870c..." : "http://localhost:8000" },
  get editor() { return isProduction() ? "https://editor-backend-production..." : "http://localhost:8001" },
}
```

---

## 5. Como Rodar Localmente

### Pre-requisitos
- Python 3.11+
- Node.js 20+
- FFmpeg
- PostgreSQL (ou usar SQLite para dev)

### Curadoria Backend
```bash
cd app-curadoria/backend
pip install -r requirements.txt
export YOUTUBE_API_KEY="AIzaSyBbVufo..."
export DATABASE_URL="sqlite:///./curadoria.db"  # ou PostgreSQL
uvicorn main:app --host 0.0.0.0 --port 8002
```

### Redator
```bash
# Backend
cd app-redator
pip install -r requirements.txt
export ANTHROPIC_API_KEY="sk-ant-..."
export DATABASE_URL="sqlite:///./best_of_opera.db"
uvicorn backend.main:app --host 0.0.0.0 --port 8000

# Frontend
cd app-redator/frontend
npm install && npm run dev  # porta 5173
```

### Editor
```bash
# Backend
cd app-editor/backend
pip install -r requirements.txt
export GEMINI_API_KEY="AIzaSyAQIB2H..."
export DATABASE_URL="sqlite:///./editor.db"
uvicorn app.main:app --host 0.0.0.0 --port 8001

# Frontend
cd app-editor/frontend
npm install && npm run dev  # porta 5174
```

### Portal
```bash
cd app-portal
npm install && npm run dev  # porta 3000
# Automaticamente usa localhost:8000/8001/8002 para os backends
```

---

## 6. Deploy (Railway)

### Via Git Push (automatico)
Railway faz auto-deploy a cada push para `main`. Cada servico monitora apenas seu `rootDirectory`.

### Via API GraphQL (manual/CLI)

**IMPORTANTE:** O Railway CLI (`railway` command) **NAO funciona** com Account Tokens. Usar a API GraphQL diretamente.

```bash
# Autenticar
export RAILWAY_TOKEN="seu-token-aqui"

# Verificar
curl -s -X POST "https://backboard.railway.com/graphql/v2" \
  -H "Authorization: Bearer $RAILWAY_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"query { me { id email } }"}'

# Redeploy de um servico
curl -s -X POST "https://backboard.railway.com/graphql/v2" \
  -H "Authorization: Bearer $RAILWAY_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"mutation { serviceInstanceRedeploy(serviceId: \"SERVICE_ID\", environmentId: \"4ec5a08f-d29e-4d7b-a54d-a3e161edd716\") }"}'

# Verificar status
curl -s -X POST "https://backboard.railway.com/graphql/v2" \
  -H "Authorization: Bearer $RAILWAY_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"query { project(id: \"c4d0468d-f3da-4765-b582-42cf6ef5ff66\") { services { edges { node { name serviceInstances { edges { node { latestDeployment { status } } } } } } } } }"}'
```

---

## 7. API Keys Necessarias

| Chave | Servico que usa | Onde obter |
|-------|----------------|------------|
| `ANTHROPIC_API_KEY` | Redator | https://console.anthropic.com |
| `GEMINI_API_KEY` | Editor | https://aistudio.google.com |
| `YOUTUBE_API_KEY` | Curadoria | https://console.cloud.google.com (YouTube Data API v3) |
| `GOOGLE_TRANSLATE_API_KEY` | Redator | https://console.cloud.google.com (Cloud Translation API) |
| `RAILWAY_TOKEN` | Deploy | https://railway.app/account/tokens |

---

## 8. Gotchas e Armadilhas

1. **Railway CLI vs API** — O CLI nao aceita Account Tokens (formato UUID). Sempre usar a GraphQL API em `backboard.railway.com/graphql/v2`.

2. **Next.js Standalone + Rewrites** — O modo `output: "standalone"` do Next.js NAO suporta rewrites para URLs externas. Por isso o portal usa deteccao runtime de hostname em `base.ts`.

3. **CORS** — O editor-backend usa uma lista explicita de origins (`CORS_ORIGINS`). Ao adicionar novos dominios, atualizar essa variavel. Redator e Curadoria usam `allow_origins=["*"]`.

4. **Storage Efemero** — Railway nao persiste arquivos entre deploys. Videos renderizados no editor sao perdidos. Considerar S3/R2 para persistencia.

5. **Quota YouTube** — Limite diario de ~10.000 unidades. Cada search custa 100 pontos. Monitorar em `/api/quota/status`.

6. **Banco Compartilhado** — Os 3 backends usam o mesmo PostgreSQL. As tabelas nao tem conflito de nomes, mas considerar schemas separados se escalar.

7. **Gemini Transcricao** — O prompt DEVE incluir "NAO omita versos" para evitar gaps nos timestamps.

8. **SQLite Local** — Para dev local, cada backend usa SQLite por default. O Redator usa `best_of_opera.db` (path relativo ao CWD).

---

## 9. Projetos Railway Legados

Existem outros projetos na mesma conta que podem ser desativados:
- `blissful-education` — Deploy antigo da curadoria (substituido por curadoria-backend)
- `skillful-respect` — Apenas Postgres (parece abandonado)
- `believable-communication` — Web service (parece abandonado)

---

## 10. Proximos Passos Sugeridos

- [ ] Adicionar dominio customizado (ex: app.bestofopera.com)
- [ ] Migrar storage de videos para S3/R2 (resolver ephemeral storage)
- [ ] Separar schemas do PostgreSQL por app
- [ ] Adicionar CI/CD (GitHub Actions para testes antes do deploy)
- [ ] Implementar autenticacao robusta no portal (atualmente aberto)
- [ ] Monitoramento/alertas (uptime, erros, quota)
- [ ] Dockerfiles para Redator (atualmente usa Nixpacks)
