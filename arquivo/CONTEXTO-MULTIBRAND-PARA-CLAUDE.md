# Contexto Multi-Brand — Estado Real do Repo
Gerado em: 2026-03-09

---

## 1. Legendas — Estado Atual

**Arquivo:** `app-editor/backend/app/services/legendas.py`

- **Fonte:** `TeX Gyre Pagella` (usada em todos os 3 tracks)
- **PlayRes:** 1080x1920 (vertical 9:16)

| Track     | fontsize | primarycolor | outlinecolor | outline | shadow | alignment | marginv | bold  | italic |
|-----------|----------|-------------|-------------|---------|--------|-----------|---------|-------|--------|
| Overlay   | 63       | #FFFFFF     | #000000      | 3       | 1      | 2 (bottom-center) | 1296 | True  | False  |
| Lyrics    | 45       | #FFFF64 (amarelo) | #000000 | 2  | 0      | 2 (bottom-center) | 573  | True  | True   |
| Tradução  | 43       | #FFFFFF     | #000000      | 2       | 0      | 8 (top-center) | 1353 | True  | True   |

- **OVERLAY_MAX_CHARS:** 70
- **OVERLAY_MAX_CHARS_LINHA:** 35
- **LYRICS_MAX_CHARS:** 43
- **TRADUCAO_MAX_CHARS:** 100

- **Posicionamento:** Estático com `marginv` fixo por track. Não há cálculo dinâmico — cada track tem um valor fixo de marginv definido em `ESTILOS_PADRAO`. Os estilos são passados como dict e aplicados diretamente ao `pysubs2.SSAStyle`.

- **Funções de formatação de texto:**
  - `_formatar_overlay(texto, max_por_linha=30)` — Quebra overlay em 2 linhas equilibradas, trunca com `...` se exceder
  - `_truncar_texto(texto, max_chars)` — Corta no último espaço antes do limite, adiciona `...`
  - `_formatar_texto_legenda(texto, max_chars=40, max_linhas=2)` — Word-wrap genérico (definida mas não usada no fluxo principal de gerar_ass)
  - `quebrar_texto_overlay(texto, max_chars=70)` — Quebra em 2 linhas equilibradas (definida mas não usada diretamente em gerar_ass)

- **Assinatura de `gerar_ass()`:**
  ```python
  def gerar_ass(
      overlay: list,
      lyrics: list,
      traducao: Optional[list],
      idioma_versao: str,
      idioma_musica: str,
      estilos: dict = None,   # ← JÁ aceita estilos customizados (default=ESTILOS_PADRAO)
      sem_lyrics: bool = False,
  ) -> pysubs2.SSAFile
  ```
  > **Ponto-chave para multi-brand:** O parâmetro `estilos` já existe e permite override completo dos 3 tracks. Hoje ninguém o passa — sempre usa `ESTILOS_PADRAO`.

---

## 2. Pipeline — Como Chama Legendas

**Arquivo:** `app-editor/backend/app/routes/pipeline.py`

### Chamada de `gerar_ass()` (linha 1666):
```python
ass_obj = gerar_ass(
    overlay=d["overlay_segs"] or [],
    lyrics=lyrics_segs or [],
    traducao=d["traducao_segs"],
    idioma_versao=idioma,
    idioma_musica=idioma_musica,
    sem_lyrics=sem_lyrics_val,
)
```
**Nota:** O parâmetro `estilos=` **NÃO** é passado — sempre usa o default `ESTILOS_PADRAO`.

### IDIOMAS_ALVO (definido em `config.py`, importado na linha 24):
```python
IDIOMAS_ALVO = ["en", "pt", "es", "de", "fr", "it", "pl"]
```
São 7 idiomas fixos. Não há mecanismo para customizar por projeto/marca.

### idioma_preview (linha 1868):
```python
idioma_preview = "pt" if edicao.idioma != "pt" else edicao.idioma
```
Lógica: se a música NÃO é em PT, preview em PT (para mostrar tradução). Se já é PT, preview em PT mesmo (sem tradução, pois idioma_versao == idioma_musica).

### perfil_id no código:
**NÃO existe.** Nenhuma referência a `perfil_id`, `PROJECT_ID`, ou qualquer mecanismo de seleção de marca no pipeline de render.

### Parâmetros de `_render_task()`:
```python
async def _render_task(
    edicao_id: int,
    idiomas_renderizar: list = None,
    is_preview: bool = False,
    sem_legendas: bool = False,
)
```

---

## 3. Modelo Edicao — Colunas Existentes

**Arquivo:** `app-editor/backend/app/models/edicao.py`

| Coluna | Tipo | Observação |
|--------|------|-----------|
| id | Integer | PK |
| curadoria_video_id | Integer | nullable |
| youtube_url | String(500) | |
| youtube_video_id | String(20) | |
| artista | String(300) | |
| musica | String(300) | |
| compositor | String(300) | |
| opera | String(300) | |
| categoria | String(50) | |
| idioma | String(10) | idioma da música |
| eh_instrumental | Boolean | default=False |
| sem_lyrics | Boolean | default=False |
| duracao_total_sec | Float | |
| status | String(30) | default="aguardando" |
| passo_atual | Integer | default=1 |
| erro_msg | Text | |
| janela_inicio_sec | Float | |
| janela_fim_sec | Float | |
| duracao_corte_sec | Float | |
| corte_original_inicio | String(20) | |
| corte_original_fim | String(20) | |
| arquivo_video_completo | String(500) | |
| arquivo_video_cortado | String(500) | |
| arquivo_audio_completo | String(500) | |
| arquivo_video_cru | String(500) | |
| rota_alinhamento | String(5) | |
| confianca_alinhamento | Float | |
| r2_base | String(500) | |
| redator_project_id | Integer | |
| notas_revisao | Text | |
| editado_por | String(100) | |
| tempo_edicao_seg | Integer | |
| task_heartbeat | DateTime | |
| progresso_detalhe | JSON | |
| tentativas_requeue | Integer | default=0 |
| created_at | DateTime | server_default=now() |
| updated_at | DateTime | server_default=now(), onupdate |

**Total: 32 colunas.**

**perfil_id: NÃO existe** no modelo. Nenhuma referência a marca/projeto.

---

## 4. Migrations Existentes

**Arquivo:** `app-editor/backend/app/main.py` → `_run_migrations()`

### Colunas adicionadas via migration na tabela `editor_edicoes`:
1. `corte_original_inicio` — VARCHAR(20)
2. `corte_original_fim` — VARCHAR(20)
3. `notas_revisao` — TEXT
4. `r2_base` — VARCHAR(500)
5. `redator_project_id` — INTEGER
6. `task_heartbeat` — TIMESTAMP
7. `progresso_detalhe` — JSON
8. `tentativas_requeue` — INTEGER DEFAULT 0
9. `sem_lyrics` — BOOLEAN DEFAULT FALSE

### Indexes criados:
- `uq_traducao_edicao_idioma` — UNIQUE em `editor_traducoes_letras (edicao_id, idioma)`
- `uq_render_edicao_idioma` — UNIQUE em `editor_renders (edicao_id, idioma)`
- `uix_redator_project_id` — UNIQUE parcial em `editor_edicoes (redator_project_id) WHERE NOT NULL`

### Migrations em `editor_reports`:
- `prioridade` — VARCHAR(20) DEFAULT 'media'
- `resolvido_em` — TIMESTAMP
- `updated_at` — TIMESTAMP

### Tabela `editor_perfis`:
**NÃO existe.** Nenhuma referência a esta tabela.

---

## 5. Config — Variáveis de Ambiente

**Arquivo:** `app-editor/backend/app/config.py`

| Variável | Default | Observação |
|----------|---------|-----------|
| DATABASE_URL | `postgresql://postgres:postgres@localhost:5432/railway` | |
| GEMINI_API_KEY | `""` | |
| GOOGLE_TRANSLATE_API_KEY | `""` | |
| STORAGE_PATH | `/tmp/editor_storage` | |
| MAX_VIDEO_SIZE_MB | `500` | |
| CORS_ORIGINS | `["*"]` | |
| SECRET_KEY | `dev-secret-key-change-in-production` | |
| REDATOR_API_URL | `https://app-production-870c.up.railway.app` | |
| EXPORT_PATH | `""` | |
| CURADORIA_API_URL | `https://curadoria-backend-production.up.railway.app` | |
| GENIUS_API_TOKEN | `""` | |
| SENTRY_DSN | `None` | |
| COBALT_API_URL | `https://api.cobalt.tools` | |

**Constante hardcoded (não env var):**
- `IDIOMAS_ALVO = ["en", "pt", "es", "de", "fr", "it", "pl"]`

**PROJECT_ID: NÃO existe.** Nenhuma variável de ambiente para seleção de marca/projeto.

---

## 6. Dependências Relevantes

**Arquivo:** `app-editor/backend/requirements.txt`

| Pacote | Versão | Instalado? |
|--------|--------|-----------|
| sentry-sdk[fastapi] | >=2.0.0 | **SIM** |
| python-jose | — | **NÃO** |
| passlib | — | **NÃO** |
| pysubs2 | 1.7.2 | SIM (geração ASS) |
| google-generativeai | 0.8.0 | SIM (Gemini) |
| httpx | 0.26.0 | SIM |
| boto3 | >=1.34.0 | SIM (R2/S3) |
| alembic | 1.13.1 | SIM (mas migrations são manuais via _run_migrations) |

---

## 7. Estado Geral (MEMORIA-VIVA)

**Arquivo:** `MEMORIA-VIVA.md`

### Última sessão (2026-03-09): BLAST v3 + Refactor Curadoria

**BLAST v3 — 7 blocos concluídos:**
- Cobalt.tools como 3a fonte de download (cascata: R2 → Cobalt → yt-dlp)
- Worker sequencial para pacote ZIP
- Retry automático de tradução (2 passadas)
- Sentry integrado (opcional via SENTRY_DSN)
- UNIQUE indexes em traduções e renders + upserts
- Progresso com namespaces (render/traducao/pacote)

**Refactor Curadoria — God Object → 11 módulos:**
- `main.py` de 1275 linhas → 52 linhas
- Config por marca via `data/best-of-opera.json` + `load_brand_config()`
- `PROJECT_ID` env var já funciona na Curadoria (seleciona JSON)
- `calc_score_v7(v, category, config)` recebe config como parâmetro

### Status atual do multi-brand:
- **Curadoria:** Parcialmente pronta — `PROJECT_ID` + JSON por marca já funciona
- **Editor:** Zero suporte multi-brand — sem `perfil_id`, sem `PROJECT_ID`, estilos hardcoded em `ESTILOS_PADRAO`
- **Redator:** Não avaliado neste relatório (fora do escopo solicitado)

### Pendências declaradas na MEMORIA-VIVA:
- Nenhuma pendência aberta (todos os blocos BLAST v3 concluídos)

---

## 8. Resumo de Gaps para Multi-Brand (Editor)

| Item | Estado Atual | O que falta |
|------|-------------|-------------|
| Fonte de legendas | Hardcoded `TeX Gyre Pagella` | Parametrizar por perfil |
| Cores/tamanhos | Hardcoded em `ESTILOS_PADRAO` | Override via perfil |
| `gerar_ass(estilos=)` | Parâmetro existe mas nunca usado | Pipeline precisa passar estilos do perfil |
| `IDIOMAS_ALVO` | Hardcoded 7 idiomas | Parametrizar por perfil |
| `perfil_id` no modelo | Não existe | Adicionar coluna + migration |
| Tabela `editor_perfis` | Não existe | Criar tabela |
| `PROJECT_ID` env var | Não existe no Editor | Adicionar em config.py |
| idioma_preview | Hardcoded para PT | Possivelmente configurável por marca |
