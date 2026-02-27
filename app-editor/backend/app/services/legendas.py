"""Serviço de geração de arquivos ASS com 3 tracks de legenda."""
from typing import Optional
import pysubs2
from app.services.regua import timestamp_to_seconds, seconds_to_timestamp

# Layout para vídeo 16:9 dentro de frame 9:16 (1080x1920)
# Vídeo escala para 1080x608, centralizado verticalmente
# Barras pretas: 656px em cima, vídeo 608px (y=656..1264), 656px embaixo
# Legendas na barra preta inferior, simétrico ao overlay no topo.
# Cada track tem max 2 linhas (84px com fontsize=35+outline=2).
# lyrics: marginv=500 → y_base=1420, 2 linhas topo em 1336, gap ao vídeo=72px
# traducao: marginv=380 → y_base=1540, gap ao lyrics base=36px
ESTILOS_PADRAO = {
    "overlay": {
        "fontname": "Georgia",
        "fontsize": 47,
        "primarycolor": "#FFFFFF",
        "outlinecolor": "#000000",
        "outline": 3,
        "shadow": 1,
        "alignment": 8,   # topo
        "marginv": 530,    # 2 linhas cabem sem invadir vídeo (gap 16px)
        "bold": True,
        "italic": True,
    },
    "lyrics": {
        "fontname": "Georgia",
        "fontsize": 35,
        "primarycolor": "#FFFF64",
        "outlinecolor": "#000000",
        "outline": 2,
        "shadow": 0,
        "alignment": 2,   # base
        "marginv": 500,    # y_base=1420 — barra preta inferior, 72px gap ao vídeo (simétrico ao overlay)
        "bold": True,
        "italic": True,
    },
    "traducao": {
        "fontname": "Georgia",
        "fontsize": 35,
        "primarycolor": "#FFFFFF",
        "outlinecolor": "#000000",
        "outline": 2,
        "shadow": 0,
        "alignment": 2,   # base
        "marginv": 380,    # y_base=1540 — 36px abaixo do lyrics, barra preta inferior
        "bold": True,
        "italic": True,
    },
}

OVERLAY_MAX_CHARS = 35


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


def quebrar_texto_overlay(texto: str, max_chars: int = OVERLAY_MAX_CHARS) -> str:
    """Quebra texto em 2 linhas equilibradas se exceder max_chars.
    Encontra o ponto de quebra mais próximo do meio, sem cortar palavras.
    Usa \\N (line break do ASS) para separar."""
    if len(texto) <= max_chars:
        return texto
    palavras = texto.split()
    if len(palavras) <= 1:
        return texto
    # Encontrar o ponto de quebra que deixa as 2 linhas mais equilibradas
    meio = len(texto) / 2
    melhor_quebra = 0
    melhor_diff = len(texto)
    pos = 0
    for i, palavra in enumerate(palavras[:-1]):
        pos += len(palavra) + (1 if i > 0 else 0)
        diff = abs(pos - meio)
        if diff < melhor_diff:
            melhor_diff = diff
            melhor_quebra = i + 1
    linha1 = " ".join(palavras[:melhor_quebra])
    linha2 = " ".join(palavras[melhor_quebra:])
    return linha1 + "\\N" + linha2


def _formatar_texto_legenda(texto: str, max_chars: int = 40, max_linhas: int = 2) -> str:
    """Quebra texto longo em linhas de até max_chars, máximo max_linhas.
    Usa \\N como separador de linha (padrão ASS)."""
    if not texto:
        return texto

    # Normalizar: remover quebras ASS existentes
    texto_limpo = texto.replace("\\N", " ").replace("\\n", " ").strip()

    if len(texto_limpo) <= max_chars:
        return texto_limpo

    # Word-wrap em linhas de até max_chars
    palavras = texto_limpo.split()
    linhas = []
    linha_atual = ""

    for palavra in palavras:
        candidata = (linha_atual + " " + palavra).strip() if linha_atual else palavra
        if len(candidata) <= max_chars:
            linha_atual = candidata
        else:
            if linha_atual:
                linhas.append(linha_atual)
            linha_atual = palavra

    if linha_atual:
        linhas.append(linha_atual)

    # Limitar a max_linhas
    linhas = linhas[:max_linhas]

    return "\\N".join(linhas)


def corrigir_timestamps_sobrepostos(segmentos: list) -> list:
    """Garante que nenhum segmento sobrepõe o próximo.
    Chamado automaticamente antes de gerar legendas."""
    if not segmentos:
        return segmentos
    result = [dict(s) for s in segmentos]
    for i in range(len(result) - 1):
        end_sec = timestamp_to_seconds(result[i].get("end", "0"))
        next_start_sec = timestamp_to_seconds(result[i + 1].get("start", "0"))
        if end_sec > next_start_sec:
            result[i]["end"] = seconds_to_timestamp(max(0, next_start_sec - 0.1))
    # Último segmento: garantir duração mínima de 2s
    last = result[-1]
    start_sec = timestamp_to_seconds(last.get("start", "0"))
    end_sec = timestamp_to_seconds(last.get("end", "0"))
    if end_sec - start_sec < 2.0:
        last["end"] = seconds_to_timestamp(start_sec + 2.0)
    return result


def gerar_ass(
    overlay: list,
    lyrics: list,
    traducao: Optional[list],
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

    # Corrigir timestamps antes de gerar
    lyrics = corrigir_timestamps_sobrepostos(lyrics)

    # Calcular duração total do corte (último timestamp dos lyrics)
    duracao_total_ms = 0
    for seg in lyrics:
        end_ms = seg_to_ms(seg.get("end", 0))
        if end_ms > duracao_total_ms:
            duracao_total_ms = end_ms

    # Track 1: Overlay (com word wrap e timing contínuo)
    # Cada overlay dura até 1s antes do próximo; último até o fim do corte
    overlay_filtrado = [seg for seg in overlay if seg.get("text")]

    # Detectar caso degenerado: todos os timestamps iguais (ex: todos zerados)
    def _get_start_ms(s):
        k = "start" if "start" in s else "timestamp"
        return seg_to_ms(s.get(k, 0))

    overlay_starts = [_get_start_ms(s) for s in overlay_filtrado]
    todos_iguais = len(overlay_filtrado) > 1 and len(set(overlay_starts)) <= 1

    for i, seg in enumerate(overlay_filtrado):
        event = pysubs2.SSAEvent()

        if todos_iguais and duracao_total_ms > 0:
            # Fallback: distribuir igualmente pelo vídeo quando timestamps são todos iguais
            n = len(overlay_filtrado)
            interval = duracao_total_ms // n
            event.start = i * interval
            event.end = (i + 1) * interval
        else:
            start_key = "start" if "start" in seg else "timestamp"
            event.start = seg_to_ms(seg.get(start_key, 0))
            # End = próximo overlay - 1s gap, ou fim do vídeo
            if i + 1 < len(overlay_filtrado):
                next_seg = overlay_filtrado[i + 1]
                next_start_key = "start" if "start" in next_seg else "timestamp"
                next_start_ms = seg_to_ms(next_seg.get(next_start_key, 0))
                event.end = max(event.start + 1, next_start_ms - 1000)  # 1s gap
            else:
                # Último overlay: até o fim do corte
                event.end = duracao_total_ms if duracao_total_ms > 0 else event.start + 10000

        # Garantir duração mínima de 2s
        if event.end - event.start < 2000:
            event.end = event.start + 2000
        event.text = quebrar_texto_overlay(seg["text"], max_chars=OVERLAY_MAX_CHARS)
        event.style = "Overlay"
        subs.events.append(event)

    # Preparar mapa de traduções por index (para sincronizar lyrics ↔ tradução)
    precisa_traducao = idioma_versao != idioma_musica and traducao
    traducao_por_index = {}
    if precisa_traducao:
        for seg in traducao:
            idx = seg.get("index")
            if idx is not None and seg.get("traducao"):
                traducao_por_index[idx] = seg

    # Tracks 2 e 3: Lyrics + Tradução (sincronizados)
    # Regra: se a versão precisa de tradução, lyrics SÓ aparece quando
    # tiver tradução correspondente. Nunca lyrics sem tradução.
    for seg in lyrics:
        text = seg.get("texto_final", seg.get("text", ""))
        if not text:
            continue

        idx = seg.get("index")

        # Se precisa tradução mas não tem para este segmento, pular
        if precisa_traducao and idx not in traducao_por_index:
            continue

        # Lyrics
        event = pysubs2.SSAEvent()
        event.start = seg_to_ms(seg.get("start", 0))
        event.end = seg_to_ms(seg.get("end", 0))
        event.text = _formatar_texto_legenda(text)
        event.style = "Lyrics"
        subs.events.append(event)

        # Tradução (mesmo timing que lyrics)
        if precisa_traducao and idx in traducao_por_index:
            trad_seg = traducao_por_index[idx]
            event_trad = pysubs2.SSAEvent()
            event_trad.start = event.start
            event_trad.end = event.end
            event_trad.text = _formatar_texto_legenda(trad_seg["traducao"])
            event_trad.style = "Traducao"
            subs.events.append(event_trad)

    return subs
