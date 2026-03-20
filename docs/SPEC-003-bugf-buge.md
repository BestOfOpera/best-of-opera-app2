# SPEC-003 — BUG-F (marca errada) + BUG-E (cached_videos sem brand_slug)
**Data:** 19/03/2026
**Status:** CONCLUÍDO
**Origem:** PRD-003-pendencias-criticas.md — Frentes 2 e 4

---

## Ordem de execução

```
Task 01 (BUG-F backend) → Task 02 (BUG-E schema + funções + callers)
```

---

## Task 01 — BUG-F: filtro de marca na listagem de edições

**Arquivo:** `app-editor/backend/app/routes/edicoes.py`
**Linhas:** 18–32
**Status:** CONCLUÍDO (19/03/2026)
**⚠️ DEPLOY PENDENTE:** `editor-backend` no Railway

### Causa raiz

`perfil_id` é `Optional` no endpoint `GET /edicoes`. Quando o frontend não envia o parâmetro
(ex.: brand ainda não carregada no contexto React), o backend retorna **todas** as edições
de todas as marcas.

### Código atual (bug)

```python
@router.get("/edicoes", response_model=list[EdicaoOut])
def listar_edicoes(
    status: Optional[str] = None,
    categoria: Optional[str] = None,
    perfil_id: Optional[int] = Query(None),  # ← opcional — sem brand retorna tudo
    db: Session = Depends(get_db),
):
    q = db.query(Edicao).order_by(Edicao.id.desc())
    if status:
        q = q.filter(Edicao.status == status)
    if categoria:
        q = q.filter(Edicao.categoria == categoria)
    if perfil_id is not None:
        q = q.filter(Edicao.perfil_id == perfil_id)
    return q.all()  # ← retorna tudo se perfil_id não vier
```

### Fix

Se `perfil_id` não for enviado, retornar lista vazia. Não retornar erro (frontend pode chamar
antes de carregar o contexto de marca — lista vazia é o comportamento correto).

```python
@router.get("/edicoes", response_model=list[EdicaoOut])
def listar_edicoes(
    status: Optional[str] = None,
    categoria: Optional[str] = None,
    perfil_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    if perfil_id is None:
        return []
    q = db.query(Edicao).filter(
        Edicao.perfil_id == perfil_id
    ).order_by(Edicao.id.desc())
    if status:
        q = q.filter(Edicao.status == status)
    if categoria:
        q = q.filter(Edicao.categoria == categoria)
    return q.all()
```

### Critério de done

- Sem `perfil_id`: retorna `[]`
- Com `perfil_id=1`: retorna só edições do perfil 1
- Com `perfil_id=2`: retorna só edições do perfil 2

---

## Task 02 — BUG-E: `cached_videos` sem isolamento por marca

**Arquivo principal:** `app-curadoria/backend/database.py`
**Arquivo secundário:** `app-curadoria/backend/routes/curadoria.py`
**Status:** CONCLUÍDO (19/03/2026)
**⚠️ DEPLOY PENDENTE:** `curadoria-backend` no Railway
**⚠️ Migration pendente no banco antes do deploy** (ver Sub-task 02-A)

### Causa raiz

A tabela `cached_videos` não tem coluna `brand_slug`. As funções `save_cached_videos()` e
`get_cached_videos()` não recebem nem filtram por marca. O `UNIQUE(video_id, category)` não
inclui `brand_slug`, causando conflito silencioso se duas marcas usarem a mesma categoria.

### Sub-task 02-A — Migration (executar no banco de produção)

```sql
-- Adicionar coluna brand_slug com default para não quebrar registros existentes
ALTER TABLE cached_videos
  ADD COLUMN IF NOT EXISTS brand_slug TEXT NOT NULL DEFAULT 'best-of-opera';

-- Atualizar constraint UNIQUE para incluir brand_slug
ALTER TABLE cached_videos DROP CONSTRAINT IF EXISTS cached_videos_video_id_category_key;
ALTER TABLE cached_videos ADD CONSTRAINT cached_videos_video_id_category_brand_key
  UNIQUE (video_id, category, brand_slug);

-- Índice para performance
CREATE INDEX IF NOT EXISTS idx_cached_videos_brand ON cached_videos(brand_slug);
```

**⚠️ Executar no Railway PostgreSQL antes de deployar o código.**

### Sub-task 02-B — `database.py`: atualizar schema CREATE TABLE

O `CREATE TABLE IF NOT EXISTS` já existe no banco após a migration, mas atualizar o código
garante consistência para ambientes novos ou testes.

**Arquivo:** `app-curadoria/backend/database.py` — bloco CREATE TABLE cached_videos

Adicionar `brand_slug TEXT NOT NULL DEFAULT 'best-of-opera'` e atualizar UNIQUE:

```sql
-- ANTES
UNIQUE(video_id, category)

-- DEPOIS
brand_slug TEXT NOT NULL DEFAULT 'best-of-opera',
UNIQUE(video_id, category, brand_slug)
```

### Sub-task 02-C — `database.py`: função `save_cached_videos()`

**Linhas aprox.:** 175–206

```python
# ANTES
def save_cached_videos(videos: List[Dict], category: str):
    ...
    c.execute("DELETE FROM cached_videos WHERE category = %s", (category,))
    for v in videos:
        c.execute("""
            INSERT INTO cached_videos
            (video_id, url, title, artist, song, channel, year, published, duration,
             views, hd, thumbnail, category, score_total, score_fixed, score_guia,
             artist_match, song_match, posted)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (video_id, category) DO UPDATE SET ...
        """, (...))

# DEPOIS
def save_cached_videos(videos: List[Dict], category: str, brand_slug: str = "best-of-opera"):
    ...
    c.execute("DELETE FROM cached_videos WHERE category = %s AND brand_slug = %s", (category, brand_slug))
    for v in videos:
        c.execute("""
            INSERT INTO cached_videos
            (video_id, url, title, artist, song, channel, year, published, duration,
             views, hd, thumbnail, category, score_total, score_fixed, score_guia,
             artist_match, song_match, posted, brand_slug)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (video_id, category, brand_slug) DO UPDATE SET ...
        """, (..., brand_slug))
```

### Sub-task 02-D — `database.py`: função `get_cached_videos()`

**Linhas aprox.:** 209–234

```python
# ANTES
def get_cached_videos(category: str, hide_posted: bool = True) -> List[Dict]:
    ...
    query = "SELECT * FROM cached_videos WHERE category = %s"
    params: list = [category]

# DEPOIS
def get_cached_videos(category: str, hide_posted: bool = True, brand_slug: str = "best-of-opera") -> List[Dict]:
    ...
    query = "SELECT * FROM cached_videos WHERE category = %s AND brand_slug = %s"
    params: list = [category, brand_slug]
```

### Sub-task 02-E — `curadoria.py`: passar `brand_slug` nas chamadas

**Arquivo:** `app-curadoria/backend/routes/curadoria.py`

Todas as chamadas a `save_cached_videos()` e `get_cached_videos()` precisam passar
`brand_slug=config.get("brand_slug") or "best-of-opera"`.

Localizar todas as ocorrências com grep em `curadoria.py` e adicionar o argumento.

### Critério de done — Task 02

- Migration executada sem erro no banco de produção
- `get_cached_videos(category="Opera", brand_slug="best-of-opera")` retorna só vídeos da BO
- `get_cached_videos(category="Opera", brand_slug="reels-classics")` retorna só vídeos da RC
- `save_cached_videos()` não apaga cache de outra marca ao salvar

---

## Arquivos a modificar

| Arquivo | Task | Tipo |
|---|---|---|
| `app-editor/backend/app/routes/edicoes.py` | 01 | Edição — guard `perfil_id is None` |
| `app-curadoria/backend/database.py` | 02-B, 02-C, 02-D | Edição — coluna + funções |
| `app-curadoria/backend/routes/curadoria.py` | 02-E | Edição — passar brand_slug nos callers |

---

## Deploy necessário após execução

| Serviço | Motivo |
|---|---|
| `editor-backend` | Task 01 — filtro de marca em edicoes.py |
| `curadoria-backend` | Task 02 — brand_slug em cached_videos |

**⚠️ Não deployar sem aprovação explícita.**
**⚠️ Task 02: executar migration no banco ANTES de deployar o código.**
