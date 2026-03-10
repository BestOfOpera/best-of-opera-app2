"""Testes unitários críticos — BLAST v4 Fase 2: Multi-brand."""
import pytest
from types import SimpleNamespace

from app.services.legendas import (
    ESTILOS_PADRAO,
    _estilos_do_perfil,
    gerar_ass,
)
from app.models.perfil import Perfil


# ---------------------------------------------------------------------------
# 1. _estilos_do_perfil retorna ESTILOS_PADRAO quando campos são None
# ---------------------------------------------------------------------------
def test_estilos_do_perfil_retorna_padrao_quando_none():
    perfil = SimpleNamespace(
        overlay_style=None,
        lyrics_style=None,
        traducao_style=None,
    )
    result = _estilos_do_perfil(perfil)
    assert result["overlay"] == ESTILOS_PADRAO["overlay"]
    assert result["lyrics"] == ESTILOS_PADRAO["lyrics"]
    assert result["traducao"] == ESTILOS_PADRAO["traducao"]


# ---------------------------------------------------------------------------
# 2. _estilos_do_perfil retorna estilos custom quando fornecidos
# ---------------------------------------------------------------------------
def test_estilos_do_perfil_retorna_custom():
    custom_overlay = {
        "fontname": "Arial", "fontsize": 50,
        "primarycolor": "#FF0000", "outlinecolor": "#000000",
        "outline": 2, "shadow": 0, "alignment": 2, "marginv": 1000,
        "bold": False, "italic": False,
    }
    perfil = SimpleNamespace(
        overlay_style=custom_overlay,
        lyrics_style=None,
        traducao_style=None,
    )
    result = _estilos_do_perfil(perfil)
    assert result["overlay"] == custom_overlay
    assert result["overlay"]["fontname"] == "Arial"
    assert result["overlay"]["fontsize"] == 50
    # lyrics e traducao caem para padrão
    assert result["lyrics"] == ESTILOS_PADRAO["lyrics"]


# ---------------------------------------------------------------------------
# 3. Seed Best of Opera tem valores idênticos ao ESTILOS_PADRAO
# ---------------------------------------------------------------------------
def test_seed_best_of_opera_valores_corretos():
    # Validar os valores do seed diretamente contra ESTILOS_PADRAO
    seed_overlay = {
        "fontname": "TeX Gyre Pagella", "fontsize": 63,
        "primarycolor": "#FFFFFF", "outlinecolor": "#000000",
        "outline": 3, "shadow": 1, "alignment": 2, "marginv": 1296,
        "bold": True, "italic": False,
    }
    seed_lyrics = {
        "fontname": "TeX Gyre Pagella", "fontsize": 45,
        "primarycolor": "#FFFF64", "outlinecolor": "#000000",
        "outline": 2, "shadow": 0, "alignment": 2, "marginv": 573,
        "bold": True, "italic": True,
    }
    seed_traducao = {
        "fontname": "TeX Gyre Pagella", "fontsize": 43,
        "primarycolor": "#FFFFFF", "outlinecolor": "#000000",
        "outline": 2, "shadow": 0, "alignment": 8, "marginv": 1353,
        "bold": True, "italic": True,
    }
    assert seed_overlay == ESTILOS_PADRAO["overlay"], "overlay seed diverge do ESTILOS_PADRAO"
    assert seed_lyrics == ESTILOS_PADRAO["lyrics"], "lyrics seed diverge do ESTILOS_PADRAO"
    assert seed_traducao == ESTILOS_PADRAO["traducao"], "traducao seed diverge do ESTILOS_PADRAO"


# ---------------------------------------------------------------------------
# 4. gerar_ass com perfil custom usa fontsize diferente no output ASS
# ---------------------------------------------------------------------------
def test_gerar_ass_com_perfil_custom():
    custom_overlay = dict(ESTILOS_PADRAO["overlay"])
    custom_overlay["fontsize"] = 99  # fontsize diferente
    perfil = SimpleNamespace(
        overlay_style=custom_overlay,
        lyrics_style=None,
        traducao_style=None,
        overlay_max_chars_linha=35,
        lyrics_max_chars=43,
        traducao_max_chars=100,
        video_width=1080,
        video_height=1920,
    )
    overlay = [{"text": "Test overlay", "start": "00:00", "end": "00:05"}]
    lyrics = [{"text": "Test lyrics", "start": "00:00,000", "end": "00:05,000", "index": 0}]

    result = gerar_ass(
        overlay=overlay,
        lyrics=lyrics,
        traducao=None,
        idioma_versao="pt",
        idioma_musica="pt",
        perfil=perfil,
    )

    ass_str = result.to_string("ass")
    assert "99" in ass_str  # fontsize 99 deve aparecer no output ASS
    # Verificar que o estilo Overlay existe no ASS
    assert "Overlay" in ass_str


# ---------------------------------------------------------------------------
# 5. gerar_ass sem perfil é retrocompatível com comportamento atual
# ---------------------------------------------------------------------------
def test_gerar_ass_sem_perfil_retrocompativel():
    overlay = [{"text": "Test overlay", "start": "00:00", "end": "00:05"}]
    lyrics = [{"text": "Test lyrics", "start": "00:00,000", "end": "00:05,000", "index": 0}]

    # Com perfil=None (retrocompatível)
    result_sem = gerar_ass(
        overlay=overlay,
        lyrics=lyrics,
        traducao=None,
        idioma_versao="pt",
        idioma_musica="pt",
        perfil=None,
    )
    # Com estilos=None (comportamento original)
    result_orig = gerar_ass(
        overlay=overlay,
        lyrics=lyrics,
        traducao=None,
        idioma_versao="pt",
        idioma_musica="pt",
    )

    # PlayRes deve ser identico
    assert result_sem.info["PlayResX"] == result_orig.info["PlayResX"]
    assert result_sem.info["PlayResY"] == result_orig.info["PlayResY"]
    # Mesma quantidade de events
    assert len(result_sem.events) == len(result_orig.events)


# ---------------------------------------------------------------------------
# 6. _detect_music_lang com set de 4 idiomas customizado
# ---------------------------------------------------------------------------
def test_detect_music_lang_com_idiomas_custom():
    from app.routes.importar import _detect_music_lang

    proj = {
        "translations": [
            {"language": "pt"},
            {"language": "en"},
            {"language": "es"},
        ]
    }
    # Com 4 idiomas: {pt, en, es, de} → faltante excluindo pt editorial = {de}
    result = _detect_music_lang(proj, idiomas_alvo={"pt", "en", "es", "de"})
    assert result == "de"


# ---------------------------------------------------------------------------
# 7. Perfil slug deve ser único (constraint no modelo)
# ---------------------------------------------------------------------------
def test_perfil_slug_unico(db_session):
    p1 = Perfil(nome="Marca A", sigla="MA", slug="marca-a")
    p2 = Perfil(nome="Marca B", sigla="MB", slug="marca-a")  # mesmo slug
    db_session.add(p1)
    db_session.flush()
    db_session.add(p2)
    with pytest.raises(Exception):  # IntegrityError ou similar
        db_session.flush()


# ---------------------------------------------------------------------------
# 8. Edicao sem perfil_id funciona (retrocompatibilidade)
# ---------------------------------------------------------------------------
def test_edicao_perfil_nullable(db_session):
    from app.models.edicao import Edicao as _Edicao
    edicao = _Edicao(
        youtube_url="https://youtube.com/watch?v=test",
        youtube_video_id="test",
        artista="Artista",
        musica="Musica",
        idioma="it",
        perfil_id=None,  # nullable — deve funcionar
    )
    db_session.add(edicao)
    db_session.flush()
    assert edicao.id is not None
    assert edicao.perfil_id is None
