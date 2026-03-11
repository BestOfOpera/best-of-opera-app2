"""APP Editor — Best of Opera. Ponto de entrada FastAPI."""
import asyncio
import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import STORAGE_PATH, SENTRY_DSN

logger = logging.getLogger(__name__)

# Sentry — inicializar antes do lifespan para capturar erros de startup
if SENTRY_DSN:
    import sentry_sdk
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        traces_sample_rate=0.1,
        environment="production",
        attach_stacktrace=True,
        server_name="editor-backend",
    )
    logger.info("[sentry] Sentry inicializado")

from app.database import engine, Base
from app.routes import edicoes, letras, pipeline, health, importar, dashboard, reports, auth, admin_perfil


def _run_migrations():
    """Adiciona colunas novas que create_all não cria em tabelas existentes."""
    import json as _json
    from sqlalchemy import text, inspect
    insp = inspect(engine)

    # Migration: tabela editor_perfis + seed do Best of Opera
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS editor_perfis (
                id SERIAL PRIMARY KEY,
                nome VARCHAR(100) UNIQUE NOT NULL,
                sigla VARCHAR(5) NOT NULL,
                slug VARCHAR(50) UNIQUE NOT NULL,
                ativo BOOLEAN DEFAULT TRUE,
                identity_prompt TEXT,
                tom_de_voz TEXT,
                editorial_lang VARCHAR(5) DEFAULT 'pt',
                hashtags_fixas JSON,
                categorias_hook JSON,
                idiomas_alvo JSON,
                idioma_preview VARCHAR(5) DEFAULT 'pt',
                overlay_style JSON,
                lyrics_style JSON,
                traducao_style JSON,
                overlay_max_chars INTEGER DEFAULT 70,
                overlay_max_chars_linha INTEGER DEFAULT 35,
                lyrics_max_chars INTEGER DEFAULT 43,
                traducao_max_chars INTEGER DEFAULT 100,
                video_width INTEGER DEFAULT 1080,
                video_height INTEGER DEFAULT 1920,
                escopo_conteudo TEXT,
                duracao_corte_min INTEGER DEFAULT 30,
                duracao_corte_max INTEGER DEFAULT 90,
                cor_primaria VARCHAR(10) DEFAULT '#1a1a2e',
                cor_secundaria VARCHAR(10) DEFAULT '#e94560',
                r2_prefix VARCHAR(100) DEFAULT 'editor',
                curadoria_categories JSON,
                elite_hits JSON,
                power_names JSON,
                voice_keywords JSON,
                institutional_channels JSON,
                category_specialty JSON,
                scoring_weights JSON,
                curadoria_filters JSON,
                anti_spam_terms VARCHAR(500) DEFAULT '-karaoke -piano -tutorial -lesson -reaction -review -lyrics -chords',
                playlist_id VARCHAR(100) DEFAULT '',
                hook_categories_redator JSON,
                identity_prompt_redator TEXT,
                tom_de_voz_redator TEXT,
                logo_url VARCHAR(500),
                font_name VARCHAR(100),
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """))
        logger.info("Migration: tabela editor_perfis garantida")

        # Seed idempotente do perfil Best of Opera
        overlay_style = _json.dumps({
            "fontname": "TeX Gyre Pagella", "fontsize": 63,
            "primarycolor": "#FFFFFF", "outlinecolor": "#000000",
            "outline": 3, "shadow": 1, "alignment": 2, "marginv": 1296,
            "bold": True, "italic": False,
        })
        lyrics_style = _json.dumps({
            "fontname": "TeX Gyre Pagella", "fontsize": 45,
            "primarycolor": "#FFFF64", "outlinecolor": "#000000",
            "outline": 2, "shadow": 0, "alignment": 2, "marginv": 573,
            "bold": True, "italic": True,
        })
        traducao_style = _json.dumps({
            "fontname": "TeX Gyre Pagella", "fontsize": 43,
            "primarycolor": "#FFFFFF", "outlinecolor": "#000000",
            "outline": 2, "shadow": 0, "alignment": 8, "marginv": 1353,
            "bold": True, "italic": True,
        })
        idiomas_alvo = _json.dumps(["en", "pt", "es", "de", "fr", "it", "pl"])
        hashtags = _json.dumps(["#BestOfOpera", "#Opera", "#ClassicalMusic"])
        categorias = _json.dumps(["Emotional", "Historical", "Vocal"])
        curadoria_categories = _json.dumps({
            "icones": {"name": "Icones", "emoji": "👑", "desc": "Lendas eternas da opera", "seeds": ["Luciano Pavarotti best live aria opera performance", "Maria Callas iconic soprano opera aria live", "Placido Domingo tenor concert opera live", "Montserrat Caballe soprano legendary opera performance", "Jose Carreras three tenors concert live opera", "Enrico Caruso historical opera tenor recording"]},
            "estrelas": {"name": "Estrelas", "emoji": "⭐", "desc": "Estrelas modernas da opera", "seeds": ["Andrea Bocelli live concert opera performance", "Anna Netrebko soprano opera performance live", "Jonas Kaufmann tenor opera aria live concert", "Pretty Yende soprano opera live performance", "Juan Diego Florez tenor opera live performance", "Jakub Jozef Orlinski countertenor baroque opera live"]},
            "hits": {"name": "Hits", "emoji": "🎵", "desc": "Arias e musicas mais populares", "seeds": ["Nessun Dorma best live performance opera tenor", "Ave Maria opera live soprano performance beautiful", "Time to Say Goodbye Con te partiro live opera", "O Sole Mio best live tenor performance opera", "The Prayer duet opera live performance beautiful", "Hallelujah best live performance classical choir"]},
            "surpreendente": {"name": "Surpreendente", "emoji": "🎭", "desc": "Performances virais e inesperadas", "seeds": ["flash mob opera surprise public performance amazing", "unexpected opera singer street performance viral", "theremin classical music amazing performance instrument", "overtone singing polyphonic incredible vocal technique", "opera singer surprise restaurant wedding performance", "unusual instrument classical performance viral amazing"]},
            "talent": {"name": "Talent", "emoji": "🌟", "desc": "Revelacoes em shows de talentos", "seeds": ["opera singer audition got talent amazing judges shocked", "golden buzzer opera performance talent show incredible", "child sings opera audition judges crying talent show", "Susan Boyle I Dreamed a Dream first audition", "Paul Potts Nessun Dorma Britain got talent audition", "unexpected opera voice talent show blind audition amazing"]},
            "corais": {"name": "Corais", "emoji": "🎶", "desc": "Corais e grupos vocais", "seeds": ["amazing choir opera performance live concert best", "Pentatonix Hallelujah live concert performance", "African choir incredible performance amazing vocal", "boys choir sacred music cathedral performance beautiful", "a cappella group classical opera performance live", "choir flash mob opera surprise performance public"]},
        })
        elite_hits_val = _json.dumps(["Nessun Dorma", "Ave Maria", "O mio babbino caro", "Time to Say Goodbye", "The Prayer", "Hallelujah", "O Sole Mio", "La donna e mobile", "Con te partiro", "Casta Diva", "Queen of the Night", "Flower Duet", "I Dreamed a Dream", "Never Enough", "Vissi d'arte", "Pie Jesu", "O Holy Night", "Amazing Grace", "Sempre Libera", "Habanera", "Granada", "Largo al factotum", "Vesti la giubba", "Baba Yetu", "Danny Boy", "Caruso", "Bohemian Rhapsody"])
        power_names_val = _json.dumps(["Luciano Pavarotti", "Andrea Bocelli", "Maria Callas", "Placido Domingo", "Montserrat Caballe", "Jonas Kaufmann", "Anna Netrebko", "Amira Willighagen", "Jackie Evancho", "Laura Bretan", "Susan Boyle", "Paul Potts", "Pentatonix", "Sarah Brightman", "Jose Carreras", "Renee Fleming", "Cecilia Bartoli", "Diana Damrau", "Jakub Jozef Orlinski", "Emma Kok", "Malakai Bayoh", "Pretty Yende", "Angela Gheorghiu", "Juan Diego Florez", "Rolando Villazon", "Bryn Terfel"])
        voice_keywords_val = _json.dumps(["soprano", "tenor", "baritone", "mezzo", "countertenor", "aria", "opera", "classical voice", "live concert"])
        institutional_channels_val = _json.dumps(["royal opera", "met opera", "metropolitan opera", "la scala", "wiener staatsoper", "bbc", "arte concert", "deutsche oper", "opera de paris", "sydney opera", "andre rieu"])
        category_specialty_val = _json.dumps({"icones": ["three tenors", "la scala", "royal opera", "pavarotti and friends", "farewell", "legendary"], "estrelas": ["recital", "gala concert", "concert hall", "philharmonic", "arena di verona"], "hits": ["encore", "standing ovation", "duet", "best version", "iconic"], "surpreendente": ["flash mob", "street", "theremin", "overtone", "handpan", "surprise", "viral"], "talent": ["audition", "golden buzzer", "got talent", "x factor", "the voice", "judges"], "corais": ["choir", "ensemble", "a cappella", "choral", "voices", "gospel"]})
        scoring_weights_val = _json.dumps({"elite_hit": 15, "power_name": 15, "specialty": 25, "voice": 15, "institutional": 10, "quality": 10, "views": 10, "views_threshold": 100000, "max_total": 100})
        curadoria_filters_val = _json.dumps({"duracao_max": 900})

        conn.execute(text("""
            INSERT INTO editor_perfis (
                nome, sigla, slug, ativo, editorial_lang,
                idiomas_alvo, idioma_preview,
                overlay_style, lyrics_style, traducao_style,
                overlay_max_chars, overlay_max_chars_linha,
                lyrics_max_chars, traducao_max_chars,
                video_width, video_height,
                r2_prefix, cor_primaria, cor_secundaria,
                duracao_corte_min, duracao_corte_max,
                hashtags_fixas, categorias_hook,
                curadoria_categories, elite_hits, power_names, voice_keywords,
                institutional_channels, category_specialty, scoring_weights, curadoria_filters
            )
            SELECT
                'Best of Opera', 'BO', 'best-of-opera', TRUE, 'pt',
                :idiomas_alvo, 'pt',
                :overlay_style, :lyrics_style, :traducao_style,
                70, 35, 43, 100, 1080, 1920,
                'editor', '#1a1a2e', '#e94560', 30, 90,
                :hashtags, :categorias,
                :curadoria_categories, :elite_hits, :power_names, :voice_keywords,
                :institutional_channels, :category_specialty, :scoring_weights, :curadoria_filters
            WHERE NOT EXISTS (
                SELECT 1 FROM editor_perfis WHERE sigla = 'BO'
            )
        """), {
            "idiomas_alvo": idiomas_alvo,
            "overlay_style": overlay_style,
            "lyrics_style": lyrics_style,
            "traducao_style": traducao_style,
            "hashtags": hashtags,
            "categorias": categorias,
            "curadoria_categories": curadoria_categories,
            "elite_hits": elite_hits_val,
            "power_names": power_names_val,
            "voice_keywords": voice_keywords_val,
            "institutional_channels": institutional_channels_val,
            "category_specialty": category_specialty_val,
            "scoring_weights": scoring_weights_val,
            "curadoria_filters": curadoria_filters_val,
        })
        logger.info("Migration: seed editor_perfis Best of Opera OK (idempotente)")

        # Backfill: popular campos de curadoria no BO existente (se ainda NULL)
        conn.execute(text("""
            UPDATE editor_perfis SET
                curadoria_categories = :curadoria_categories,
                elite_hits = :elite_hits,
                power_names = :power_names,
                voice_keywords = :voice_keywords,
                institutional_channels = :institutional_channels,
                category_specialty = :category_specialty,
                scoring_weights = :scoring_weights,
                curadoria_filters = :curadoria_filters
            WHERE sigla = 'BO' AND curadoria_categories IS NULL
        """), {
            "curadoria_categories": curadoria_categories,
            "elite_hits": elite_hits_val,
            "power_names": power_names_val,
            "voice_keywords": voice_keywords_val,
            "institutional_channels": institutional_channels_val,
            "category_specialty": category_specialty_val,
            "scoring_weights": scoring_weights_val,
            "curadoria_filters": curadoria_filters_val,
        })
        logger.info("Migration: backfill curadoria campos no BO OK")

    # Migration: adicionar colunas de curadoria ao editor_perfis (para tabelas já existentes)
    if "editor_perfis" in insp.get_table_names():
        with engine.begin() as conn:
            perfil_cols = [c["name"] for c in insp.get_columns("editor_perfis")]
            for col_name, col_type in [
                ("curadoria_categories", "JSON"),
                ("elite_hits", "JSON"),
                ("power_names", "JSON"),
                ("voice_keywords", "JSON"),
                ("institutional_channels", "JSON"),
                ("category_specialty", "JSON"),
                ("scoring_weights", "JSON"),
                ("curadoria_filters", "JSON"),
                ("anti_spam_terms", "VARCHAR(500) DEFAULT '-karaoke -piano -tutorial -lesson -reaction -review -lyrics -chords'"),
                ("playlist_id", "VARCHAR(100) DEFAULT ''"),
                ("hook_categories_redator", "JSON"),
                ("identity_prompt_redator", "TEXT"),
                ("tom_de_voz_redator", "TEXT"),
                ("logo_url", "VARCHAR(500)"),
                ("font_name", "VARCHAR(100)"),
            ]:
                if col_name not in perfil_cols:
                    conn.execute(text(f"ALTER TABLE editor_perfis ADD COLUMN {col_name} {col_type}"))
                    logger.info(f"Migration: added column editor_perfis.{col_name}")
            logger.info("Migration: editor_perfis curadoria columns OK")

    # Migration: tabela editor_usuarios (auth)
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS editor_usuarios (
                id SERIAL PRIMARY KEY,
                nome VARCHAR(100) NOT NULL,
                email VARCHAR(200) UNIQUE NOT NULL,
                senha_hash VARCHAR(500) NOT NULL,
                role VARCHAR(20) DEFAULT 'operador',
                ativo BOOLEAN DEFAULT TRUE,
                ultimo_login TIMESTAMP,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_editor_usuarios_email ON editor_usuarios (email)"))
        logger.info("Migration: tabela editor_usuarios garantida")

        # Seed: usuario admin padrão (idempotente)
        ja_existe = conn.execute(text(
            "SELECT 1 FROM editor_usuarios WHERE email = 'admin@bestofopera.com'"
        )).fetchone()
        if not ja_existe:
            from passlib.context import CryptContext as _CryptContext
            _pwd = _CryptContext(schemes=["bcrypt"], deprecated="auto")
            _admin_hash = _pwd.hash("BestOfOpera2026!")
            conn.execute(text("""
                INSERT INTO editor_usuarios (nome, email, senha_hash, role, ativo)
                VALUES ('Admin', 'admin@bestofopera.com', :senha_hash, 'admin', TRUE)
            """), {"senha_hash": _admin_hash})
            logger.info("Migration: seed usuario admin@bestofopera.com criado. TROQUE A SENHA APÓS O PRIMEIRO LOGIN.")
        else:
            logger.info("Migration: seed usuario admin@bestofopera.com ja existe (ok)")

    if "editor_edicoes" not in insp.get_table_names():
        return
    cols = [c["name"] for c in insp.get_columns("editor_edicoes")]

    # ALTER TABLE — transação própria, sem try/except interno (garantia de commit isolado)
    with engine.begin() as conn:
        for col_name, col_type in [
            ("corte_original_inicio", "VARCHAR(20)"),
            ("corte_original_fim", "VARCHAR(20)"),
            ("notas_revisao", "TEXT"),
            ("r2_base", "VARCHAR(500)"),
            ("redator_project_id", "INTEGER"),
            ("task_heartbeat", "TIMESTAMP"),
            ("progresso_detalhe", "JSON"),
            ("tentativas_requeue", "INTEGER DEFAULT 0"),
            ("sem_lyrics", "BOOLEAN DEFAULT FALSE"),
            ("perfil_id", "INTEGER REFERENCES editor_perfis(id)"),
        ]:
            if col_name not in cols:
                conn.execute(text(f"ALTER TABLE editor_edicoes ADD COLUMN {col_name} {col_type}"))
                logger.info(f"Migration: added column {col_name}")

    # Vincular edições existentes ao perfil Best of Opera — transação própria
    try:
        with engine.begin() as conn:
            conn.execute(text("""
                UPDATE editor_edicoes
                SET perfil_id = (SELECT id FROM editor_perfis WHERE sigla = 'BO')
                WHERE perfil_id IS NULL
            """))
        logger.info("Migration: editor_edicoes.perfil_id preenchido para edicoes sem perfil")
    except Exception as e:
        logger.warning(f"Migration perfil_id update: {e}")

    # Migration: UNIQUE index em traducao_letra — transação própria
    try:
        with engine.begin() as conn:
            conn.execute(text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_traducao_edicao_idioma "
                "ON editor_traducoes_letras (edicao_id, idioma)"
            ))
        logger.info("Migration: created unique index uq_traducao_edicao_idioma")
    except Exception as e:
        logger.warning(f"Migration uq_traducao_edicao_idioma: {e}")

    # Migration: UNIQUE index em render — transação própria
    try:
        with engine.begin() as conn:
            conn.execute(text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_render_edicao_idioma "
                "ON editor_renders (edicao_id, idioma)"
            ))
        logger.info("Migration: created unique index uq_render_edicao_idioma")
    except Exception as e:
        logger.warning(f"Migration uq_render_edicao_idioma: {e}")

    # Migration: UNIQUE index em redator_project_id — transação própria
    try:
        with engine.begin() as conn:
            dups = conn.execute(text(
                "SELECT redator_project_id, COUNT(*) as qtd "
                "FROM editor_edicoes "
                "WHERE redator_project_id IS NOT NULL "
                "GROUP BY redator_project_id "
                "HAVING COUNT(*) > 1"
            )).fetchall()
            if dups:
                logger.warning(
                    f"Migration: {len(dups)} redator_project_id duplicados encontrados. "
                    "UNIQUE index NÃO criado. Limpeza manual necessária."
                )
            else:
                conn.execute(text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS uix_redator_project_id "
                    "ON editor_edicoes (redator_project_id) "
                    "WHERE redator_project_id IS NOT NULL"
                ))
                logger.info("Migration: created unique index uix_redator_project_id")
    except Exception as e:
        logger.warning(f"Migration uix_redator_project_id: {e}")

    # Migration: tabela editor_reports (criada pelo create_all, mas garantir colunas)
    if "editor_reports" in insp.get_table_names():
        report_cols = [c["name"] for c in insp.get_columns("editor_reports")]
        with engine.begin() as conn:
            for col_name, col_type in [
                ("prioridade", "VARCHAR(20) DEFAULT 'media'"),
                ("resolvido_em", "TIMESTAMP"),
                ("updated_at", "TIMESTAMP"),
            ]:
                if col_name not in report_cols:
                    try:
                        conn.execute(text(f"ALTER TABLE editor_reports ADD COLUMN {col_name} {col_type}"))
                        logger.info(f"Migration editor_reports: added column {col_name}")
                    except Exception as e:
                        logger.warning(f"Migration editor_reports/{col_name}: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Criar tabelas no startup
    Base.metadata.create_all(bind=engine)
    _run_migrations()
    # Criar diretório de storage
    Path(STORAGE_PATH).mkdir(parents=True, exist_ok=True)
    # Iniciar worker sequencial e reagendar tasks travadas
    from app.worker import worker_loop, requeue_stale_tasks
    worker_task = asyncio.create_task(worker_loop())
    requeue_stale_tasks()
    yield
    # Shutdown: cancelar worker limpo
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="Best of Opera — Editor",
    description="APP3: Download, corte, lyrics, renderização em 7 idiomas",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rotas
app.include_router(health.router)
app.include_router(edicoes.router)
app.include_router(letras.router)
app.include_router(pipeline.router)
app.include_router(importar.router)
app.include_router(dashboard.router)
app.include_router(reports.router)
app.include_router(auth.router)
app.include_router(admin_perfil.router)
app.include_router(admin_perfil.router_internal)
