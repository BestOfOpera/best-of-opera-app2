# AUDITORIA PROFUNDA DO SISTEMA — Best of Opera

> **Data:** 2026-04-04
> **Tipo:** Somente leitura. Nenhum arquivo foi alterado.
> **Objetivo:** Mapeamento completo para planejamento de features (dashboard, calendário, organização, UX)

---

# SEÇÃO 1 — ESTRUTURA DE DIRETÓRIOS

## 1.1 Árvore de diretórios (2 níveis)

### app-curadoria/
```
app-curadoria/backend/
├── config.py                    (Config + brand loading + 138 linhas)
├── database.py                  (PostgreSQL + DDL migrations + 502 linhas)
├── main.py                      (FastAPI app + lifespan + 78 linhas)
├── worker.py                    (Background task queue)
├── dataset_v3_categorizado.csv  (Seed dataset para categorias)
├── Dockerfile
├── railway.json
├── requirements.txt
├── data/                        (Brand JSON configs fallback)
│   └── best-of-opera.json
├── routes/
│   ├── __init__.py
│   ├── curadoria.py             (742 linhas — todos os endpoints)
│   └── health.py
├── services/
│   ├── scoring.py               (V7 scoring algorithm)
│   ├── youtube.py               (YouTube API v3 integration)
│   └── download.py              (yt-dlp + cobalt + R2 upload)
└── static/                      (Frontend estático — legado)
```

### app-redator/
```
app-redator/backend/
├── config.py                    (209 linhas — config + brand loading)
├── database.py                  (SQLAlchemy setup)
├── main.py                      (94 linhas — FastAPI + migrations)
├── models.py                    (90 linhas — Project + Translation)
├── schemas.py                   (168 linhas — Pydantic models)
├── requirements.txt
├── routers/
│   ├── __init__.py
│   ├── projects.py              (CRUD + R2 management)
│   ├── generation.py            (Claude generation + RC)
│   ├── approval.py              (Status approvals)
│   ├── translation.py           (Multi-language)
│   ├── export.py                (ZIP/R2 export)
│   └── health.py
├── services/
│   ├── claude_service.py        (Anthropic SDK — Claude Sonnet)
│   ├── translate_service.py     (Google Translate API)
│   └── export_service.py        (R2/ZIP packaging)
└── prompts/                     (Claude prompt templates)
```

### app-editor/
```
app-editor/backend/app/
├── config.py                    (27 linhas — env vars)
├── database.py                  (SQLAlchemy setup)
├── main.py                      (~500 linhas — migrations + seeds)
├── worker.py                    (140 linhas — sequential queue)
├── schemas.py                   (Pydantic schemas)
├── models/
│   ├── edicao.py                (61 linhas — modelo principal)
│   ├── perfil.py                (80 linhas — multi-brand config)
│   ├── overlay.py               (subtitles por idioma)
│   ├── letra.py                 (lyrics)
│   ├── post.py                  (social post)
│   ├── seo.py                   (YouTube metadata)
│   ├── alinhamento.py           (alignment data)
│   ├── traducao_letra.py        (translated lyrics)
│   ├── render.py                (render output)
│   ├── report.py                (bug reports)
│   └── usuario.py               (auth users)
├── routes/
│   ├── edicoes.py               (Edition CRUD)
│   ├── importar.py              (Import from Redator)
│   ├── pipeline.py              (~3000 linhas — MAIOR ARQUIVO)
│   ├── letras.py                (Lyrics API)
│   ├── dashboard.py             (Analytics)
│   ├── auth.py                  (Authentication JWT)
│   ├── admin_perfil.py          (Profile management)
│   ├── reports.py               (Reporting)
│   └── health.py
├── services/
│   ├── legendas.py              (FFmpeg text overlay + PIL)
│   ├── transcript.py            (Gemini STT)
│   ├── alignment.py             (Viterbi alignment)
│   ├── render.py                (FFmpeg rendering)
│   └── lyrics.py                (Genius.com API)
├── middleware/
│   └── auth.py                  (JWT middleware)
└── utils/                       (Helpers)
```

### app-portal/
```
app-portal/
├── app/                          (Next.js 13+ app router)
│   ├── (app)/                    (Route group — protected)
│   │   ├── admin/marcas/         (Brand management)
│   │   ├── admin/usuarios/       (User management)
│   │   ├── curadoria/            (Curation module)
│   │   ├── editor/               (Video editor module)
│   │   ├── redator/              (Content writer module)
│   │   └── layout.tsx            (RequireAuth + AppShell)
│   ├── dashboard/                (Dashboard routes)
│   ├── alterar-senha/            (Change password)
│   ├── login/                    (Login page)
│   ├── layout.tsx                (Root: providers)
│   └── page.tsx                  (Redirect → /curadoria)
├── components/
│   ├── admin/                    (Brand preview & config)
│   ├── auth/                     (Auth guards)
│   ├── curadoria/                (Dashboard, VideoCard, VideoDetailModal, Downloads, ScoreRing)
│   ├── dashboard/                (VisaoGeral, Saude, Producao, Reports)
│   ├── editor/                   (EditingQueue, Overview, ValidateLyrics, ValidateAlignment, Conclusion)
│   ├── redator/                  (ProjectList, ApproveOverlay, ApprovePost, ApproveYoutube, ApproveHooksRC, ApproveAutomationRC, NewProject, ExportPage)
│   ├── ui/                       (shadcn: badge, button, card, checkbox, dialog, dropdown-menu, input, label, progress, select, slider, table, tabs, textarea)
│   ├── app-sidebar.tsx           (135 linhas)
│   ├── app-shell.tsx             (60 linhas)
│   ├── app-breadcrumb.tsx
│   ├── brand-selector.tsx        (161 linhas)
│   ├── status-badge.tsx          (30 linhas)
│   └── pipeline-stepper.tsx      (191 linhas)
├── lib/
│   ├── api/
│   │   ├── base.ts              (126 linhas — request helper)
│   │   ├── curadoria.ts         (218 linhas)
│   │   ├── editor.ts            (442 linhas)
│   │   └── redator.ts           (218 linhas)
│   ├── auth-context.tsx          (123 linhas)
│   ├── brand-context.tsx         (47 linhas)
│   ├── hooks/
│   │   └── use-polling.ts       (63 linhas)
│   └── utils.ts
├── package.json
└── tsconfig.json
```

## 1.2 Todas as rotas do app-portal

```
/                                          → redirect /curadoria
/login                                     → Login page (public)
/alterar-senha                             → Change password

/(app)/curadoria                           → CuradoriaDashboard
/(app)/curadoria/downloads                 → Downloads list
/(app)/redator                             → RedatorProjectList
/(app)/redator/novo                        → New project form
/(app)/redator/projeto/[id]/overlay        → Approve overlay
/(app)/redator/projeto/[id]/post           → Approve post
/(app)/redator/projeto/[id]/youtube        → Approve YouTube meta
/(app)/redator/projeto/[id]/automation     → Approve automation (RC)
/(app)/redator/projeto/[id]/hooks          → Select hook (RC)
/(app)/redator/projeto/[id]/exportar       → Export data
/(app)/editor                              → EditorEditingQueue
/(app)/editor/edicao/[id]/overview         → Editing overview
/(app)/editor/edicao/[id]/letra            → Validate lyrics
/(app)/editor/edicao/[id]/alinhamento      → Validate alignment
/(app)/editor/edicao/[id]/conclusao        → Conclusion screen
/(app)/admin/marcas                        → Brands list (Admin)
/(app)/admin/marcas/[id]                   → Brand edit (Admin)
/(app)/admin/marcas/nova                   → New brand (Admin)
/(app)/admin/usuarios                      → Users list (Admin)
/dashboard                                 → Overview
/dashboard/projeto/[id]                    → Project detail
/dashboard/saude                           → Health check
/dashboard/producao                        → Production metrics
/dashboard/reports                         → Reports list
/dashboard/reports/[id]                    → Report detail
```

**Total: 28 rotas** (23 protegidas + 2 públicas + 3 admin)

---

# SEÇÃO 2 — MODELOS DE DADOS

## 2.1 app-curadoria — Tabelas (raw SQL, sem ORM)

**Arquivo:** `app-curadoria/backend/database.py`

### cached_videos
```sql
CREATE TABLE IF NOT EXISTS cached_videos (
    id SERIAL PRIMARY KEY,
    video_id TEXT NOT NULL,
    url TEXT,
    title TEXT,
    artist TEXT,
    song TEXT,
    channel TEXT,
    year INTEGER,
    published TEXT,
    duration INTEGER,
    views INTEGER,
    hd BOOLEAN,
    thumbnail TEXT,
    category TEXT,
    score_total INTEGER,
    score_fixed INTEGER,
    score_guia REAL,
    artist_match TEXT,
    song_match TEXT,
    posted BOOLEAN,
    brand_slug TEXT NOT NULL DEFAULT 'best-of-opera',
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(video_id, category, brand_slug)
);
-- Indexes: idx_category, idx_score(DESC), idx_video_id, idx_cached_brand
```

**Status:** Não há campo status — vídeos são cached (existem) ou não.
**Marca:** `brand_slug` TEXT NOT NULL DEFAULT 'best-of-opera'
**Cross-ref:** `video_id` (YouTube 11-char ID) — usado como referência cruzada com editor via `curadoria_video_id`

### playlist_videos
```sql
CREATE TABLE IF NOT EXISTS playlist_videos (
    id SERIAL PRIMARY KEY,
    video_id TEXT NOT NULL,
    url TEXT, title TEXT, artist TEXT, song TEXT, channel TEXT,
    year INTEGER, published TEXT, duration INTEGER, views INTEGER,
    hd BOOLEAN, thumbnail TEXT,
    score_total INTEGER, score_fixed INTEGER, score_guia REAL,
    artist_match TEXT, song_match TEXT, posted BOOLEAN,
    position INTEGER,
    brand_slug TEXT NOT NULL DEFAULT 'best-of-opera',
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- UNIQUE(video_id, brand_slug)
```

### system_config
```sql
CREATE TABLE IF NOT EXISTS system_config (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### downloads
```sql
CREATE TABLE IF NOT EXISTS downloads (
    id SERIAL PRIMARY KEY,
    video_id TEXT NOT NULL,
    filename TEXT,
    artist TEXT,
    song TEXT,
    youtube_url TEXT,
    brand_slug TEXT DEFAULT NULL,
    downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### category_seeds
```sql
CREATE TABLE IF NOT EXISTS category_seeds (
    category_id TEXT PRIMARY KEY,
    last_seed INTEGER DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### quota_usage
```sql
CREATE TABLE IF NOT EXISTS quota_usage (
    usage_date DATE PRIMARY KEY,
    search_calls INTEGER DEFAULT 0,
    detail_calls INTEGER DEFAULT 0,
    total_points INTEGER DEFAULT 0
);
```

## 2.2 app-redator — Modelos SQLAlchemy (Mapped[T] — 2.0 style)

**Arquivo:** `app-redator/backend/models.py`

```python
class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Source
    youtube_url: Mapped[str] = mapped_column(String(500), default="")

    # Metadata
    artist: Mapped[str] = mapped_column(String(255))
    work: Mapped[str] = mapped_column(String(255))
    composer: Mapped[str] = mapped_column(String(255))
    composition_year: Mapped[str] = mapped_column(String(50), default="")
    nationality: Mapped[str] = mapped_column(String(255), default="")
    nationality_flag: Mapped[str] = mapped_column(String(100), default="")
    voice_type: Mapped[str] = mapped_column(String(255), default="")
    birth_date: Mapped[str] = mapped_column(String(255), default="")
    death_date: Mapped[str] = mapped_column(String(255), default="")
    album_opera: Mapped[str] = mapped_column(String(255), default="")
    category: Mapped[str] = mapped_column(String(100), default="")
    hook: Mapped[str] = mapped_column(Text, default="")
    hook_category: Mapped[str] = mapped_column(String(50), default="")
    highlights: Mapped[str] = mapped_column(Text, default="")
    original_duration: Mapped[str] = mapped_column(String(20), default="")
    cut_start: Mapped[str] = mapped_column(String(20), default="")
    cut_end: Mapped[str] = mapped_column(String(20), default="")

    # Multi-brand
    perfil_id: Mapped[Optional[int]] = mapped_column(nullable=True)
    brand_slug: Mapped[str] = mapped_column(String(50), nullable=False)  # SEM DEFAULT (SPEC-009)

    # Status machine
    status: Mapped[str] = mapped_column(String(50), default="input_complete")
    # Valores: input_complete | generating | awaiting_approval | translating | export_ready

    # Generated content
    overlay_json: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)
    post_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    youtube_title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    youtube_tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Approval flags
    overlay_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    post_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    youtube_approved: Mapped[bool] = mapped_column(Boolean, default=False)

    # RC (Reels Classics)
    research_data: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)
    hooks_json: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)
    selected_hook: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    automation_json: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)
    automation_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    instrument_formation: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    orchestra: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    conductor: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    translations: Mapped[list["Translation"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )


class Translation(Base):
    __tablename__ = "translations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    language: Mapped[str] = mapped_column(String(10))  # pt, es, de, fr, it, pl

    overlay_json: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)
    post_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    youtube_title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    youtube_tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    project: Mapped["Project"] = relationship(back_populates="translations")
```

## 2.3 app-editor — Modelos SQLAlchemy (Column() — 1.x style)

**Arquivo:** `app-editor/backend/app/models/edicao.py`

```python
class Edicao(Base):
    __tablename__ = "editor_edicoes"

    id = Column(Integer, primary_key=True, index=True)
    curadoria_video_id = Column(Integer, nullable=True)
    youtube_url = Column(String(500), nullable=False)
    youtube_video_id = Column(String(20), nullable=False)

    artista = Column(String(300), nullable=False)
    musica = Column(String(300), nullable=False)
    compositor = Column(String(300))
    opera = Column(String(300))
    categoria = Column(String(50))
    idioma = Column(String(10), nullable=False)
    eh_instrumental = Column(Boolean, default=False)
    sem_lyrics = Column(Boolean, default=False)
    duracao_total_sec = Column(Float)

    status = Column(String(30), default="aguardando")
    # Valores: aguardando | baixando | cortando | transcricao | traducao |
    #          renderizando | preview_pronto | concluido | erro
    passo_atual = Column(Integer, default=1)
    erro_msg = Column(Text)

    janela_inicio_sec = Column(Float)
    janela_fim_sec = Column(Float)
    duracao_corte_sec = Column(Float)
    corte_original_inicio = Column(String(20))
    corte_original_fim = Column(String(20))

    arquivo_video_completo = Column(String(500))
    arquivo_video_cortado = Column(String(500))
    arquivo_audio_completo = Column(String(500))
    arquivo_video_cru = Column(String(500))

    rota_alinhamento = Column(String(5))
    confianca_alinhamento = Column(Float)

    r2_base = Column(String(500), nullable=True)      # "Pavarotti - Nessun Dorma"
    redator_project_id = Column(Integer, nullable=True)
    notas_revisao = Column(Text, nullable=True)

    editado_por = Column(String(100))
    tempo_edicao_seg = Column(Integer)

    task_heartbeat = Column(DateTime, nullable=True)
    progresso_detalhe = Column(JSON, default=dict)
    tentativas_requeue = Column(Integer, default=0)

    perfil_id = Column(Integer, ForeignKey("editor_perfis.id"), nullable=True)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
```

**Arquivo:** `app-editor/backend/app/models/perfil.py`

```python
class Perfil(Base):
    __tablename__ = "editor_perfis"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), unique=True, nullable=False)       # "Best of Opera"
    sigla = Column(String(5), nullable=False)                     # "BO"
    slug = Column(String(50), unique=True, nullable=False)        # "best-of-opera"
    ativo = Column(Boolean, default=True)
    sem_lyrics_default = Column(Boolean, default=False)

    # Identidade
    identity_prompt = Column(Text)
    tom_de_voz = Column(Text)
    editorial_lang = Column(String(5), default="pt")
    hashtags_fixas = Column(JSON, default=list)
    categorias_hook = Column(JSON, default=list)

    # Idiomas
    idiomas_alvo = Column(JSON, default=lambda: ["en", "pt", "es", "de", "fr", "it", "pl"])
    idioma_preview = Column(String(5), default="pt")

    # Estilos de legenda
    overlay_style = Column(JSON, default=dict)
    lyrics_style = Column(JSON, default=dict)
    traducao_style = Column(JSON, default=dict)

    # Limites
    overlay_max_chars = Column(Integer, default=70)
    overlay_max_chars_linha = Column(Integer, default=30)
    lyrics_max_chars = Column(Integer, default=43)
    traducao_max_chars = Column(Integer, default=100)
    overlay_interval_secs = Column(Integer, default=6)

    # Video
    video_width = Column(Integer, default=1080)
    video_height = Column(Integer, default=1920)

    # Curadoria
    escopo_conteudo = Column(Text)
    curadoria_categories = Column(JSON, default=dict)
    elite_hits = Column(JSON, default=list)
    power_names = Column(JSON, default=list)
    voice_keywords = Column(JSON, default=list)
    institutional_channels = Column(JSON, default=list)
    category_specialty = Column(JSON, default=dict)
    scoring_weights = Column(JSON, default=dict)
    curadoria_filters = Column(JSON, default=dict)
    anti_spam_terms = Column(String(500), default="-karaoke -piano ...")
    playlist_id = Column(String(100), default="")

    # Redator
    hook_categories_redator = Column(JSON, default=dict)
    identity_prompt_redator = Column(Text)
    tom_de_voz_redator = Column(Text)
    custom_post_structure = Column(Text)
    brand_opening_line = Column(Text)
    hashtag_count = Column(Integer)
    logo_url = Column(String(500))
    font_name = Column(String(100))
    font_file_r2_key = Column(String(200))
    overlay_cta = Column(Text)   # CTA em PT-BR, traduzido automaticamente

    # Visual
    cor_primaria = Column(String(10), default="#1a1a2e")
    cor_secundaria = Column(String(10), default="#e94560")

    # R2
    r2_prefix = Column(String(100), default="editor")

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
```

**Sub-modelos do editor (resumo):**

| Tabela | Arquivo | Campos chave |
|--------|---------|-------------|
| editor_overlays | overlay.py | edicao_id, idioma, segmentos(JSON) |
| editor_letras | letra.py | edicao_id, artista, musica, idioma, lyrics_json |
| editor_posts | post.py | edicao_id, idioma, texto |
| editor_seos | seo.py | edicao_id, idioma, titulo, descricao, tags |
| editor_alinhamentos | alinhamento.py | edicao_id, confianca, resultado(JSON) |
| editor_traducoes_letras | traducao_letra.py | letra_id, idioma, texto_traduzido |
| editor_renders | render.py | edicao_id, idioma, formato, status, r2_key |
| editor_reports | report.py | perfil_id, tipo, titulo, prioridade, status, screenshots(JSON) |
| editor_usuarios | usuario.py | nome, email, senha_hash, role, is_admin |

## 2.4 Mapa de Relacionamentos

```
┌─────────────┐     video_id      ┌──────────────┐
│ CURADORIA   │ ◄─────────────────│   EDITOR     │
│ cached_     │   curadoria_      │ editor_      │
│ videos      │   video_id        │ edicoes      │
└─────────────┘                   └──────┬───────┘
                                         │ redator_project_id
                                         │
┌─────────────┐                   ┌──────▼───────┐
│ REDATOR     │ ◄─────────────────│   EDITOR     │
│ projects    │   (HTTP fetch)     │ (importar)   │
└──────┬──────┘                   └──────────────┘
       │ 1:N
┌──────▼──────┐
│ translations │
└─────────────┘
```

**Conexões:**
- **Editor → Redator:** `redator_project_id` em `editor_edicoes` aponta para `projects.id` do redator (via HTTP import, não FK real)
- **Editor → Curadoria:** `curadoria_video_id` em `editor_edicoes` (referência opcional, sem FK)
- **Cada app tem banco SEPARADO** (3 PostgreSQL no Railway + 1 SQLite local do redator em dev)
- **NÃO há FKs reais entre apps** — a integridade é via HTTP + IDs de referência

---

# SEÇÃO 3 — MIGRATIONS

## 3.1 Abordagem

Todas as 3 apps usam **migrations inline** no startup (não Alembic):
- **Curadoria:** DDL direto em `database.py:init_db()` com `CREATE TABLE IF NOT EXISTS` + `ALTER TABLE ADD COLUMN IF NOT EXISTS`
- **Redator:** `main.py:_run_migrations()` com `sa_inspect` para verificar colunas existentes
- **Editor:** `main.py:_run_migrations()` com verificação por coluna + seeds idempotentes

## 3.2 Lista de migrations

### app-curadoria
| N | O que faz | Tabela | Idempotente? |
|---|-----------|--------|-------------|
| 1 | CREATE cached_videos | cached_videos | Sim (IF NOT EXISTS) |
| 2 | ADD brand_slug | cached_videos | Sim (IF NOT EXISTS) |
| 3 | UPDATE UNIQUE constraint multi-column | cached_videos | Sim (DROP IF EXISTS + CREATE IF NOT EXISTS) |
| 4 | CREATE playlist_videos | playlist_videos | Sim |
| 5 | ADD brand_slug | playlist_videos | Sim |
| 6 | UPDATE UNIQUE constraint | playlist_videos | Sim |
| 7 | CREATE system_config | system_config | Sim |
| 8 | CREATE downloads | downloads | Sim |
| 9 | ADD brand_slug | downloads | Sim |
| 10 | CREATE category_seeds | category_seeds | Sim |
| 11 | CREATE quota_usage | quota_usage | Sim |

### app-redator
| N | O que faz | Tabela | Idempotente? |
|---|-----------|--------|-------------|
| 1 | CREATE projects + translations | auto via create_all | Sim |
| 2 | ADD hook_category | projects | Sim (verifica cols) |
| 3 | ADD perfil_id | projects | Sim |
| 4 | ADD brand_slug + DROP DEFAULT | projects | **Parcial** — DROP DEFAULT roda toda vez |
| 5 | v13: ADD research_data, hooks_json, selected_hook, automation_json, automation_approved | projects | Sim |
| 6 | v14: ADD instrument_formation, orchestra, conductor | projects | Sim |

### app-editor
| N | O que faz | Tabela | Idempotente? |
|---|-----------|--------|-------------|
| 1 | CREATE editor_perfis | editor_perfis | Sim |
| 2 | Seed BO profile (idempotent check by slug) | editor_perfis | Sim |
| 3 | Seed RC profile (idempotent check by slug) | editor_perfis | Sim |
| 4 | Backfill fonts, styles, weights | editor_perfis | Sim (check before update) |
| 5 | Multiple column adds across all model tables | vários | Sim (IF NOT EXISTS) |

---

# SEÇÃO 4 — APIs COMPLETAS

## 4.1 app-curadoria — Endpoints

**Prefixo:** `/api/` (montado via `routes/curadoria.py`)

| Método | Path | Params | O que faz | Frontend chama? |
|--------|------|--------|-----------|----------------|
| POST | /api/auth | password(query) | Verifica senha | Sim (curadoriaApi.auth) |
| GET | /api/health | — | YouTube API status | Sim (curadoriaApi.health) |
| GET | /api/quota/status | — | Uso diário da cota | Sim (curadoriaApi.quota) |
| GET | /api/posted | — | Total de vídeos postados | **GHOST** — não encontrado no frontend |
| GET | /api/posted/check | artist, song | Verifica se postado | **GHOST** |
| GET | /api/categories | brand_slug | Lista categorias | Sim |
| GET | /api/category/{key} | hide_posted, force_refresh, brand_slug | Busca por categoria (V7 seed) | Sim |
| GET | /api/search | q, max_results, hide_posted, brand_slug | Busca manual YouTube | Sim |
| GET | /api/ranking | hide_posted, brand_slug | Ranking cross-category | Sim |
| POST | /api/manual-video | youtube_url, brand_slug | Adicionar vídeo manual | Sim |
| GET | /api/playlist/videos | hide_posted, brand_slug | Vídeos da playlist | Sim |
| POST | /api/playlist/refresh | brand_slug | Refresh playlist (background) | Sim |
| POST | /api/playlist/download-all | brand_slug | Download todos da playlist | **GHOST** |
| GET | /api/playlist/download-status | — | Status de downloads | **GHOST** |
| GET | /api/download/{video_id} | artist, song, brand_slug | Stream download + R2 upload | Sim |
| POST | /api/prepare-video/{video_id} | artist, song, brand_slug | Download → R2 (sem stream) | Sim |
| POST | /api/upload-video/{video_id} | file(form), artist, song, brand_slug | Upload manual pro R2 | Sim |
| GET | /api/r2/check | artist, song, video_id, brand_slug | Verifica existência no R2 | Sim |
| GET | /api/r2/info | folder, brand_slug | Metadados do vídeo no R2 | Sim |
| GET | /api/downloads | brand_slug | Lista downloads | Sim |
| GET | /api/downloads/brands | — | Marcas com downloads | Sim |
| GET | /api/downloads/export | brand_slug | Export CSV | Sim |
| GET | /api/cache/status | — | Status do cache | Sim |
| POST | /api/cache/populate-initial | brand_slug | Popula cache (background) | **GHOST** — automático no startup |
| POST | /api/cache/refresh-categories | brand_slug | Refresh categorias | **GHOST** |
| POST | /api/quota/register | search_calls, detail_calls | Registra uso | **GHOST** — interno |
| GET | /health | — | Health check simples | Sim |

**Total: 27 endpoints (6 ghost)**

## 4.2 app-redator — Endpoints

**Prefixo:** `/api/` (montado via múltiplos routers)

| Método | Path | Params | O que faz | Frontend chama? |
|--------|------|--------|-----------|----------------|
| POST | /api/projects | ProjectCreate(body) | Criar projeto | Sim |
| GET | /api/projects | brand_slug | Listar projetos | Sim |
| GET | /api/projects/r2-available | brand_slug, r2_prefix | Vídeos no R2 sem projeto | Sim |
| DELETE | /api/projects/r2-available | folders[](body) | Deletar itens R2 | Sim |
| DELETE | /api/projects/by-brand/{slug} | — | Bulk delete por marca | Sim |
| DELETE | /api/projects/bulk | ids[](body) | Bulk delete por IDs | Sim |
| DELETE | /api/projects/{id} | — | Deletar projeto | Sim |
| GET | /api/projects/{id} | — | Detalhe do projeto | Sim |
| PUT | /api/projects/{id} | ProjectUpdate(body) | Atualizar projeto | Sim |
| POST | /api/projects/detect-metadata | file, youtube_url, brand_slug | Detect via screenshot | Sim |
| POST | /api/projects/detect-metadata-text | youtube_url, title, desc, brand_slug | Detect via texto | Sim |
| POST | /api/projects/{id}/generate | — | Gerar todo conteúdo | Sim |
| POST | /api/projects/{id}/regenerate-overlay | custom_prompt | Regenerar overlay | Sim |
| POST | /api/projects/{id}/regenerate-post | custom_prompt | Regenerar post | Sim |
| POST | /api/projects/{id}/regenerate-youtube | custom_prompt | Regenerar YouTube | Sim |
| POST | /api/projects/{id}/generate-hooks | — | Gerar 5 hooks narrativos | Sim |
| POST | /api/projects/{id}/generate-research-rc | — | RC: deep research | Sim |
| POST | /api/projects/{id}/generate-hooks-rc | — | RC: hooks from research | Sim |
| PUT | /api/projects/{id}/select-hook | hook_index, custom_hook | RC: selecionar hook | Sim |
| POST | /api/projects/{id}/generate-overlay-rc | — | RC: overlay from hook | Sim |
| POST | /api/projects/{id}/generate-post-rc | — | RC: post from hook | Sim |
| POST | /api/projects/{id}/generate-automation-rc | — | RC: automation data | Sim |
| PUT | /api/projects/{id}/approve-overlay | overlay_json | Aprovar overlay | Sim |
| PUT | /api/projects/{id}/approve-post | post_text | Aprovar post | Sim |
| PUT | /api/projects/{id}/approve-youtube | title, tags | Aprovar YouTube meta | Sim |
| PUT | /api/projects/{id}/approve-automation | — | RC: aprovar automation | Sim |
| POST | /api/projects/{id}/translate | — | Traduzir p/ todos idiomas | Sim |
| POST | /api/projects/{id}/retranslate/{lang} | — | Retraduzir idioma | Sim |
| PUT | /api/projects/{id}/translation/{lang} | data(body) | Editar tradução | Sim |
| GET | /api/export-config | — | Config de exportação | Sim |
| POST | /api/projects/{id}/export | — | Export ZIP | Sim |
| POST | /api/projects/{id}/export-to-folder | — | Export to folder | Sim |
| POST | /api/projects/{id}/save-to-r2 | — | Save to R2 | Sim |
| GET | /health | — | Health check | Sim |

**Total: 34 endpoints (0 ghost)**

## 4.3 app-editor — Endpoints

**Prefixo:** `/api/v1/editor/` (montado via múltiplos routers)

| Método | Path | Params | O que faz | Frontend chama? |
|--------|------|--------|-----------|----------------|
| **Auth** | | | | |
| POST | /auth/login | email, senha | Login JWT | Sim |
| GET | /auth/me | — | User atual | Sim |
| GET | /auth/usuarios | — | Listar usuários | Sim |
| POST | /auth/registrar | data + senha | Criar usuário | Sim |
| PATCH | /auth/usuarios/{id} | data + senha? | Atualizar usuário | Sim |
| POST | /auth/alterar-senha | senha_nova | Alterar senha | Sim |
| **Edicoes** | | | | |
| GET | /edicoes | status?, perfil_id? | Listar edições | Sim |
| POST | /edicoes | EdicaoCreate | Criar edição | Sim |
| GET | /edicoes/{id} | — | Detalhe edição | Sim |
| PATCH | /edicoes/{id} | EdicaoUpdate | Atualizar edição | Sim |
| DELETE | /edicoes/{id} | — | Deletar (limpa R2) | Sim |
| POST | /edicoes/{id}/upload-overlays | file(ZIP) | Upload legendas JSON | Sim |
| POST | /edicoes/{id}/upload-video | file | Upload vídeo manual | Sim |
| GET | /edicoes/{id}/video/status | — | Status do vídeo | Sim |
| **Pipeline** | | | | |
| POST | /edicoes/{id}/garantir-video | — | Garantir download | Sim |
| POST | /edicoes/{id}/letra | — | Buscar/transcrever letra | Sim |
| PUT | /edicoes/{id}/letra | letra(body) | Aprovar letra | Sim |
| POST | /edicoes/{id}/transcricao | — | Transcrição Gemini | Sim |
| POST | /edicoes/{id}/alinhamento-manual | — | Criar alinhamento manual | Sim |
| GET | /edicoes/{id}/alinhamento | — | Obter alinhamento | Sim |
| PUT | /edicoes/{id}/alinhamento | segmentos(body) | Validar alinhamento | Sim |
| POST | /edicoes/{id}/aplicar-corte | params? | Aplicar corte no vídeo | Sim |
| GET | /edicoes/{id}/corte | — | Info do corte | Sim |
| POST | /edicoes/{id}/traducao-lyrics | — | Traduzir lyrics | Sim |
| GET | /edicoes/{id}/traducao-lyrics | — | Obter traduções | Sim |
| POST | /edicoes/{id}/renderizar | sem_legendas? | Render final | Sim |
| POST | /edicoes/{id}/renderizar-preview | sem_legendas? | Render preview | Sim |
| POST | /edicoes/{id}/aprovar-preview | aprovado, notas | Aprovar preview | Sim |
| GET | /edicoes/{id}/renders | — | Listar renders | Sim |
| POST | /edicoes/{id}/re-renderizar/{lang} | — | Re-render idioma | Sim |
| POST | /edicoes/{id}/re-traduzir/{lang} | — | Re-traduzir idioma | Sim |
| GET | /edicoes/{id}/audio | — | Stream áudio | Sim (URL) |
| GET | /edicoes/{id}/renders/{rid}/download | — | Download render | Sim (URL) |
| POST | /edicoes/{id}/pacote | — | Gerar pacote ZIP | Sim |
| GET | /edicoes/{id}/pacote/status | — | Status pacote | Sim |
| GET | /edicoes/{id}/pacote/download | — | Download pacote | Sim (URL) |
| POST | /edicoes/{id}/exportar | — | Exportar para pasta | Sim |
| POST | /edicoes/{id}/desbloquear | — | Desbloquear edição presa | Sim |
| POST | /edicoes/{id}/limpar-edicao | — | Limpar e resetar edição | Sim |
| POST | /edicoes/{id}/limpar-traducoes | — | Limpar traduções | **GHOST** |
| POST | /edicoes/{id}/reset-traducao | — | Reset tradução | **GHOST** |
| GET | /fila/status | — | Status do worker | Sim |
| **Import** | | | | |
| GET | /redator/projetos | perfil_id? | Listar projetos do redator | Sim |
| POST | /redator/importar/{id} | idioma, eh_instrumental, perfil_id | Importar do redator | Sim |
| **Dashboard** | | | | |
| GET | /dashboard/visao-geral | perfil_id? | Overview geral | Sim |
| GET | /dashboard/saude | — | Health metrics | Sim |
| GET | /dashboard/producao | — | Production metrics | Sim |
| GET | /dashboard/stats | — | Estatísticas detalhadas | **GHOST** |
| GET | /dashboard/edicoes-recentes | — | Edições recentes | **GHOST** |
| GET | /dashboard/fila | — | Fila status | **GHOST** |
| GET | /dashboard/pipeline | — | Pipeline status | **GHOST** |
| **Reports** | | | | |
| POST | /reports | data, perfil_id | Criar report | Sim |
| POST | /reports/{id}/screenshot | file | Upload screenshot | Sim |
| GET | /reports | params?, perfil_id | Listar reports | Sim |
| GET | /reports/{id} | — | Detalhe report | Sim |
| PATCH | /reports/{id} | data | Atualizar report | Sim |
| DELETE | /reports/{id} | — | Deletar report | Sim |
| GET | /reports/resumo | perfil_id? | Resumo reports | Sim |
| DELETE | /reports/resolvidos | perfil_id? | Deletar resolvidos | Sim |
| **Admin** | | | | |
| GET | /admin/perfis | — | Listar perfis | Sim |
| GET | /admin/perfis/{id} | — | Detalhe perfil | Sim |
| POST | /admin/perfis | data | Criar perfil | Sim |
| PUT | /admin/perfis/{id} | data, force? | Atualizar perfil | Sim |
| PATCH | /admin/perfis/{id} | data, force? | Atualizar parcial | Sim |
| POST | /admin/perfis/{id}/duplicar | — | Duplicar perfil | Sim |
| DELETE | /admin/perfis/{id}/edicoes | force? | Resetar edições do perfil | Sim |
| GET | /admin/perfis/{id}/preview-legenda | — | Preview de legenda | Sim |
| POST | /admin/perfis/{id}/upload-font | file, force? | Upload fonte | Sim |
| GET | /admin/perfis/{id}/curadoria-config | — | Config curadoria (interno) | **GHOST** (usado inter-app) |
| GET | /admin/perfis/template-bo | — | Template BO | **GHOST** |
| GET | /health | — | Health check | Sim |

**Total: ~70 endpoints (8 ghost, 2 inter-app)**

## 4.4 Montagem de routers

### app-curadoria/main.py
```python
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=["*"])
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(health.router)
app.include_router(curadoria.router)
```

### app-redator/main.py
```python
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=["*"])
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(export.router)       # ANTES de projects — rotas literais primeiro
app.include_router(projects.router)     # catch-all /{project_id} depois
app.include_router(generation.router)
app.include_router(approval.router)
app.include_router(translation.router)
app.include_router(health.router)
# SPA: monta frontend antigo se dist/ existe (VER SEÇÃO 11B)
```

### app-editor/main.py
```python
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=["*"])
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(edicoes.router)
app.include_router(letras.router)
app.include_router(pipeline.router)
app.include_router(health.router)
app.include_router(importar.router)
app.include_router(dashboard.router)
app.include_router(reports.router)
app.include_router(auth.router)
app.include_router(admin_perfil.router)
```

---

# SEÇÃO 5 — FRONTEND COMPLETO

## 5.1 Sistema de rotas
Ver Seção 1.2 — **28 rotas** total.

## 5.2 Navegação principal

**Arquivo:** `app-portal/components/app-sidebar.tsx` (135 linhas)

```typescript
const tools: ToolSection[] = [
  { id: "curadoria", label: "Curadoria", icon: Search, items: [
      { label: "Dashboard", href: "/curadoria", icon: LayoutDashboard },
      { label: "Downloads", href: "/curadoria/downloads", icon: Download },
  ]},
  { id: "redator", label: "Redator de Conteúdo", icon: PenTool, items: [
      { label: "Projetos", href: "/redator", icon: ListPlus },
      { label: "Novo Projeto", href: "/redator/novo", icon: FileText },
  ]},
  { id: "editor", label: "Editor de Vídeo", icon: Film, items: [
      { label: "Fila de Edicao", href: "/editor", icon: ListOrdered },
  ]},
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard, items: [
      { label: "Visão Geral", href: "/dashboard", icon: LayoutDashboard },
      { label: "Saúde", href: "/dashboard/saude", icon: HardDrive },
      { label: "Produção", href: "/dashboard/producao", icon: ListOrdered },
      { label: "Reports", href: "/dashboard/reports", icon: FileText },
  ]},
  { id: "admin", label: "Administração", icon: ShieldCheck, adminOnly: true, items: [
      { label: "Marcas / Perfis", href: "/admin/marcas", icon: Globe },
      { label: "Usuários", href: "/admin/usuarios", icon: User },
  ]},
]
```

- Sem separação visual por marca na sidebar
- Sem badges/contadores em itens de menu
- Admin filtrado por `isAdmin`
- Expandido por clique no grupo

## 5.3 Componentes de listagem

### a) Curadoria Dashboard
**Arquivo:** `components/curadoria/dashboard.tsx` (~419 linhas)
- **API:** `curadoriaApi.searchCategory()`, `.search()`, `.ranking()`, `.playlistVideos()`
- **Campos exibidos:** thumbnail, artist, song, score (ScoreRing), views, year, HD, duration
- **Filtros:** hide_posted toggle, category selection dropdown
- **Busca:** input text → `curadoriaApi.search()`
- **Paginação:** NÃO — carrega tudo de uma vez
- **Separação por marca:** via `brand_slug` no query param (vem do BrandContext)

### b) Redator Project List
**Arquivo:** `components/redator/project-list.tsx` (~290 linhas)
- **API:** `redatorApi.listProjects(brand_slug)`
- **Campos exibidos:** artist/work, composer, category, status, overlay/post/youtube approval badges, brand sigla
- **Filtros:** 3 views (Em andamento, Prontos p/ Exportar, R2)
- **Busca:** NÃO
- **Ordenação:** NÃO (ordem do backend — created_at DESC implícito)
- **Paginação:** NÃO
- **Separação por marca:** via brand_slug (filtrado no backend)
- **Ações:** multi-select, bulk delete

### c) Editor Editing Queue
**Arquivo:** `components/editor/editing-queue.tsx` (~812 linhas)
- **API:** `editorApi.listarEdicoes()`
- **Campos exibidos:** artista/musica, compositor, opera, status, duration, brand badge, passo_atual
- **Filtros:** active vs completed (hardcoded in component)
- **Busca:** NÃO
- **Ordenação:** NÃO (ordem do backend)
- **Paginação:** NÃO
- **Separação por marca:** via perfil_id (filtrado no backend)
- **Ações:** import from redator, create manual, upload overlays, clear, delete

### d) Outras listagens
- **Dashboard Visão Geral:** `editorApi.dashboardVisaoGeral()` — cards com resumo + lista de edições
- **Dashboard Reports:** `editorApi.listarReports()` — lista de reports com filtro tipo/prioridade
- **Curadoria Downloads:** `curadoriaApi.downloads()` — lista de vídeos baixados

## 5.4 Componentes de detalhe

### a) Redator — Approve Overlay
- Exibe array de overlays `{ timestamp, text }`
- Edição inline de texto e timestamp
- Character count (max 70)
- Regenerar com prompt customizado
- Ação: aprovar → POST approve-overlay → redirect para /post

### b) Redator — Approve Post
- Exibe post_text com character count (optimal 1600-2200)
- Edição inline
- Regenerar com prompt customizado
- Ação: aprovar → POST approve-post → redirect para /youtube (BO) ou /automation (RC)

### c) Redator — Approve YouTube
- Exibe youtube_title e youtube_tags
- Edição inline
- Regenerar com prompt customizado
- Ação: aprovar → PUT approve-youtube → marca export_ready se todas aprovadas

### d) Redator — Export
- Tradução automática para todos idiomas
- Download ZIP ou export to folder/R2
- Link para "Importar no Editor"

### e) Editor — Overview
- Status pipeline completo
- Links para cada etapa (letra, alinhamento, conclusão)
- Botão desbloquear se preso

### f) Editor — Conclusion
- Lista de renders por idioma
- Download individual ou pacote ZIP
- Export para pasta

## 5.5 Camada API do frontend

**Completa na Seção 1.2 e aqui:**

### base.ts (126 linhas)
```typescript
const PROD_URLS = {
  curadoria: "https://curadoria-backend-production.up.railway.app",
  redator:   "https://app-production-870c.up.railway.app",
  editor:    "https://editor-backend-production.up.railway.app",
}

// resolveUrl: env var > PROD_URLS (production) > localhost (dev)
// request<T>: fetch + Bearer token + timeout(30s) + 401 logout
// requestFormData<T>: multipart upload
```

### curadoria.ts — 17 funções (ver Seção 4.1)
### redator.ts — 28 funções (ver Seção 4.2)
### editor.ts — 52 funções (ver Seção 4.3)

## 5.6 Estado

- **AuthContext:** user, isAdmin, login(token), logout
- **BrandContext:** selectedBrand, setSelectedBrand, savedBrandId
- **Persistência:** `localStorage.bo_auth_token`, `localStorage.selectedBrandId`
- **Sem Redux/Zustand** — Context API puro
- **Polling:** `useAdaptivePolling` (3s fast → 15s slow depois de 2min)

## 5.7 Notificação/Feedback

- **Toast:** Sonner `<Toaster position="top-right" richColors closeButton />`
- **Loading:** Loader2 spinner + skeleton pulses + disabled buttons
- **Empty state:** Cards com ícone + mensagem + CTA
- **Erro:** Alert banners vermelho + toast.error
- **Status:** `StatusBadge` com dot colorido + texto

---

# SEÇÃO 6 — FLUXO DO OPERADOR

## 6.1 Início → Curadoria

1. Operador abre app → `/` redireciona para `/curadoria`
2. Vê dashboard com categorias, busca, playlist
3. Seleciona marca no BrandSelector (header)
4. Busca por categoria ou texto → grid de vídeos
5. Clica em vídeo → modal com detalhes + score breakdown
6. Dois botões: "Download local" ou "Preparar para Edição"
7. "Preparar" → `POST /prepare-video/{id}` → download + R2 upload
8. Sucesso → toast "Vídeo pronto no R2"
9. **NÃO há redirect automático** — operador deve ir manualmente ao Redator

## 6.2 Curadoria → Redação

1. Operador navega para `/redator/novo`
2. Preenche URL do YouTube ou seleciona de "Prontos no R2"
3. Detecção automática de metadados (Claude Vision)
4. Cria projeto → redirect para lista de projetos
5. **PONTO DE FRICÇÃO:** projeto recém-criado não é destacado na lista

## 6.3 Redação (pipeline)

### Best of Opera (BO):
1. `/redator/projeto/[id]/overlay` → gerar + aprovar overlays
2. `/redator/projeto/[id]/post` → gerar + aprovar post
3. `/redator/projeto/[id]/youtube` → gerar + aprovar título/tags
4. `/redator/projeto/[id]/exportar` → traduzir + exportar

### Reels Classics (RC):
1. Research → gerar pesquisa profunda
2. Hooks → gerar 5 hooks → selecionar 1
3. Overlay → gerar overlays a partir do hook
4. Post → gerar post
5. Automation → gerar + aprovar automation data
6. Export → traduzir + exportar

### Navegação entre etapas:
- Links na lista de projetos apontam para próxima etapa baseada em flags de aprovação
- **NÃO há stepper visual** (pipeline-stepper.tsx existe mas **nunca é importado**)

## 6.4 Redação → Editor

1. Na tela de exportação, operador clica "Exportar para R2" ou "Exportar para Pasta"
2. Depois vai manualmente para `/editor`
3. Na editing queue, clica "Importar do Redator"
4. Seleciona projeto na lista → modal de idioma (se necessário)
5. `POST /redator/importar/{id}` → cria edição no editor
6. **NÃO há redirect automático do redator para o editor**

## 6.5 Editor (pipeline)

1. Edição criada com status `aguardando`
2. Download automático do vídeo (cascata: R2 local → R2 curadoria → cobalt → yt-dlp)
3. Letra: transcrição automática (Gemini) ou busca (Genius)
4. Alinhamento: sincronização de legendas com áudio
5. Corte: definição da janela de 60-90s
6. Tradução: lyrics para todos idiomas
7. Render: FFmpeg com overlays + lyrics + traducao (.ASS)
8. Preview → aprovação
9. Pacote ZIP para download

## 6.6 Pós-Editor

- **NÃO existe** tela de "finalizados" — edições concluídas ficam na mesma lista
- Operador volta manualmente para curadoria para próximo vídeo
- **NÃO há ciclo/loop automatizado**

## 6.7 Pontos de fricção

| # | Ponto | Onde | Severidade |
|---|-------|------|-----------|
| 1 | Sem redirect curadoria → redator | Após prepare-video | ALTA |
| 2 | Sem redirect redator → editor | Após exportação | ALTA |
| 3 | Sem highlight de "recém-criado" | Lista do redator | MÉDIA |
| 4 | Sem busca por texto nas listas | Redator + Editor | MÉDIA |
| 5 | Sem ordenação configurável | Todas as listas | MÉDIA |
| 6 | Sem paginação | Todas as listas | BAIXA (poucos projetos) |
| 7 | Sem stepper visual no redator | Fluxo de aprovação | MÉDIA |
| 8 | Sem separação visual ativo/concluído | Fila do editor | MÉDIA |
| 9 | Sem conceito de "fila" priorizada | Todas as apps | ALTA |
| 10 | Sem dashboard centralizado | Navegação geral | ALTA |
| 11 | Sem calendário de produção | Planejamento | ALTA |
| 12 | Sem notificação de conclusão | Render terminado | MÉDIA |

---

# SEÇÃO 7 — ESTADO DE ORGANIZAÇÃO ATUAL

## 7.1 Como projetos são organizados

### Curadoria
- Lista única por resultado de busca — sem persistência de "fila"
- Ordenação: por score (V7) descendente
- Filtros: hidePosted, category
- Sem busca por texto livre
- Sem agrupamento visual

### Redação
- Lista única filtrada por brand_slug
- 3 views por status: em_andamento, export_ready, r2_available
- Sem busca por texto
- Sem ordenação manual
- Projetos antigos se misturam com novos
- **Conceito de "completado":** status = export_ready (mas continua na lista)

### Editor
- Lista única filtrada por perfil_id
- Sem conceito de "fila" — todas edições aparecem juntas
- Sem separação clara active/completed (feito no componente com filter)
- Sem ordenação manual

## 7.2 Conceitos que existem ou faltam

| Conceito | Existe? | Onde/Detalhes |
|----------|---------|---------------|
| Dashboard/home | Sim | `/dashboard` — visão geral, saúde, produção, reports |
| Calendário/agenda | **NÃO** | — |
| Prioridade | **NÃO** | Sem campo priority em nenhum modelo |
| Tags/labels | **NÃO** | Apenas `category` (fixo, não editável) |
| Busca global | **NÃO** | Busca existe apenas na curadoria (YouTube) |
| Status pipeline | Sim | status_badge.tsx com cores por status |
| Contadores | **Parcial** | Dashboard tem contadores, sidebar NÃO |

---

# SEÇÃO 8 — PADRÕES TÉCNICOS

## 8.1 Frontend

| Item | Valor |
|------|-------|
| Framework | Next.js 16.1.6 |
| React | 19.2.3 |
| TypeScript | 5.x |
| CSS | Tailwind CSS 4 |
| Componentes UI | shadcn/ui (Radix primitives) |
| Icons | Lucide React 0.564.0 |
| Toast | Sonner 2.0.7 |
| Fetch | Native fetch() com wrapper custom |
| State | React Context API |
| Monitoring | Sentry/Next.js 8.0.0 |

## 8.2 Backends

| Item | Curadoria | Redator | Editor |
|------|-----------|---------|--------|
| Python | 3.11 | 3.11 | 3.11 |
| FastAPI | 0.115.0 | 0.115.6 | 0.109.0 |
| SQLAlchemy | — (raw SQL) | 2.0.36 (Mapped[T]) | 2.0.25 (Column()) |
| DB | PostgreSQL (psycopg3) | PostgreSQL/SQLite | PostgreSQL |
| Async | async def + psycopg pool | sync endpoints | async def + worker |
| HTTP | httpx 0.27.2 | requests 2.31 | httpx 0.26.0 |
| Auth | Password in query param | Nenhuma | JWT (python-jose) |
| AI | — | Anthropic 0.42.0 (Claude) | Google GenAI 0.8.0 (Gemini) |
| Translate | — | Google Translate API | Google Translate API |
| Monitoring | Sentry | Sentry | Sentry |

## 8.3 Comunicação inter-apps

```
app-portal ──HTTP──► curadoria (port 8002)
app-portal ──HTTP──► redator   (port 8000)
app-portal ──HTTP──► editor    (port 8001)

curadoria  ──HTTP──► editor    (GET /admin/perfis/{slug}/curadoria-config)
redator    ──HTTP──► editor    (GET /admin/perfis/{slug}/redator-config)
editor     ──HTTP──► redator   (GET /api/projects/{id} para importação)
editor     ──HTTP──► curadoria (futuro)
```

**URLs configuradas via env vars:** `EDITOR_API_URL`, `REDATOR_API_URL`, `CURADORIA_API_URL`

---

# SEÇÃO 9 — ARMAZENAMENTO

## 9.1 Banco de dados
- **Curadoria:** PostgreSQL (Railway internal) — raw SQL via psycopg3 pool
- **Redator:** PostgreSQL (prod) / SQLite (dev) — SQLAlchemy ORM
- **Editor:** PostgreSQL (Railway) — SQLAlchemy ORM
- **Cada app tem banco SEPARADO**

## 9.2 Armazenamento de arquivos

**Cloudflare R2** via `shared/storage_service.py`:
```
{r2_prefix}/{Artista} - {Musica}/
├── video/
│   ├── original.mp4
│   ├── audio_completo.ogg
│   ├── video_cortado.mp4
│   └── .youtube_id (marker)
├── {Artista} - {Musica} - EN/
│   ├── final.mp4
│   ├── post.txt
│   ├── subtitles.srt
│   └── youtube.txt
└── export/
    └── pacote.zip
```

**Prefixos:** BO → `editor/`, RC → `reels-classics/`
**URLs:** presigned URLs com expiração (não públicas)

## 9.3 Configuração

**Env vars críticas:** R2_ENDPOINT, R2_ACCESS_KEY, R2_SECRET_KEY, R2_BUCKET, DATABASE_URL (x3), ANTHROPIC_API_KEY, GEMINI_API_KEY, GOOGLE_TRANSLATE_API_KEY, GENIUS_API_TOKEN, YOUTUBE_API_KEY, SECRET_KEY (JWT), SENTRY_DSN (x3)

---

# SEÇÃO 10 — INVENTÁRIO DE PROBLEMAS CONHECIDOS

## 10.1 TODOs/FIXMEs no código
**0 encontrados** em arquivos Python e TypeScript. Codebase limpo.

## 10.2 Prints de diagnóstico

| Arquivo | Tipo | Qtd |
|---------|------|-----|
| `app-redator/backend/routers/generation.py` | `print("[PRINT TEST]...")` | 8 |
| `app-redator/backend/services/claude_service.py` | `print(...)` | 23 |
| `app-editor/backend/app/routes/pipeline.py` | `logger.info("[DIAG]...")` | ~15 |
| `app-editor/backend/app/main.py` | `print(...)` | ~5 |

## 10.3 try/except genéricos

**~60 ocorrências de `except Exception`** distribuídas:
- `app-editor/backend/app/routes/pipeline.py` — 34 (maior concentração)
- `app-curadoria/backend/database.py` — 4 (DDL migrations — aceitável)
- `app-curadoria/backend/routes/curadoria.py` — 3
- `app-editor/backend/app/main.py` — 2
- Restante espalhado em services

**14 ocorrências de `except ... pass` (engolindo erros silenciosamente):**
- `shared/storage_service.py:115`
- `app-curadoria/backend/database.py:86,93,129,136` (DDL — aceitável)
- `app-curadoria/backend/routes/curadoria.py:273,486,716`
- `app-curadoria/backend/services/download.py:60,211`
- `app-curadoria/backend/services/youtube.py:173,198`
- `app-editor/backend/app/main.py:751,841`

## 10.4 Timeouts hardcoded

| Contexto | Valor | Arquivo |
|----------|-------|---------|
| Frontend default | 30s | `base.ts:61` |
| Frontend generate | 90s | `redator.ts:141` |
| Frontend RC research | 180s | `redator.ts:179` |
| Frontend RC hooks/overlay/post | 120s | `redator.ts:181-192` |
| Frontend translate | 180s | `redator.ts:197` |
| Frontend aplicar-corte | 120s | `editor.ts:311` |
| Backend FFmpeg render | 600s | `pipeline.py:~2034` |
| Backend Gemini transcription | 120-300s | `services/gemini.py` |
| Backend Google Translate | 180s | `pipeline.py:~1472` |
| Backend Cobalt download | 300s | `pipeline.py` |
| Backend yt-dlp download | 300s | `pipeline.py` |

## 10.5 Endpoints sem paginação

**NENHUM endpoint de listagem implementa paginação limit/offset:**
- `GET /api/projects` (redator) — retorna todos
- `GET /edicoes` (editor) — retorna todos (filtro por perfil_id apenas)
- `GET /reports` (editor) — retorna todos
- `GET /api/ranking` (curadoria) — retorna todos

**Risco:** Baixo atualmente (poucas centenas de registros), mas escalará.

---

# SEÇÃO 11 — ANÁLISE FORENSE DE CÓDIGO

## 11A — CÓDIGO MORTO

### 11A.4 Ghost Endpoints (16 total)

#### Curadoria (6 ghost)

| # | Endpoint | Path | Arquivo:Linha | Prova de ausência |
|---|----------|------|--------------|-------------------|
| 1 | GET /api/posted | `/api/posted` | `curadoria.py:~195` | grep "posted" em app-portal/ → 0 matches para endpoint path |
| 2 | GET /api/posted/check | `/api/posted/check` | `curadoria.py:~204` | grep "posted/check" em app-portal/ → 0 matches |
| 3 | POST /api/cache/populate-initial | `/api/cache/populate-initial` | `curadoria.py:~319` | grep "populate-initial" em app-portal/ → 0 matches. Chamado automaticamente no startup |
| 4 | POST /api/cache/refresh-categories | `/api/cache/refresh-categories` | `curadoria.py:~327` | grep "refresh-categories" em app-portal/ → 0 matches |
| 5 | POST /api/playlist/download-all | `/api/playlist/download-all` | `curadoria.py:~360` | grep "download-all" em app-portal/ → 0 matches |
| 6 | GET /api/playlist/download-status | `/api/playlist/download-status` | `curadoria.py:~394` | grep "download-status" em app-portal/ → 0 matches |

**Nota:** Endpoints 3-4 são usados internamente no startup. Endpoints 5-6 parecem restos de feature de bulk download abandonada. Endpoints 1-2 são utilitários sem UI.

#### Editor (8 ghost)

| # | Endpoint | Path | Arquivo:Linha | Prova de ausência |
|---|----------|------|--------------|-------------------|
| 7 | GET /dashboard/stats | `/dashboard/stats` | `dashboard.py:~28` | grep "dashboard/stats" em app-portal/ → 0 matches |
| 8 | GET /dashboard/edicoes-recentes | `/dashboard/edicoes-recentes` | `dashboard.py:~101` | grep "edicoes-recentes" em app-portal/ → 0 matches |
| 9 | GET /dashboard/fila | `/dashboard/fila` | `dashboard.py:~158` | grep "dashboard/fila" em app-portal/ → 0 matches |
| 10 | GET /dashboard/pipeline | `/dashboard/pipeline` | `dashboard.py:~171` | grep "dashboard/pipeline" em app-portal/ → 0 matches |
| 11 | GET /admin/perfis/{id}/curadoria-config | inter-app | `admin_perfil.py:~510` | **INTER-APP** — chamado por curadoria via HTTP |
| 12 | GET /admin/perfis/template-bo | `/template-bo` | `admin_perfil.py:~245` | grep "template-bo" em app-portal/ → 0 matches |
| 13 | POST /edicoes/{id}/limpar-traducoes | `/limpar-traducoes` | `pipeline.py:~1592` | grep "limpar-traducoes" em app-portal/ → 0 matches |
| 14 | POST /edicoes/{id}/reset-traducao | `/reset-traducao` | `pipeline.py:~1610` | grep "reset-traducao" em app-portal/ → 0 matches |

**Nota:** Endpoint 11 é inter-app (curadoria chama editor). Endpoints 7-10 são dashboard endpoints obsoletos substituídos por visao-geral/saude/producao. Endpoints 13-14 parecem funcionalidade abandonada.

### 11A.5 Componente React nunca renderizado

| Componente | Arquivo | Importado por | Status |
|-----------|---------|---------------|--------|
| `PipelineStepper` | `components/pipeline-stepper.tsx` | **NENHUM .tsx** | MORTO |

**Prova:** grep "pipeline-stepper\|PipelineStepper" em app-portal/ → 0 matches em arquivos .tsx. Referenciado apenas em DESIGN_SYSTEM_GUIDE.md (documentação).

### 11A.6 Diretório potencialmente morto

| App | Diretório | Motivo | Confiança |
|-----|-----------|--------|-----------|
| app-redator | `frontend/dist/` | Substituído por app-portal. Ainda montado como SPA no main.py:83-93 | ALTA |

**Prova:** `app-redator/backend/main.py:83-93`:
```python
FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str): ...
```
Este SPA catch-all pode interferir com rotas da API se `frontend/dist` existir no deploy.

---

## 11B — PADRÕES OBSOLETOS

### 11B.1 Divergência de padrões SQLAlchemy

| Padrão | App | Exemplo |
|--------|-----|---------|
| `Mapped[T]` (SQLAlchemy 2.0+) | **app-redator** | `artist: Mapped[str] = mapped_column(String(255))` |
| `Column()` (SQLAlchemy 1.x) | **app-editor** | `artista = Column(String(300), nullable=False)` |
| Raw SQL (sem ORM) | **app-curadoria** | `c.execute("CREATE TABLE IF NOT EXISTS ...")` |

**Impacto:** Nenhum funcional. Apenas inconsistência de estilo entre apps. Ambos os padrões são válidos no SQLAlchemy 2.0.

### 11B.2 Frontend antigo do redator

**Arquivo:** `app-redator/backend/main.py:83-93`

O redator monta um SPA antigo (`frontend/dist/`) com catch-all route `/{full_path:path}`. Se esse diretório existir no container Railway, TODAS as rotas não-API são capturadas pelo SPA catch-all, incluindo potenciais conflitos com novos endpoints.

**Risco:** MÉDIO — depende se `frontend/dist/` existe no container de produção.

### 11B.3 Debug prints em produção

8 `print("[PRINT TEST]...")` em `app-redator/backend/routers/generation.py` e 23 `print(...)` em `app-redator/backend/services/claude_service.py`. Commits recentes confirmam que são diagnósticos intencionais para RC, mas poluem stdout.

---

## 11C — LÓGICA INCORRETA

### 11C.1 Condições mortas
**0 encontradas** com prova dupla. Condicionais são baseadas em input externo (API params, DB state).

### 11C.2 Comparações suspeitas

| Arquivo | Padrão | Status |
|---------|--------|--------|
| **Todos os backends** | `is None` | Correto — grep confirma 0 ocorrências de `== None` |

### 11C.3 Tratamento de erro que esconde bugs

**14 ocorrências de `except ... pass`** (listadas na Seção 10.3).

As mais preocupantes:
1. `shared/storage_service.py:115` — silencia erro ao verificar existência de arquivo no R2. Se R2 retornar erro de permissão, o código trata como "arquivo não existe" silenciosamente.
2. `app-curadoria/backend/routes/curadoria.py:273,486,716` — silencia erros em operações de cache/download. Pode mascarar falhas de R2.

### 11C.4 Race conditions

**Worker do editor** (`worker.py`):
- `_current_task_edicao_id` é variável global mutável
- Protegida por execução sequencial (asyncio.Queue single consumer)
- **NÃO há lock** — se por algum motivo 2 loops rodarem (bug no startup), conflito
- **Risco:** BAIXO — arquitetura previne via single consumer pattern

### 11C.5 Defaults perigosos

| Modelo | Campo | Default | Correto? |
|--------|-------|---------|----------|
| Edicao | `progresso_detalhe` | `dict` (mutable!) | **RISCO** — `default=dict` em SQLAlchemy Column pode compartilhar instância |
| Perfil | `idiomas_alvo` | `lambda: [...]` | Correto — lambda previne sharing |
| Perfil | múltiplos JSON | `dict` / `list` | **RISCO** — mesma questão de mutable defaults |

**Nota:** SQLAlchemy 2.0 lida melhor com mutable defaults que 1.x, mas o editor usa Column() (1.x style). Em prática o SQLAlchemy cria cópia no commit, então o risco é teórico.

---

## 11D — CONSISTÊNCIA E INTEGRIDADE

### 11D.1 Contratos API (Frontend vs Backend)

**Geralmente consistentes.** Os maiores riscos:

| Frontend (arquivo:função) | Backend (endpoint) | Discrepância |
|---------------------------|-------------------|-------------|
| `editor.ts:atualizarPerfilParcial` (PATCH) | `admin_perfil.py` | Frontend define PATCH, backend pode não implementar PATCH separado do PUT |
| `editor.ts:ProgressoDetalhe` (type union) | `edicao.py:progresso_detalhe` (JSON) | Frontend aceita formato antigo E novo — compat layer no frontend |

### 11D.2 Nomes inconsistentes entre camadas

| Conceito | Curadoria | Redator | Editor | Frontend |
|----------|-----------|---------|--------|----------|
| Nome da música | `song` | `work` | `musica` | Usa o de cada API |
| Artista | `artist` | `artist` | `artista` | Idem |
| Compositor | — | `composer` | `compositor` | Idem |
| Status concluído | — | `export_ready` | `concluido` | Cada um diferente |
| Brand | `brand_slug` | `brand_slug` | `perfil_id` | `brand_slug` ou `perfil_id` conforme API |

### 11D.3 Estratégias de autenticação divergentes

| App | Método | Detalhes |
|-----|--------|---------|
| Curadoria | Password in query param | `POST /api/auth?password=X` — sem token, sem sessão |
| Redator | **Nenhuma** | Endpoints públicos — sem auth |
| Editor | JWT Bearer token | Login → token → header Authorization |
| Frontend | JWT via localStorage | `bo_auth_token` — enviado para todos os backends |

**Risco:** ALTO — o redator aceita qualquer request sem autenticação. O frontend envia token JWT para todos, mas redator ignora.

### 11D.4 Referências cruzadas órfãs

| Relação | Verificação de integridade | Risco |
|---------|---------------------------|-------|
| editor.redator_project_id → redator.projects.id | NÃO — se projeto deletado no redator, editor mantém ID | MÉDIO |
| editor.curadoria_video_id → curadoria.cached_videos | NÃO — campo opcional, sem verificação | BAIXO |
| Deletar no redator → limpar no editor? | NÃO — sem cascade entre apps | MÉDIO |

### 11D.5 Timeout mismatch (frontend vs backend)

| Operação | Frontend | Backend | Match? |
|----------|----------|---------|--------|
| Request default | 30s | Sem limite | **NÃO** — backend pode processar além do timeout do frontend |
| FFmpeg render | 30s (default!) | 600s | **NÃO** — render SEMPRE excede 30s. Frontend usa polling, não espera |
| Generate (redator) | 90s | ~60s Claude | OK |
| Translate | 180s | 180s | OK |
| Aplicar corte | 120s | 120s | OK |

**Nota:** Para renders, o frontend dispara POST e depois faz polling via `useAdaptivePolling`. O mismatch não causa problema funcional porque o frontend não espera a resposta do render — apenas confirma que a task foi enfileirada.

---

# SEÇÃO 11 — RESUMO FORENSE

## 11.RESUMO.1 — Código morto confirmado (seguro remover)

| # | Item | Arquivo | Prova |
|---|------|---------|-------|
| 1 | Frontend antigo SPA catch-all | `app-redator/backend/main.py:83-93` | Substituído por app-portal |
| 2 | PipelineStepper component | `app-portal/components/pipeline-stepper.tsx` | 0 imports em .tsx |
| 3 | GET /dashboard/stats | `app-editor/backend/app/routes/dashboard.py:~28` | 0 chamadas frontend |
| 4 | GET /dashboard/edicoes-recentes | `dashboard.py:~101` | 0 chamadas |
| 5 | GET /dashboard/fila | `dashboard.py:~158` | 0 chamadas |
| 6 | GET /dashboard/pipeline | `dashboard.py:~171` | 0 chamadas |
| 7 | POST /limpar-traducoes | `pipeline.py:~1592` | 0 chamadas |
| 8 | POST /reset-traducao | `pipeline.py:~1610` | 0 chamadas |
| 9 | GET /template-bo | `admin_perfil.py:~245` | 0 chamadas |

## 11.RESUMO.2 — Código morto provável (requer confirmação)

| # | Item | Arquivo | Motivo da incerteza |
|---|------|---------|---------------------|
| 1 | GET /api/posted | `curadoria.py:~195` | Pode ser usado por script externo |
| 2 | GET /api/posted/check | `curadoria.py:~204` | Idem |
| 3 | POST /cache/populate-initial | `curadoria.py:~319` | Usado no startup automaticamente |
| 4 | POST /cache/refresh-categories | `curadoria.py:~327` | Pode ser chamado manualmente via curl |
| 5 | POST /playlist/download-all | `curadoria.py:~360` | Feature incompleta ou removida? |
| 6 | GET /playlist/download-status | `curadoria.py:~394` | Idem |
| 7 | POST /quota/register | `curadoria.py:~406` | Usado internamente pelas funções de busca |

## 11.RESUMO.3 — Padrões obsoletos por prioridade

| Prioridade | Padrão | Ação |
|-----------|--------|------|
| ALTO | Frontend antigo do redator no main.py | Remover SPA catch-all |
| ALTO | 8 print("[PRINT TEST]") em production | Converter para logger ou remover |
| MÉDIO | 14 except...pass silenciosos | Adicionar logging |
| MÉDIO | Column() vs Mapped[T] divergência | Cosmético — não mexer |
| BAIXO | session.query() em todo o editor | Funcional — não mexer |

## 11.RESUMO.4 — Bugs lógicos confirmados

| Sev | Bug | Arquivo | Prova |
|-----|-----|---------|-------|
| MÉDIO | Redator sem autenticação | Todos endpoints redator | Nenhum middleware auth |
| MÉDIO | `except pass` em storage_service | `shared/storage_service.py:115` | Mascara erros de permissão R2 |
| BAIXO | Mutable default `dict` em Column | `models/edicao.py:53` | Teórico — SQLAlchemy mitiga |

## 11.RESUMO.5 — Inconsistências entre camadas (Top 10)

| # | Inconsistência | Risco |
|---|---------------|-------|
| 1 | 3 estratégias de auth (password/none/JWT) | ALTO |
| 2 | Nomes diferentes (song/work/musica, artist/artista) | BAIXO (frontend adapta) |
| 3 | Status em português (editor) vs inglês (redator) | BAIXO (cada um consistente consigo) |
| 4 | Sem cascade delete entre apps | MÉDIO |
| 5 | Frontend timeout 30s default vs backend sem limite | BAIXO (polling compensa) |
| 6 | 3 prefixos de API (/api/, /api/v1/editor/, /health) | BAIXO (cosmético) |
| 7 | brand_slug (curadoria/redator) vs perfil_id (editor) | BAIXO (frontend mapeia) |
| 8 | SPA catch-all no redator pode conflitar com novas rotas | MÉDIO |
| 9 | Sem paginação em nenhuma listagem | BAIXO (escala futura) |
| 10 | Debug prints em produção (31 prints no redator) | BAIXO |

## 11.RESUMO.6 — Mapa de zonas

| Zona | Diretório/Arquivo | Avaliação |
|------|-------------------|-----------|
| VERDE | `app-portal/lib/api/*` | Estável, bem abstraído, tipos TS |
| VERDE | `app-portal/components/ui/*` | shadcn — framework-managed |
| VERDE | `shared/storage_service.py` | Bem testado, retry, fallback |
| VERDE | `app-editor/backend/app/worker.py` | Pattern sólido, recovery |
| AMARELA | `app-editor/backend/app/routes/pipeline.py` | 3000 linhas, 34 except, funcional mas denso |
| AMARELA | `app-curadoria/backend/routes/curadoria.py` | 742 linhas, 6 ghost endpoints, 3 except pass |
| AMARELA | `app-redator/backend/main.py` | SPA catch-all + sem auth |
| AMARELA | `app-portal/components/editor/editing-queue.tsx` | 812 linhas, UI complexa |
| VERDE | `app-editor/backend/app/models/*` | Modelos claros, bem definidos |
| VERDE | `app-portal/lib/auth-context.tsx` | Gestão de auth robusta |

---

# RESUMO EXECUTIVO GERAL

## Totais

| Métrica | Valor |
|---------|-------|
| Rotas frontend | **28** (23 protegidas + 2 públicas + 3 admin) |
| Endpoints curadoria | **27** (6 ghost) |
| Endpoints redator | **34** (0 ghost) |
| Endpoints editor | **~70** (8 ghost, 2 inter-app) |
| **Total endpoints** | **~131** |
| Tabelas curadoria | 6 |
| Tabelas redator | 2 |
| Tabelas editor | 11 |
| **Total tabelas** | **19** |

## Fluxo do operador

```
┌──────────┐    manual    ┌──────────┐    manual    ┌──────────┐
│CURADORIA │ ──────────►  │ REDATOR  │ ──────────►  │  EDITOR  │
│          │              │          │              │          │
│ Buscar   │              │ Criar    │              │ Importar │
│ Avaliar  │              │ Gerar    │              │ Download │
│ Preparar │              │ Aprovar  │              │ Alinhar  │
│          │              │ Traduzir │              │ Render   │
│          │              │ Exportar │              │ Pacote   │
└──────────┘              └──────────┘              └──────────┘
     ▲                                                    │
     └────────── operador volta manualmente ──────────────┘
```

## TOP 10 Pontos de Fricção

1. **Sem redirect automático entre etapas** (curadoria→redator→editor)
2. **Sem dashboard centralizado** com visão cross-app
3. **Sem calendário de produção**
4. **Sem fila priorizada** em nenhuma app
5. **Sem busca por texto** nas listas do redator/editor
6. **Sem stepper visual** no fluxo de aprovação do redator
7. **Sem separação clara ativo/concluído** na fila do editor
8. **Sem contadores na sidebar** (quantos pendentes?)
9. **Sem notificação de conclusão** (render terminou)
10. **Sem ordenação configurável** nas listas

## TOP 5 Dados Faltantes para Features Planejadas

1. **Campo `priority`** — não existe em nenhum modelo (necessário para fila priorizada)
2. **Campo `scheduled_date`** — não existe (necessário para calendário)
3. **Campo `stage` unificado** — cada app tem status independente (necessário para pipeline cross-app)
4. **Tabela de `workflow_events`** — não existe (necessário para tracking de tempo/histórico)
5. **Campo `tags`** — não existe (necessário para organização/busca)

## TOP 10 Achados Forenses

1. **Redator sem autenticação** — endpoints públicos
2. **Frontend antigo do redator** montado como SPA catch-all (pode conflitar)
3. **14 except...pass** silenciando erros em produção
4. **8 print("[PRINT TEST]")** no redator em produção
5. **16 ghost endpoints** (código morto no backend)
6. **PipelineStepper** — componente criado mas nunca usado
7. **Sem cascade delete** entre apps (órfãos possíveis)
8. **3 estratégias de auth diferentes** entre backends
9. **Mutable defaults** em Column() do SQLAlchemy 1.x
10. **Timeout mismatch** frontend 30s vs backend 600s (mitigado por polling)

## Recomendações Pré-Implementação

Antes de implementar novas features, resolver:

1. **Remover SPA catch-all do redator** (`main.py:83-93`) — risco de conflito
2. **Remover/converter prints de diagnóstico** do redator para logger
3. **Adicionar auth ao redator** (ou pelo menos Bearer token check)
4. **Remover ghost endpoints** (16 endpoints mortos) — reduzir superfície
5. **Remover PipelineStepper** ou integrá-lo ao fluxo do redator
6. **Adicionar logging** aos 14 `except...pass` mais críticos
7. **Padronizar prefixos de API** (todos `/api/v1/` ou todos `/api/`)
