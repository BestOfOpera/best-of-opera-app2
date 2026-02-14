"""Serviço de geração de arquivos ASS com 3 tracks de legenda."""
import pysubs2
from app.services.regua import timestamp_to_seconds

ESTILOS_PADRAO = {
    "overlay": {
        "fontname": "Georgia",
        "fontsize": 42,
        "primarycolor": "#FFFFFF",
        "outlinecolor": "#000000",
        "outline": 2,
        "shadow": 1,
        "alignment": 8,
        "marginv": 80,
        "bold": True,
        "italic": False,
    },
    "lyrics": {
        "fontname": "Georgia",
        "fontsize": 36,
        "primarycolor": "#FFFF64",
        "outlinecolor": "#000000",
        "outline": 2,
        "shadow": 0,
        "alignment": 2,
        "marginv": 130,
        "bold": False,
        "italic": True,
    },
    "traducao": {
        "fontname": "Georgia",
        "fontsize": 30,
        "primarycolor": "#DCDCDC",
        "outlinecolor": "#000000",
        "outline": 1.5,
        "shadow": 0,
        "alignment": 2,
        "marginv": 60,
        "bold": False,
        "italic": False,
    },
}


def hex_to_ssa_color(hex_color: str) -> pysubs2.Color:
    """Converte hex (#RRGGBB) para pysubs2.Color."""
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return pysubs2.Color(r, g, b, 0)


def seg_to_ms(value) -> int:
    """Converte valor para milissegundos."""
    if isinstance(value, (int, float)):
        return int(value * 1000)
    if isinstance(value, str):
        return int(timestamp_to_seconds(value) * 1000)
    return 0


def gerar_ass(
    overlay: list,
    lyrics: list,
    traducao: list | None,
    idioma_versao: str,
    idioma_musica: str,
    estilos: dict = None,
) -> pysubs2.SSAFile:
    """Gera arquivo ASS com até 3 tracks."""
    estilos = estilos or ESTILOS_PADRAO
    subs = pysubs2.SSAFile()
    subs.info["PlayResX"] = "1080"
    subs.info["PlayResY"] = "1920"

    # Criar estilos
    for nome, config in estilos.items():
        style = pysubs2.SSAStyle()
        style.fontname = config["fontname"]
        style.fontsize = config["fontsize"]
        style.primarycolor = hex_to_ssa_color(config["primarycolor"])
        style.outlinecolor = hex_to_ssa_color(config["outlinecolor"])
        style.outline = config.get("outline", 2)
        style.shadow = config.get("shadow", 0)
        style.alignment = config["alignment"]
        style.marginv = config["marginv"]
        style.bold = config.get("bold", False)
        style.italic = config.get("italic", False)
        subs.styles[nome.capitalize()] = style

    # Track 1: Overlay
    for seg in overlay:
        if not seg.get("text"):
            continue
        event = pysubs2.SSAEvent()
        start_key = "start" if "start" in seg else "timestamp"
        event.start = seg_to_ms(seg.get(start_key, 0))
        # Duração padrão de 4s se não tiver end
        default_end = seg.get(start_key, 0)
        if isinstance(default_end, str):
            default_end = timestamp_to_seconds(default_end) + 4
        else:
            default_end = default_end + 4
        event.end = seg_to_ms(seg.get("end", default_end))
        event.text = seg["text"]
        event.style = "Overlay"
        subs.events.append(event)

    # Track 2: Lyrics
    for seg in lyrics:
        text = seg.get("texto_final", seg.get("text", ""))
        if not text:
            continue
        event = pysubs2.SSAEvent()
        event.start = seg_to_ms(seg.get("start", 0))
        event.end = seg_to_ms(seg.get("end", 0))
        event.text = text
        event.style = "Lyrics"
        subs.events.append(event)

    # Track 3: Tradução
    if idioma_versao != idioma_musica and traducao:
        for seg in traducao:
            text = seg.get("traducao", "")
            if not text:
                continue
            event = pysubs2.SSAEvent()
            event.start = seg_to_ms(seg.get("start", 0))
            event.end = seg_to_ms(seg.get("end", 0))
            event.text = text
            event.style = "Traducao"
            subs.events.append(event)

    return subs
