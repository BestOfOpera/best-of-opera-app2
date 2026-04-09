# deploy trigger 2026-04-09
"""APP Editor — Best of Opera. Ponto de entrada FastAPI."""
import asyncio
import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

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
            "fontname": "TeX Gyre Schola",
            "fontsize": 58,             # corpo
            "gancho_fontsize": 60,      # 1ª legenda
            "cta_fontsize": 58,         # última legenda (igual ao corpo)
            "primarycolor": "#FFFFFF",
            "outlinecolor": "#000000",
            "outline": 0,               # sem contorno — texto sobre faixa preta
            "shadow": 0,
            "alignment": 2,
            "marginv": 1296,
            "bold": True,
            "italic": True,             # TeX Gyre Schola Bold Italic
            "gap_overlay_px": 30,       # 30px acima da imagem (brand doc)
        })
        lyrics_style = _json.dumps({
            "fontname": "TeX Gyre Schola",
            "fontsize": 48,
            "primarycolor": "#E4F042",
            "outlinecolor": "#000000",
            "outline": 0,
            "shadow": 0,
            "alignment": 2,
            "marginv": 573,
            "bold": True,
            "italic": True,
        })
        traducao_style = _json.dumps({
            "fontname": "TeX Gyre Schola",
            "fontsize": 48,
            "primarycolor": "#FFFFFF",
            "outlinecolor": "#000000",
            "outline": 0,
            "shadow": 0,
            "alignment": 8,
            "marginv": 1353,
            "bold": True,
            "italic": True,
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
                overlay_max_chars, overlay_max_chars_linha, overlay_interval_secs,
                lyrics_max_chars, traducao_max_chars,
                video_width, video_height,
                r2_prefix, cor_primaria, cor_secundaria,
                hashtags_fixas, categorias_hook,
                curadoria_categories, elite_hits, power_names, voice_keywords,
                institutional_channels, category_specialty, scoring_weights, curadoria_filters
            )
            SELECT
                'Best of Opera', 'BO', 'best-of-opera', TRUE, 'pt',
                :idiomas_alvo, 'pt',
                :overlay_style, :lyrics_style, :traducao_style,
                70, 35, 10, 43, 100, 1080, 1920,
                'editor', '#1a1a2e', '#e94560',
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

        # Backfill: corrigir font_name e fontname nos estilos (TeX Gyre Pagella → Playfair Display)
        conn.execute(text("""
            UPDATE editor_perfis SET
                font_name = 'Playfair Display',
                overlay_style = REPLACE(overlay_style::text, 'TeX Gyre Pagella', 'Playfair Display')::jsonb,
                lyrics_style = REPLACE(lyrics_style::text, 'TeX Gyre Pagella', 'Playfair Display')::jsonb,
                traducao_style = REPLACE(traducao_style::text, 'TeX Gyre Pagella', 'Playfair Display')::jsonb
            WHERE font_name IS NULL
              AND overlay_style::text LIKE '%TeX Gyre Pagella%'
        """))
        logger.info("Migration: backfill font_name e fontname nos estilos (Playfair Display) OK")

        # Backfill: atualizar BO para estilos corretos (brand doc v1) — guarda: só roda se fonte ainda não migrada
        conn.execute(text("""
            UPDATE editor_perfis SET
                font_name = 'TeX Gyre Schola',
                overlay_style = :overlay_style,
                lyrics_style = :lyrics_style,
                traducao_style = :traducao_style
            WHERE sigla = 'BO' AND (font_name IS NULL OR font_name != 'TeX Gyre Schola')
        """), {
            "overlay_style": overlay_style,
            "lyrics_style": lyrics_style,
            "traducao_style": traducao_style,
        })
        logger.info("Migration: backfill BO estilos brand doc v1 OK")

        # Backfill: overlay_interval_secs = 10 para BO (brand doc)
        conn.execute(text("""
            UPDATE editor_perfis SET
                overlay_interval_secs = 10
            WHERE sigla = 'BO' AND overlay_interval_secs != 10
        """))
        logger.info("Migration: backfill overlay_interval_secs BO = 10 OK")

        # Backfill: lyrics/traducao fontsize 32 → 40px no BO
        conn.execute(text("""
            UPDATE editor_perfis SET
                lyrics_style = jsonb_set(lyrics_style::jsonb, '{fontsize}', '40')::json,
                traducao_style = jsonb_set(traducao_style::jsonb, '{fontsize}', '40')::json
            WHERE sigla = 'BO'
              AND (lyrics_style->>'fontsize')::int < 40
        """))
        logger.info("Migration: backfill lyrics/traducao fontsize BO = 40px OK")

        # Backfill: aumentar fontes BO — gancho 60, corpo/cta 58, lyrics/tradução 48
        conn.execute(text("""
            UPDATE editor_perfis SET
                overlay_style = jsonb_set(
                    jsonb_set(
                        jsonb_set(overlay_style::jsonb, '{fontsize}', '58'),
                        '{gancho_fontsize}', '60'
                    ),
                    '{cta_fontsize}', '58'
                )::json,
                lyrics_style = jsonb_set(lyrics_style::jsonb, '{fontsize}', '48')::json,
                traducao_style = jsonb_set(traducao_style::jsonb, '{fontsize}', '48')::json
            WHERE sigla = 'BO'
              AND (overlay_style->>'gancho_fontsize')::int < 60
        """))
        logger.info("Migration: backfill BO fontes maiores (gancho 60, corpo/cta 58, lyrics/trad 48) OK")

        # Seed idempotente do perfil Reels Classics
        rc_overlay_style = _json.dumps({
            "fontname": "Inter",
            "fontsize": 48,
            "gancho_fontsize": 52,
            "cta_fontsize": 44,
            "primarycolor": "#FFFFFF",
            "outlinecolor": "#000000",
            "outline": 0,
            "shadow": 0,
            "alignment": 2,
            "marginv": 1291,
            "bold": True,
            "italic": False,
            "gap_overlay_px": 28,
        })
        rc_lyrics_style = _json.dumps({
            "fontname": "Inter",
            "fontsize": 32,
            "primarycolor": "#E4F042",
            "outlinecolor": "#000000",
            "outline": 0,
            "shadow": 0,
            "alignment": 2,
            "marginv": 614,
            "bold": True,
            "italic": True,
        })
        rc_traducao_style = _json.dumps({
            "fontname": "Inter",
            "fontsize": 32,
            "primarycolor": "#FFFFFF",
            "outlinecolor": "#000000",
            "outline": 0,
            "shadow": 0,
            "alignment": 8,
            "marginv": 614,
            "bold": True,
            "italic": True,
        })
        conn.execute(text("""
            INSERT INTO editor_perfis (
                nome, sigla, slug, ativo, editorial_lang,
                idiomas_alvo, idioma_preview,
                overlay_style, lyrics_style, traducao_style,
                overlay_max_chars, overlay_max_chars_linha,
                lyrics_max_chars, traducao_max_chars,
                video_width, video_height,
                r2_prefix, cor_primaria, cor_secundaria,
                font_name
            )
            SELECT
                'Reels Classics', 'RC', 'reels-classics', TRUE, 'pt',
                :idiomas_alvo, 'pt',
                :overlay_style, :lyrics_style, :traducao_style,
                66, 33, 43, 100, 1080, 1920,
                'reels-classics', '#0a0a0a', '#c0a060',
                :font_name
            WHERE NOT EXISTS (
                SELECT 1 FROM editor_perfis WHERE sigla = 'RC'
            )
        """), {
            "idiomas_alvo": idiomas_alvo,
            "overlay_style": rc_overlay_style,
            "lyrics_style": rc_lyrics_style,
            "traducao_style": rc_traducao_style,
            "font_name": "Inter",
        })
        logger.info("Migration: seed editor_perfis Reels Classics OK (idempotente)")

        conn.execute(text("""
            UPDATE editor_perfis SET
                font_name = :font_name,
                overlay_style = :overlay_style,
                lyrics_style = :lyrics_style,
                traducao_style = :traducao_style
            WHERE sigla = 'RC' AND font_name IS NULL
        """), {
            "font_name": "Inter",
            "overlay_style": rc_overlay_style,
            "lyrics_style": rc_lyrics_style,
            "traducao_style": rc_traducao_style,
        })
        logger.info("Migration: backfill Reels Classics font e estilos OK")

        # Backfill: corrigir overlay_max_chars do RC (Content Bible v3.4: 66/33)
        conn.execute(text("""
            UPDATE editor_perfis SET
                overlay_max_chars = 66,
                overlay_max_chars_linha = 33
            WHERE sigla = 'RC' AND overlay_max_chars = 70
        """))
        logger.info("Migration: backfill overlay_max_chars RC = 66/33 OK")

    # Migration: corrigir overlay_style do RC (Brand Definition v1.0 / SPEC-008)
    try:
        with engine.begin() as conn:
            import json as _json2
            rc_overlay_style_v2 = _json2.dumps({
                "fontname": "Inter Bold",
                "fontsize": 48,
                "gancho_fontsize": 52,
                "corpo_fontsize": 48,
                "cta_fontsize": 44,
                "primarycolor": "#FFFFFF",
                "outline": 0,
                "shadow": 0,
                "alignment": 2,
                "marginv": 28,
            })
            conn.execute(text("""
                UPDATE editor_perfis SET
                    font_name = :font_name,
                    overlay_style = :overlay_style,
                    lyrics_style = :empty_json,
                    traducao_style = :empty_json
                WHERE sigla = 'RC'
                  AND (overlay_style->>'corpo_fontsize') IS NULL
            """), {
                "font_name": "Inter Bold",
                "overlay_style": rc_overlay_style_v2,
                "empty_json": "{}",
            })
            logger.info("Migration: backfill RC overlay_style Brand Definition v1.0 (SPEC-008) OK")
    except Exception as e:
        logger.warning(f"Migration RC overlay_style SPEC-008: {e}")

    # Migration v3: Atualizar perfil Reels Classics com valores auditados (Inter Display Bold)
    # Valores finais validados: fontsize 54/48/44, alignment 8 (top), outline 0, shadow 0.
    # MarginV calculado DINAMICAMENTE por evento baseado no número de linhas do texto.
    # Campos gancho_gap/corpo_gap/cta_gap + line_spacing controlam o posicionamento.
    # lyrics_style e traducao_style ficam vazios em v1 (RC usa defaults do sistema para vocal).
    try:
        with engine.begin() as conn:
            import json as _json3
            rc_overlay_v3 = _json3.dumps({
                "fontsize": 48,
                "primarycolor": "#FFFFFF",
                "outlinecolor": "#000000",
                "outline": 0,
                "shadow": 0,
                "alignment": 8,
                "bold": True,
                "italic": False,
                "gancho_fontsize": 54,
                "corpo_fontsize": 48,
                "cta_fontsize": 44,
                "gap_overlay_px": 15,
                "gancho_gap": 15,
                "corpo_gap": 18,
                "cta_gap": 20,
                "gancho_line_spacing": 10,
                "corpo_line_spacing": 9,
                "cta_line_spacing": 12,
                "marginl": 40,
                "marginr": 40,
                "marginv": 453,
            })
            conn.execute(text("""
                UPDATE editor_perfis SET
                    font_name = :font_name,
                    overlay_style = :overlay_style,
                    lyrics_style = :empty_json,
                    traducao_style = :empty_json
                WHERE sigla = 'RC'
                  AND (overlay_style->>'gancho_gap') IS NULL
            """), {
                "font_name": "Inter Display",
                "overlay_style": rc_overlay_v3,
                "empty_json": "{}",
            })
            logger.info("Migration v3: RC overlay_style Inter Display Bold (valores auditados) OK")
    except Exception as e:
        logger.warning(f"Migration v3 RC overlay_style: {e}")

    # Migration v4: RC — fontsizes maiores para melhor legibilidade em mobile
    # Valores revisados após teste visual em produção (fontsizes anteriores pequenos demais).
    # video_top agora é dinâmico (image_top_px), não precisa de marginv fixo na migration.
    try:
        with engine.begin() as conn:
            import json as _json4
            rc_overlay_v4 = _json4.dumps({
                "fontsize": 56,
                "primarycolor": "#FFFFFF",
                "outlinecolor": "#000000",
                "outline": 0,
                "shadow": 0,
                "alignment": 8,
                "bold": True,
                "italic": False,
                "gancho_fontsize": 64,
                "corpo_fontsize": 56,
                "cta_fontsize": 52,
                "gap_overlay_px": 18,
                "gancho_gap": 18,
                "corpo_gap": 20,
                "cta_gap": 22,
                "gancho_line_spacing": 12,
                "corpo_line_spacing": 11,
                "cta_line_spacing": 13,
                "marginl": 40,
                "marginr": 40,
                "marginv": 407,
            })
            conn.execute(text("""
                UPDATE editor_perfis SET
                    overlay_style = :overlay_style
                WHERE sigla = 'RC'
                  AND (overlay_style->>'gancho_fontsize')::int != 64
            """), {
                "overlay_style": rc_overlay_v4,
            })
            logger.info("Migration v4: RC fontsizes maiores (64/56/52) OK")
    except Exception as e:
        logger.warning(f"Migration v4 RC fontsizes: {e}")

    # Migration v5: RC — fontsizes ajustados + lyrics/tradução + pre_formatted overlays
    # Overlays pré-formatados do ZIP: sistema não trunca/reformata.
    # Lyrics: Poppins Bold Italic 46px amarelo com outline 3px.
    # Tradução: Poppins Bold 42px branco com outline 3px.
    # Cores em formato #RRGGBB (convertido internamente por hex_to_ssa_color).
    try:
        with engine.begin() as conn:
            import json as _json5
            rc_overlay_v5 = _json5.dumps({
                "fontsize": 54,
                "primarycolor": "#FFFFFF",
                "outlinecolor": "#000000",
                "outline": 0,
                "shadow": 0,
                "alignment": 8,
                "bold": True,
                "italic": False,
                "gancho_fontsize": 60,
                "corpo_fontsize": 54,
                "cta_fontsize": 50,
                "gap_overlay_px": 14,
                "gancho_gap": 14,
                "corpo_gap": 16,
                "cta_gap": 18,
                "gancho_line_spacing": 11,
                "corpo_line_spacing": 10,
                "cta_line_spacing": 12,
                "marginl": 40,
                "marginr": 40,
                "marginv": 418,
                "overlay_pre_formatted": True,
            })
            rc_lyrics_v5 = _json5.dumps({
                "fontname": "Poppins",
                "fontsize": 46,
                "primarycolor": "#FFFF00",
                "outlinecolor": "#000000",
                "outline": 3,
                "shadow": 0,
                "bold": True,
                "italic": True,
                "alignment": 2,
            })
            rc_traducao_v5 = _json5.dumps({
                "fontname": "Poppins",
                "fontsize": 42,
                "primarycolor": "#FFFFFF",
                "outlinecolor": "#000000",
                "outline": 3,
                "shadow": 0,
                "bold": True,
                "italic": False,
                "alignment": 8,
            })
            conn.execute(text("""
                UPDATE editor_perfis SET
                    overlay_style = :overlay_style,
                    lyrics_style = :lyrics_style,
                    traducao_style = :traducao_style
                WHERE sigla = 'RC'
                  AND (overlay_style->>'gancho_fontsize')::int != 60
            """), {
                "overlay_style": rc_overlay_v5,
                "lyrics_style": rc_lyrics_v5,
                "traducao_style": rc_traducao_v5,
            })
            logger.info("Migration v5: RC fontsizes ajustados + lyrics/tradução Poppins + pre_formatted OK")
    except Exception as e:
        logger.warning(f"Migration v5 RC: {e}")

    # Migration v6: RC — ajuste fino definitivo (gaps, fontsize, lyrics italic, cores HEX)
    # Guard: gancho_gap != 12 (valor definitivo desta migration)
    try:
        with engine.begin() as conn:
            import json as _json6
            rc_overlay_v6 = _json6.dumps({
                "fontsize": 50,
                "primarycolor": "#FFFFFF",
                "outlinecolor": "#000000",
                "outline": 0,
                "shadow": 0,
                "alignment": 8,
                "bold": True,
                "italic": False,
                "gancho_fontsize": 56,
                "corpo_fontsize": 50,
                "cta_fontsize": 48,
                "gap_overlay_px": 12,
                "gancho_gap": 12,
                "corpo_gap": 14,
                "cta_gap": 16,
                "gancho_line_spacing": 6,
                "corpo_line_spacing": 5,
                "cta_line_spacing": 6,
                "marginl": 40,
                "marginr": 40,
                "marginv": 418,
                "overlay_pre_formatted": True,
            })
            rc_lyrics_v6 = _json6.dumps({
                "fontname": "Poppins",
                "fontsize": 48,
                "primarycolor": "#FFFF00",
                "outlinecolor": "#000000",
                "outline": 3,
                "shadow": 0,
                "bold": True,
                "italic": True,
                "alignment": 2,
            })
            rc_traducao_v6 = _json6.dumps({
                "fontname": "Poppins",
                "fontsize": 44,
                "primarycolor": "#FFFFFF",
                "outlinecolor": "#000000",
                "outline": 3,
                "shadow": 0,
                "bold": True,
                "italic": True,
                "alignment": 8,
            })
            conn.execute(text("""
                UPDATE editor_perfis SET
                    overlay_style = :overlay_style,
                    lyrics_style = :lyrics_style,
                    traducao_style = :traducao_style
                WHERE sigla = 'RC'
                  AND (overlay_style->>'gancho_gap')::int != 12
            """), {
                "overlay_style": rc_overlay_v6,
                "lyrics_style": rc_lyrics_v6,
                "traducao_style": rc_traducao_v6,
            })
            logger.info("Migration v6: RC ajuste definitivo (gaps/fontsize/lyrics italic/pre_formatted) OK")
    except Exception as e:
        logger.warning(f"Migration v6 RC: {e}")

    # Migration v7: RC — tradução idêntica a lyrics (fontsize 48), corpo 52px
    # Tradução: cópia exata de lyrics_style, apenas primarycolor diferente (#FFFFFF vs #FFFF00)
    # Guard: traducao fontsize != 48 (valor definitivo)
    try:
        with engine.begin() as conn:
            import json as _json7
            rc_overlay_v7 = _json7.dumps({
                "fontsize": 52,
                "primarycolor": "#FFFFFF",
                "outlinecolor": "#000000",
                "outline": 0,
                "shadow": 0,
                "alignment": 8,
                "bold": True,
                "italic": False,
                "gancho_fontsize": 56,
                "corpo_fontsize": 52,
                "cta_fontsize": 48,
                "gap_overlay_px": 12,
                "gancho_gap": 12,
                "corpo_gap": 14,
                "cta_gap": 16,
                "gancho_line_spacing": 6,
                "corpo_line_spacing": 5,
                "cta_line_spacing": 6,
                "marginl": 40,
                "marginr": 40,
                "marginv": 418,
                "overlay_pre_formatted": True,
            })
            rc_lyrics_v7 = _json7.dumps({
                "fontname": "Poppins",
                "fontsize": 48,
                "primarycolor": "#FFFF00",
                "outlinecolor": "#000000",
                "outline": 3,
                "shadow": 0,
                "bold": True,
                "italic": True,
                "alignment": 2,
            })
            rc_traducao_v7 = _json7.dumps({
                "fontname": "Poppins",
                "fontsize": 48,
                "primarycolor": "#FFFFFF",
                "outlinecolor": "#000000",
                "outline": 3,
                "shadow": 0,
                "bold": True,
                "italic": True,
                "alignment": 8,
            })
            conn.execute(text("""
                UPDATE editor_perfis SET
                    overlay_style = :overlay_style,
                    lyrics_style = :lyrics_style,
                    traducao_style = :traducao_style
                WHERE sigla = 'RC'
                  AND (traducao_style->>'fontsize')::int != 48
            """), {
                "overlay_style": rc_overlay_v7,
                "lyrics_style": rc_lyrics_v7,
                "traducao_style": rc_traducao_v7,
            })
            logger.info("Migration v7: RC traducao=lyrics (fs48), corpo 52px OK")
    except Exception as e:
        logger.warning(f"Migration v7 RC: {e}")

    # Migration v8+v9: RC — fontsizes definitivos 56/52/48
    # v8 originalmente setou 58/54/50, v9 reverte para 56/52/48
    # Guard: gancho_fontsize != 56 (valor definitivo)
    try:
        with engine.begin() as conn:
            import json as _json8
            rc_overlay_v8 = _json8.dumps({
                "fontsize": 52,
                "primarycolor": "#FFFFFF",
                "outlinecolor": "#000000",
                "outline": 0,
                "shadow": 0,
                "alignment": 8,
                "bold": True,
                "italic": False,
                "gancho_fontsize": 56,
                "corpo_fontsize": 52,
                "cta_fontsize": 48,
                "gap_overlay_px": 12,
                "gancho_gap": 12,
                "corpo_gap": 14,
                "cta_gap": 16,
                "gancho_line_spacing": 6,
                "corpo_line_spacing": 5,
                "cta_line_spacing": 6,
                "marginl": 40,
                "marginr": 40,
                "marginv": 418,
                "overlay_pre_formatted": True,
            })
            conn.execute(text("""
                UPDATE editor_perfis SET
                    overlay_style = :overlay_style
                WHERE sigla = 'RC'
                  AND (overlay_style->>'gancho_fontsize')::int != 56
            """), {"overlay_style": rc_overlay_v8})
            logger.info("Migration v8/v9: RC fontsizes 56/52/48 (gancho/corpo/cta) OK")
            # RC usa 3 linhas × 33 chars = 99 chars total (não 66 que é BO 2×33)
            conn.execute(text("""
                UPDATE editor_perfis SET overlay_max_chars = 99
                WHERE sigla = 'RC' AND overlay_max_chars != 99
            """))
    except Exception as e:
        logger.warning(f"Migration v8/v9 RC: {e}")

    # Verificação de perfil RC no startup
    try:
        with engine.begin() as conn:
            row = conn.execute(text(
                "SELECT overlay_style->>'gancho_fontsize' as g, overlay_style->>'corpo_fontsize' as c, overlay_style->>'cta_fontsize' as t FROM editor_perfis WHERE sigla = 'RC'"
            )).first()
            if row:
                logger.info(f"[PERFIL CHECK] RC gancho={row[0]} corpo={row[1]} cta={row[2]}")
    except Exception as e:
        logger.warning(f"[PERFIL CHECK] Falha ao verificar fontsizes RC: {e}")

    # Migration: BO overlay gap reduzido (30→8px) para legendas mais próximas da imagem
    try:
        with engine.begin() as conn:
            conn.execute(text("""
                UPDATE editor_perfis SET
                    overlay_style = jsonb_set(
                        COALESCE(overlay_style::jsonb, '{}'),
                        '{gap_overlay_px}', '8'
                    )::json
                WHERE sigla = 'BO'
                  AND (overlay_style->>'gap_overlay_px')::int != 8
            """))
            logger.info("Migration: BO gap_overlay_px 30→8 OK")
    except Exception as e:
        logger.warning(f"Migration BO gap: {e}")

    # Migration: BO logo watermark
    try:
        with engine.begin() as conn:
            conn.execute(text("""
                UPDATE editor_perfis SET
                    logo_url = 'logo_bo.png'
                WHERE sigla = 'BO'
                  AND (logo_url IS NULL OR logo_url = '')
            """))
            logger.info("Migration: BO logo_url = 'logo_bo.png' OK")
    except Exception as e:
        logger.warning(f"Migration BO logo: {e}")

    # Cleanup: deletar edições concluídas há mais de 24h (mantém fila de importação limpa)
    try:
        with engine.begin() as conn:
            conn.execute(text("""
                DELETE FROM editor_edicoes
                WHERE status = 'concluido'
                  AND updated_at < NOW() - INTERVAL '24 hours'
            """))
            logger.info("Cleanup: edicoes concluidas > 24h deletadas OK")
    except Exception as e:
        logger.warning(f"Cleanup edicoes concluidas: {e}")

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
                ("font_file_r2_key", "VARCHAR(200)"),
                ("overlay_interval_secs", "INTEGER DEFAULT 6"),
                ("custom_post_structure", "TEXT"),
                ("brand_opening_line", "TEXT"),
                ("hashtag_count", "INTEGER"),
                ("sem_lyrics_default", "BOOLEAN NOT NULL DEFAULT FALSE"),
                ("overlay_cta", "TEXT"),
            ]:
                if col_name not in perfil_cols:
                    conn.execute(text(f"ALTER TABLE editor_perfis ADD COLUMN {col_name} {col_type}"))
                    logger.info(f"Migration: added column editor_perfis.{col_name}")
            logger.info("Migration: editor_perfis curadoria columns OK")

        # SPEC-009: RC é instrumental por padrão (após coluna existir)
        with engine.begin() as conn:
            conn.execute(text("""
                UPDATE editor_perfis SET sem_lyrics_default = TRUE
                WHERE sigla = 'RC' AND sem_lyrics_default = FALSE
            """))
            logger.info("Migration: SPEC-009 sem_lyrics_default RC = TRUE OK")

        # SPEC-010: Converter overlay_cta de JSON para TEXT (simplificação)
        with engine.begin() as conn:
            try:
                conn.execute(text("ALTER TABLE editor_perfis ALTER COLUMN overlay_cta TYPE TEXT USING overlay_cta::text"))
                logger.info("Migration: overlay_cta convertido de JSON para TEXT")
            except Exception:
                pass  # já é TEXT ou não existe — idempotente

        # SPEC-010: Seed CTA fixo para BO e RC (texto simples PT-BR)
        with engine.begin() as conn:
            conn.execute(text("""
                UPDATE editor_perfis SET overlay_cta = 'Siga para mais Best of Opera! 🎶'
                WHERE sigla = 'BO' AND (overlay_cta IS NULL OR overlay_cta = '' OR overlay_cta::text LIKE '{%')
            """))
            conn.execute(text("""
                UPDATE editor_perfis SET overlay_cta = 'Siga, o melhor da música clássica, diariamente no seu feed. ❤️'
                WHERE sigla = 'RC' AND (overlay_cta IS NULL OR overlay_cta = '' OR overlay_cta::text LIKE '{%')
            """))
            logger.info("SPEC-010: Seed overlay_cta BO e RC OK")

    # Migration: BO tipografia → Georgia Bold Italic + lyrics gold
    try:
        with engine.begin() as conn:
            conn.execute(text("""
                UPDATE editor_perfis SET
                    overlay_style = jsonb_set(
                        overlay_style::jsonb,
                        '{fontname}', '"Georgia"'
                    )::json,
                    lyrics_style = jsonb_set(
                        jsonb_set(
                            lyrics_style::jsonb,
                            '{fontname}', '"Georgia"'
                        ),
                        '{primarycolor}', '"#FFD700"'
                    )::json,
                    traducao_style = jsonb_set(
                        traducao_style::jsonb,
                        '{fontname}', '"Georgia"'
                    )::json,
                    font_name = 'Georgia'
                WHERE sigla = 'BO'
                  AND overlay_style->>'fontname' != 'Georgia'
            """))
            logger.info("Migration: BO tipografia Georgia Bold Italic + lyrics gold OK")
    except Exception as e:
        logger.warning(f"Migration BO Georgia: {e}")

    # Migration: BO fontsize reduzido (Georgia x-height maior) + CTA sem emoji
    try:
        with engine.begin() as conn:
            conn.execute(text("""
                UPDATE editor_perfis SET
                    overlay_style = jsonb_set(
                        jsonb_set(
                            jsonb_set(overlay_style::jsonb,
                                '{fontsize}', '42'),
                            '{gancho_fontsize}', '42'),
                        '{cta_fontsize}', '42'
                    )::json,
                    lyrics_style = jsonb_set(lyrics_style::jsonb, '{fontsize}', '42')::json,
                    traducao_style = jsonb_set(traducao_style::jsonb, '{fontsize}', '40')::json
                WHERE sigla = 'BO'
                  AND (overlay_style->>'fontsize')::int > 42
            """))
            conn.execute(text("""
                UPDATE editor_perfis SET
                    overlay_cta = 'Siga para mais Best of Opera!'
                WHERE sigla = 'BO'
                  AND overlay_cta LIKE '%🎶%'
            """))
            logger.info("Migration: BO fontsize reduzido + CTA sem emoji OK")
    except Exception as e:
        logger.warning(f"Migration BO fontsize/CTA: {e}")

    # Migration: BO overlay fontsize 42→44 (compensar ausência de outline na barra preta)
    try:
        with engine.begin() as conn:
            conn.execute(text("""
                UPDATE editor_perfis SET
                    overlay_style = jsonb_set(
                        jsonb_set(
                            jsonb_set(overlay_style::jsonb,
                                '{fontsize}', '44'),
                            '{gancho_fontsize}', '44'),
                        '{cta_fontsize}', '44'
                    )::json
                WHERE sigla = 'BO'
                  AND (overlay_style->>'fontsize')::int = 42
            """))
            logger.info("Migration: BO overlay fontsize 42→44 OK")
    except Exception as e:
        logger.warning(f"Migration BO overlay fontsize: {e}")

    # Migration: BO overlay fontsize 44→46 + lyrics cor #FFD700→#F0FF00
    try:
        with engine.begin() as conn:
            conn.execute(text("""
                UPDATE editor_perfis SET
                    overlay_style = jsonb_set(
                        jsonb_set(
                            jsonb_set(overlay_style::jsonb,
                                '{fontsize}', '46'),
                            '{gancho_fontsize}', '46'),
                        '{cta_fontsize}', '46'
                    )::json
                WHERE sigla = 'BO'
                  AND (overlay_style->>'fontsize')::int = 44
            """))
            conn.execute(text("""
                UPDATE editor_perfis SET
                    lyrics_style = jsonb_set(lyrics_style::jsonb,
                        '{primarycolor}', '"#F0FF00"'
                    )::json
                WHERE sigla = 'BO'
                  AND lyrics_style->>'primarycolor' = '#FFD700'
            """))
            logger.info("Migration: BO overlay 44→46 + lyrics cor #F0FF00 OK")
    except Exception as e:
        logger.warning(f"Migration BO overlay46/lyrics cor: {e}")

    # Migration: BO gap 8→10, overlay 46→48, tradução 40→42
    try:
        with engine.begin() as conn:
            conn.execute(text("""
                UPDATE editor_perfis SET
                    overlay_style = jsonb_set(overlay_style::jsonb,
                        '{gap_overlay_px}', '10'
                    )::json
                WHERE sigla = 'BO'
                  AND (overlay_style->>'gap_overlay_px')::int = 8
            """))
            conn.execute(text("""
                UPDATE editor_perfis SET
                    overlay_style = jsonb_set(
                        jsonb_set(
                            jsonb_set(overlay_style::jsonb,
                                '{fontsize}', '48'),
                            '{gancho_fontsize}', '48'),
                        '{cta_fontsize}', '48'
                    )::json
                WHERE sigla = 'BO'
                  AND (overlay_style->>'fontsize')::int = 46
            """))
            conn.execute(text("""
                UPDATE editor_perfis SET
                    traducao_style = jsonb_set(traducao_style::jsonb,
                        '{fontsize}', '42'
                    )::json
                WHERE sigla = 'BO'
                  AND (traducao_style->>'fontsize')::int = 40
            """))
            logger.info("Migration: BO gap 10, overlay 48, tradução 42 OK")
    except Exception as e:
        logger.warning(f"Migration BO gap/overlay48/trad42: {e}")

    # Migration: remover colunas obsoletas de editor_perfis
    if "editor_perfis" in insp.get_table_names():
        with engine.begin() as conn:
            perfil_cols = [c["name"] for c in insp.get_columns("editor_perfis")]
            for col_name in ("duracao_corte_min", "duracao_corte_max"):
                if col_name in perfil_cols:
                    conn.execute(text(f"ALTER TABLE editor_perfis DROP COLUMN {col_name}"))
                    logger.info(f"Migration: dropped column editor_perfis.{col_name}")

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
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_editor_edicoes_status ON editor_edicoes (status)"))
        conn.execute(text("ALTER TABLE editor_usuarios ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN DEFAULT FALSE"))
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
                "ON editor_traducoes_letra (edicao_id, idioma)"
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

    # Migration: published_at em editor_edicoes
    if "editor_edicoes" in insp.get_table_names():
        edicao_cols = [c["name"] for c in insp.get_columns("editor_edicoes")]
        if "published_at" not in edicao_cols:
            with engine.begin() as conn:
                try:
                    conn.execute(text("ALTER TABLE editor_edicoes ADD COLUMN published_at TIMESTAMP"))
                    logger.info("Migration editor_edicoes: added column published_at")
                except Exception as e:
                    logger.warning(f"Migration editor_edicoes/published_at: {e}")

    # Migration: tabela editor_reports (criada pelo create_all, mas garantir colunas)
    if "editor_reports" in insp.get_table_names():
        report_cols = [c["name"] for c in insp.get_columns("editor_reports")]
        with engine.begin() as conn:
            for col_name, col_type in [
                ("prioridade", "VARCHAR(20) DEFAULT 'media'"),
                ("resolvido_em", "TIMESTAMP"),
                ("updated_at", "TIMESTAMP"),
                ("colaborador", "VARCHAR(200)"),
                ("projeto_id", "INTEGER"),
                ("screenshots_json", "TEXT DEFAULT '[]'"),
                ("resolucao", "TEXT"),
                ("resolvido_por", "VARCHAR(200)"),
                ("codigo_err", "VARCHAR(50)"),
            ]:
                if col_name not in report_cols:
                    try:
                        conn.execute(text(f"ALTER TABLE editor_reports ADD COLUMN {col_name} {col_type}"))
                        logger.info(f"Migration editor_reports: added column {col_name}")
                    except Exception as e:
                        logger.warning(f"Migration editor_reports/{col_name}: {e}")

    # Migration: updated_at em editor_overlays
    if "editor_overlays" in insp.get_table_names():
        overlay_cols = [c["name"] for c in insp.get_columns("editor_overlays")]
        if "updated_at" not in overlay_cols:
            with engine.begin() as conn:
                try:
                    conn.execute(text("ALTER TABLE editor_overlays ADD COLUMN updated_at TIMESTAMP DEFAULT NOW()"))
                    conn.execute(text("UPDATE editor_overlays SET updated_at = created_at"))
                    logger.info("Migration editor_overlays: added column updated_at")
                except Exception as e:
                    logger.warning(f"Migration editor_overlays/updated_at: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Log FFmpeg version no startup (diagnóstico de qualidade)
    import subprocess as _sp
    try:
        _r = _sp.run(["ffmpeg", "-version"], capture_output=True, text=True, timeout=5)
        _lines = _r.stdout.strip().split("\n")
        print(f"[FFMPEG VERSION] {_lines[0]}", flush=True)
        for _l in _lines[1:4]:
            print(f"[FFMPEG VERSION] {_l}", flush=True)
    except Exception:
        print("[FFMPEG VERSION] não encontrado", flush=True)
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

# Proxy headers — Railway termina HTTPS no edge, FastAPI vê HTTP.
# Sem isso, redirect_slashes gera Location: http://... → Mixed Content.
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=["*"])

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
