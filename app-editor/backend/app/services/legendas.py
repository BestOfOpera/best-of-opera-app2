"""Serviço de geração de arquivos ASS com 3 tracks de legenda."""
import logging
from typing import Optional
import pysubs2
from app.services.regua import timestamp_to_seconds, seconds_to_timestamp

logger = logging.getLogger(__name__)

ESTILOS_PADRAO = {
    "overlay": {
        "fontname": "TeX Gyre Pagella",
        "fontsize": 63,
        "primarycolor": "#FFFFFF",
        "outlinecolor": "#000000",
        "outline": 3,
        "shadow": 1,
        "alignment": 2,
        "marginv": 1296,
        "bold": True,
        "italic": False,
    },
    "lyrics": {
        "fontname": "TeX Gyre Pagella",
        "fontsize": 45,
        "primarycolor": "#FFFF64",
        "outlinecolor": "#000000",
        "outline": 2,
        "shadow": 0,
        "alignment": 2,
        "marginv": 573,
        "bold": True,
        "italic": True,
    },
    "traducao": {
        "fontname": "TeX Gyre Pagella",
        "fontsize": 43,
        "primarycolor": "#FFFFFF",
        "outlinecolor": "#000000",
        "outline": 2,
        "shadow": 0,
        "alignment": 8,
        "marginv": 1353,
        "bold": True,
        "italic": True,
    },
}

OVERLAY_MAX_CHARS = 70
OVERLAY_MAX_CHARS_LINHA = 35
LYRICS_MAX_CHARS = 43
TRADUCAO_MAX_CHARS = 100


def hex_to_ssa_color(hex_color: str) -> pysubs2.Color:
    """Converte hex (#RRGGBB) para pysubs2.Color."""
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return pysubs2.Color(r, g, b, 0)


def seg_to_ms(value) -> int:
    """Converte valor para milissegundos."""
    if value is None:
        return 0
    # Delegar para timestamp_to_seconds para lidar com heurística de s vs ms
    sec = timestamp_to_seconds(value)
    return int(sec * 1000)


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


def _formatar_overlay(texto: str, max_por_linha: int = 30) -> str:
    """Garante overlay com max 2 linhas equilibradas, max_por_linha chars cada."""
    texto = texto.strip()
    if len(texto) <= max_por_linha:
        return texto
    # Se já tem quebra manual (\n ou \\N), verificar cada linha
    for sep in ["\\N", "\n"]:
        if sep in texto:
            linhas = texto.split(sep)
            formatadas = []
            for l in linhas[:2]:
                l = l.strip()
                if len(l) > max_por_linha:
                    l = _truncar_texto(l, max_por_linha)
                formatadas.append(l)
            return "\\N".join(formatadas)
    # Sem quebra — inserir \\N no ponto mais equilibrado
    meio = len(texto) // 2
    pos_esq = texto.rfind(" ", 0, meio + 1)
    pos_dir = texto.find(" ", meio)
    if pos_esq == -1 and pos_dir == -1:
        return texto[:max_por_linha - 1].rstrip() + "…"
    candidatos = []
    if pos_esq != -1:
        l1, l2 = texto[:pos_esq].strip(), texto[pos_esq:].strip()
        candidatos.append((abs(len(l1) - len(l2)), l1, l2))
    if pos_dir != -1 and pos_dir != pos_esq:
        l1, l2 = texto[:pos_dir].strip(), texto[pos_dir:].strip()
        candidatos.append((abs(len(l1) - len(l2)), l1, l2))
    candidatos.sort(key=lambda x: x[0])
    _, linha1, linha2 = candidatos[0]
    # Guarda: menor linha >= 35% do total
    total = len(linha1) + len(linha2)
    if min(len(linha1), len(linha2)) < total * 0.35:
        for offset in range(1, meio):
            for pos in [texto.rfind(" ", 0, meio - offset + 1), texto.find(" ", meio + offset)]:
                if pos is not None and pos > 0:
                    l1 = texto[:pos].strip()
                    l2 = texto[pos:].strip()
                    if min(len(l1), len(l2)) >= (len(l1) + len(l2)) * 0.35:
                        linha1, linha2 = l1, l2
                        break
            else:
                continue
            break
    if len(linha1) > max_por_linha:
        linha1 = _truncar_texto(linha1, max_por_linha)
    if len(linha2) > max_por_linha:
        linha2 = _truncar_texto(linha2, max_por_linha)
    return linha1 + "\\N" + linha2


def _truncar_texto(texto: str, max_chars: int) -> str:
    """Trunca texto que excede max_chars, cortando no último espaço.
    Garante que nenhuma palavra seja cortada ao meio.
    Adiciona '...' no final."""
    if len(texto) <= max_chars:
        return texto
    
    # Limite efetivo para o texto antes dos pontos
    limite = max_chars - 3
    if limite <= 0:
        return "..."
    
    # Pega o trecho até o limite
    cortado = texto[:limite]
    
    # Tenta encontrar o último espaço ANTES do limite
    ultimo_espaco = cortado.rfind(" ")
    
    if ultimo_espaco != -1:
        # Trunca no espaço encontrado
        return cortado[:ultimo_espaco].rstrip() + "..."
    
    # Em caso de palavra única maior que o limite, trunca no limite (fallback)
    return cortado.rstrip() + "..."


def corrigir_timestamps_sobrepostos(segmentos: list) -> list:
    """Garante que nenhum segmento sobrepõe o próximo.
    Chamado automaticamente antes de gerar legendas."""
    if not segmentos:
        return segmentos
    result = [dict(s) for s in segmentos]
    for i in range(len(result) - 1):
        s1 = timestamp_to_seconds(result[i].get("start", "0"))
        e1 = timestamp_to_seconds(result[i].get("end", "0"))
        s2 = timestamp_to_seconds(result[i + 1].get("start", "0"))

        if e1 > s2:
            # Garante que o fim não ultrapassa o início do próximo, mas também não fica menor que o próprio início
            result[i]["end"] = seconds_to_timestamp(max(s1 + 0.1, s2 - 0.1))
    
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
    sem_lyrics: bool = False,
) -> pysubs2.SSAFile:
    """Gera arquivo ASS com até 3 tracks.

    Quando sem_lyrics=True, gera apenas a track de overlay (topo),
    omitindo completamente as tracks de lyrics e tradução.
    """
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
    # Cada overlay dura até o próximo; último até o fim do corte
    overlay_filtrado = [seg for seg in overlay if seg.get("text")]

    # Bug B: Garantir ordenação temporal antes de processar os overlays
    def _get_start_ms(s):
        k = "start" if "start" in s else ("timestamp" if "timestamp" in s else "start")
        return seg_to_ms(s.get(k, 0))

    overlay_filtrado.sort(key=_get_start_ms)

    # Detectar caso degenerado: todos os timestamps iguais (ex: todos zerados)
    overlay_starts = [_get_start_ms(s) for s in overlay_filtrado]
    todos_iguais = len(overlay_filtrado) > 1 and len(set(overlay_starts)) <= 1

    for i, seg in enumerate(overlay_filtrado):
        event = pysubs2.SSAEvent()
        start_ms = _get_start_ms(seg)

        if todos_iguais and duracao_total_ms > 0:
            # Fallback: distribuir igualmente pelo vídeo quando timestamps são todos iguais
            n = len(overlay_filtrado)
            interval = duracao_total_ms // n
            event.start = i * interval
            event.end = (i + 1) * interval
        else:
            event.start = start_ms
            # End: prioridade para o campo 'end' se existir, senão usa o próximo start
            end_ms = seg_to_ms(seg.get("end")) if "end" in seg else 0
            
            if end_ms > event.start:
                event.end = end_ms
            elif i + 1 < len(overlay_filtrado):
                next_start_ms = _get_start_ms(overlay_filtrado[i + 1])
                # Garante que o fim é pelo menos 1ms após o início, e idealmente o próximo start
                event.end = max(event.start + 1, next_start_ms)
            else:
                # Último overlay: até o fim do corte
                event.end = duracao_total_ms if duracao_total_ms > event.start else event.start + 10000

        # Garantir duração mínima de 2s para legibilidade, a menos que o próximo sobreponha
        if i + 1 < len(overlay_filtrado):
            next_start_ms = _get_start_ms(overlay_filtrado[i + 1])
            # Se der pra expandir pra 2s sem atropelar o próximo, expande
            if event.end - event.start < 2000 and next_start_ms > event.start + 2000:
                event.end = event.start + 2000
        else:
            # Último: força 2s se possível
            if event.end - event.start < 2000:
                event.end = event.start + 2000

        texto = seg["text"]
        texto_original = texto
        texto = _formatar_overlay(texto, OVERLAY_MAX_CHARS_LINHA)
        if texto != texto_original:
            logger.info(f"[legendas] Overlay formatado: {len(texto_original)}→{len(texto)} chars")
        event.text = "{\\q2}" + texto
        event.style = "Overlay"
        subs.events.append(event)

    if sem_lyrics:
        logger.info("[legendas] sem_lyrics=True: omitindo tracks de lyrics e tradução")
        return subs

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
        start_ms = seg_to_ms(seg.get("start", 0))
        end_ms = seg_to_ms(seg.get("end", 0))

        # ERR-055: Filtrar segmentos com duração <= 0
        if end_ms <= start_ms:
            logger.warning(f"[legendas] Segmento de lyrics descartado (duração zero ou negativa) em idx={idx}: {start_ms} - {end_ms}")
            continue

        logger.info(f"[legendas] Lyrics segment: idx={idx} {start_ms} - {end_ms} '{text[:30]}...'")

        event = pysubs2.SSAEvent()
        event.start = start_ms
        event.end = end_ms
        texto = text
        texto_original = texto
        texto = _truncar_texto(texto, LYRICS_MAX_CHARS)
        if texto != texto_original:
            logger.warning(f"[legendas] Lyrics truncado: '{texto_original[:50]}' ({len(texto_original)}→{len(texto)})")
        event.text = "{\\q2}" + texto
        event.style = "Lyrics"
        subs.events.append(event)

        # Tradução (mesmo timing que lyrics)
        if precisa_traducao and idx in traducao_por_index:
            trad_seg = traducao_por_index[idx]
            event_trad = pysubs2.SSAEvent()
            event_trad.start = event.start
            event_trad.end = event.end
            texto_trad = trad_seg["traducao"]
            texto_trad_original = texto_trad
            texto_trad = _truncar_texto(texto_trad, TRADUCAO_MAX_CHARS)
            if texto_trad != texto_trad_original:
                logger.warning(f"[legendas] Tradução truncado: '{texto_trad_original[:50]}' ({len(texto_trad_original)}→{len(texto_trad)})")
            event_trad.text = texto_trad
            event_trad.style = "Traducao"
            subs.events.append(event_trad)

    return subs
