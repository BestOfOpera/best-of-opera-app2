"""Serviço de geração de arquivos ASS com 3 tracks de legenda."""
import logging
from typing import Optional
import pysubs2
from app.services.regua import timestamp_to_seconds, seconds_to_timestamp

logger = logging.getLogger(__name__)

ESTILOS_PADRAO = {
    "overlay": {
        "fontname": "TeX Gyre Schola",
        "fontsize": 40,
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
        "fontname": "TeX Gyre Schola",
        "fontsize": 30,
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
        "fontname": "TeX Gyre Schola",
        "fontsize": 30,
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
OVERLAY_MAX_CHARS_LINHA = 30
LYRICS_MAX_CHARS = 43
TRADUCAO_MAX_CHARS = 100


def _estilos_do_perfil(perfil) -> dict:
    """Converte campos JSON do Perfil para dict de estilos ASS.
    Retorna estrutura idêntica a ESTILOS_PADRAO.

    Merge: ESTILOS_PADRAO como base, sobrescrito pelos valores do perfil.
    Garante que mesmo estilos parciais ou dicts vazios tenham todas as chaves.

    Se perfil.font_name estiver definido, sobrescreve o fontname em todos
    os estilos — isso garante que a fonte customizada do perfil seja usada
    mesmo que os JSONs de estilo no banco ainda tenham o nome antigo.
    """
    _TRACK_ATTRS = {
        "overlay": "overlay_style",
        "lyrics": "lyrics_style",
        "traducao": "traducao_style",
    }
    estilos = {}
    for track, attr in _TRACK_ATTRS.items():
        perfil_style = getattr(perfil, attr, None)
        merged = dict(ESTILOS_PADRAO[track])  # copia defaults
        if perfil_style and isinstance(perfil_style, dict):
            merged.update(perfil_style)  # sobrescreve com valores do perfil
        estilos[track] = merged
    # font_name do perfil é o default global — override APENAS em tracks
    # que não definem fontname explícito no JSON de estilo.
    # Se lyrics_style ou traducao_style já trazem fontname (ex: "Poppins"),
    # o font_name do perfil (ex: "Inter Display") NÃO sobrescreve.
    font_override = getattr(perfil, "font_name", None)
    if font_override:
        for track_name, track_style in estilos.items():
            perfil_style_json = getattr(perfil, _TRACK_ATTRS[track_name], None)
            # Só sobrescrever se o JSON do track NÃO tem fontname explícito
            if not (perfil_style_json and isinstance(perfil_style_json, dict) and "fontname" in perfil_style_json):
                track_style["fontname"] = font_override
    return estilos


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


def _formatar_overlay(texto: str, max_por_linha: int = 30, pre_formatted: bool = False) -> str:
    """Garante overlay com max 2 linhas equilibradas, max_por_linha chars cada.
    Se pre_formatted=True, apenas converte \\n→\\\\N sem truncar ou reformatar."""
    texto = texto.strip()
    # Converter newlines Python para quebras ASS antes de qualquer lógica
    texto = texto.replace("\n", "\\N")
    if pre_formatted:
        return texto
    if len(texto) <= max_por_linha:
        return texto
    # Se já tem quebra manual (\N, newline ou \n literal dois chars), verificar cada linha
    for sep in ["\\N", "\n", "\\n"]:
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
    perfil=None,
    image_top_px: Optional[int] = None,
    duracao_video_ms: Optional[int] = None,
) -> pysubs2.SSAFile:
    """Gera arquivo ASS com até 3 tracks.

    Quando sem_lyrics=True, gera apenas a track de overlay (topo),
    omitindo completamente as tracks de lyrics e tradução.

    Se perfil fornecido, usa estilos e limites do perfil.
    Caso contrário, usa ESTILOS_PADRAO e constantes globais (retrocompatibilidade).
    """
    if perfil is not None:
        estilos = _estilos_do_perfil(perfil)
        overlay_max_linha = perfil.overlay_max_chars_linha or OVERLAY_MAX_CHARS_LINHA
        lyrics_max = perfil.lyrics_max_chars or LYRICS_MAX_CHARS
        traducao_max = perfil.traducao_max_chars or TRADUCAO_MAX_CHARS
        play_res_x = str(perfil.video_width or 1080)
        play_res_y = str(perfil.video_height or 1920)
    else:
        estilos = estilos or ESTILOS_PADRAO
        overlay_max_linha = OVERLAY_MAX_CHARS_LINHA
        lyrics_max = LYRICS_MAX_CHARS
        traducao_max = TRADUCAO_MAX_CHARS
        play_res_x = "1080"
        play_res_y = "1920"

    subs = pysubs2.SSAFile()
    subs.info["PlayResX"] = play_res_x
    subs.info["PlayResY"] = play_res_y

    # Recalcular marginv do overlay, lyrics e traducao baseado na posição real da imagem
    if image_top_px is not None:
        frame_h = int(subs.info.get("PlayResY", "1920"))
        estilos = dict(estilos)

        # Overlay: posiciona acima da imagem
        overlay_alignment = estilos.get("overlay", {}).get("alignment", 2)
        if overlay_alignment >= 7:
            # Top alignment (7/8/9): perfil define marginv fixo (pré-calculado).
            # NÃO recalcular — valores como gancho_marginv/corpo_marginv/cta_marginv
            # são aplicados via inline \pos tags por evento.
            estilos["overlay"] = dict(estilos["overlay"])
        else:
            # Bottom alignment (1/2/3): calcular dinamicamente
            overlay_gap = estilos.get("overlay", {}).get("gap_overlay_px", 28)
            estilos["overlay"] = dict(estilos["overlay"])
            estilos["overlay"]["marginv"] = frame_h - (image_top_px - overlay_gap)

        # Lyrics: posiciona abaixo da imagem (na barra preta inferior)
        # image_top_px == pad_y == altura da barra preta (topo e base são iguais)
        fontsize_lyrics = estilos.get("lyrics", {}).get("fontsize", 30)
        text_height = int(fontsize_lyrics * 1.3)  # altura aproximada de uma linha renderizada
        gap_from_image = 10  # gap entre borda inferior da imagem e texto
        inter_line_gap = 6   # gap entre lyrics e traducao
        lyrics_marginv = image_top_px - gap_from_image - text_height
        estilos["lyrics"] = dict(estilos["lyrics"])
        estilos["lyrics"]["marginv"] = lyrics_marginv

        # Traducao: posiciona logo abaixo das lyrics
        estilos["traducao"] = dict(estilos["traducao"])
        estilos["traducao"]["marginv"] = frame_h - lyrics_marginv + inter_line_gap

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
        style.spacing = config.get("spacing", 0)
        style.marginl = config.get("marginl", 0)
        style.marginr = config.get("marginr", 0)
        subs.styles[nome.capitalize()] = style

    # Corrigir timestamps antes de gerar
    lyrics = corrigir_timestamps_sobrepostos(lyrics)

    # Calcular duração total do corte (último timestamp dos lyrics)
    duracao_total_ms = 0
    for seg in lyrics:
        end_ms = seg_to_ms(seg.get("end", 0))
        if end_ms > duracao_total_ms:
            duracao_total_ms = end_ms

    # Fallback: se lyrics vazios (instrumental), usar duração real do vídeo
    if duracao_total_ms == 0 and duracao_video_ms:
        duracao_total_ms = duracao_video_ms

    # Track 1: Overlay (com word wrap e timing contínuo)
    # Cada overlay dura até o próximo; último até o fim do corte
    overlay_filtrado = [seg for seg in overlay if seg.get("text")]

    logger.info(
        f"[legendas] OVERLAY DIAGNÓSTICO: "
        f"{len(overlay)} segs recebidos, {len(overlay_filtrado)} após filtro texto, "
        f"duracao_total_ms={duracao_total_ms}, sem_lyrics={sem_lyrics}"
    )
    for idx, seg in enumerate(overlay_filtrado):
        logger.info(
            f"[legendas]   seg[{idx}]: text='{seg.get('text', '')[:50]}' "
            f"timestamp={seg.get('timestamp')} start={seg.get('start')} end={seg.get('end')}"
        )

    # Bug B: Garantir ordenação temporal antes de processar os overlays
    def _get_start_ms(s):
        k = "start" if "start" in s else ("timestamp" if "timestamp" in s else "start")
        return seg_to_ms(s.get(k, 0))

    # Separar CTA (flag _is_cta) para garantir que seja sempre o último,
    # independente do timestamp (fix: CTA aparecia antes da última narrativa)
    cta_seg = None
    overlay_sem_cta = []
    for seg in overlay_filtrado:
        if seg.get("_is_cta"):
            cta_seg = seg
        else:
            overlay_sem_cta.append(seg)

    overlay_sem_cta.sort(key=_get_start_ms)
    if cta_seg:
        # Garantir que CTA comece DEPOIS da última narrativa.
        # Se CTA tem timestamp <= última narrativa, ajustar para 2s depois.
        # Sem isso, overlays anteriores estendem end até a última narrativa,
        # sobrepondo visualmente com o CTA que começa antes.
        if overlay_sem_cta:
            last_narrative_ms = _get_start_ms(overlay_sem_cta[-1])
            cta_ms = _get_start_ms(cta_seg)
            if cta_ms <= last_narrative_ms:
                new_cta_s = (last_narrative_ms + 2000) / 1000
                cta_seg = dict(cta_seg)  # não mutar original
                if "timestamp" in cta_seg:
                    cta_seg["timestamp"] = seconds_to_timestamp(new_cta_s)
                if "start" in cta_seg:
                    cta_seg["start"] = seconds_to_timestamp(new_cta_s)
                logger.info(
                    f"[legendas] CTA timestamp ajustado: {cta_ms}ms → {last_narrative_ms + 2000}ms "
                    f"(última narrativa em {last_narrative_ms}ms)"
                )
        overlay_sem_cta.append(cta_seg)
    overlay_filtrado = overlay_sem_cta

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
                event.end = duracao_total_ms if duracao_total_ms > event.start else event.start + 5000

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
        _pre_fmt = estilos.get("overlay", {}).get("overlay_pre_formatted", False)
        if i == 0:
            logger.info(
                f"[legendas] OVERLAY CONFIG: pre_formatted={_pre_fmt} "
                f"max_linha={overlay_max_linha} alignment={estilos.get('overlay', {}).get('alignment')}"
            )
        texto = _formatar_overlay(texto, overlay_max_linha, pre_formatted=_pre_fmt)
        if texto != texto_original:
            logger.info(f"[legendas] Overlay formatado: {len(texto_original)}→{len(texto)} chars")

        # Tags de tamanho e posição por sub-estilo: gancho (1ª) / corpo (meio) / CTA (última)
        overlay_estilo = estilos.get("overlay", {})
        gancho_fs = overlay_estilo.get("gancho_fontsize")
        corpo_fs = overlay_estilo.get("corpo_fontsize")
        cta_fs = overlay_estilo.get("cta_fontsize")

        fs_tag = ""
        pos_tag = ""
        if gancho_fs and i == 0:
            fs_tag = f"{{\\fs{gancho_fs}}}"
        elif cta_fs and i == len(overlay_filtrado) - 1:
            fs_tag = f"{{\\fs{cta_fs}}}"
        elif corpo_fs:
            fs_tag = f"{{\\fs{corpo_fs}}}"

        # Posicionamento dinâmico por sub-estilo para perfis top-aligned (alignment >= 7)
        # Calcula \pos(X,Y) por evento baseado no número real de linhas do texto.
        # Ativado quando o perfil define gancho_gap/corpo_gap/cta_gap no overlay_style.
        overlay_alignment = estilos.get("overlay", {}).get("alignment", 2)
        _has_dynamic_pos = overlay_alignment >= 7 and any(
            overlay_estilo.get(k) is not None
            for k in ("gancho_gap", "corpo_gap", "cta_gap")
        )
        if _has_dynamic_pos:
            # Configuração por sub-estilo
            _substyle = {
                "gancho": {
                    "fontsize": overlay_estilo.get("gancho_fontsize", overlay_estilo.get("fontsize", 48)),
                    "gap": overlay_estilo.get("gancho_gap", overlay_estilo.get("gap_overlay_px", 15)),
                    "line_spacing": overlay_estilo.get("gancho_line_spacing", 10),
                },
                "corpo": {
                    "fontsize": overlay_estilo.get("corpo_fontsize", overlay_estilo.get("fontsize", 48)),
                    "gap": overlay_estilo.get("corpo_gap", overlay_estilo.get("gap_overlay_px", 18)),
                    "line_spacing": overlay_estilo.get("corpo_line_spacing", 9),
                },
                "cta": {
                    "fontsize": overlay_estilo.get("cta_fontsize", overlay_estilo.get("fontsize", 44)),
                    "gap": overlay_estilo.get("cta_gap", overlay_estilo.get("gap_overlay_px", 20)),
                    "line_spacing": overlay_estilo.get("cta_line_spacing", 12),
                },
            }
            # video_top dinâmico: usa image_top_px (calculado por probar_video + calcular_image_top)
            # Fallback 555 = (1920-810)//2 para crop 4:3 de input 16:9 padrão
            _VIDEO_TOP = image_top_px if image_top_px is not None else 555

            # Determinar tipo do evento
            is_cta = seg.get("_is_cta", False) or (i == len(overlay_filtrado) - 1 and cta_seg is not None and seg is cta_seg)
            is_gancho = (i == 0 and not is_cta)
            if is_cta:
                cfg = _substyle["cta"]
            elif is_gancho:
                cfg = _substyle["gancho"]
            else:
                cfg = _substyle["corpo"]

            # Contar linhas reais do texto formatado (\\N é quebra ASS)
            num_lines = texto.count("\\N") + 1

            # Calcular altura do bloco de texto
            line_h = round(cfg["fontsize"] * 0.926)  # cap-height ratio
            block_h = line_h * num_lines + cfg["line_spacing"] * (num_lines - 1)

            # Y = video_top - gap - block_h (borda inferior do bloco acima do vídeo)
            pos_y = _VIDEO_TOP - cfg["gap"] - block_h

            _play_res_x = int(subs.info.get("PlayResX", "1080"))
            _center_x = _play_res_x // 2
            pos_tag = f"{{\\an8\\pos({_center_x},{pos_y})}}"

        event.text = "{\\q2}" + pos_tag + fs_tag + texto
        event.style = "Overlay"
        subs.events.append(event)

        # Log CTA (último overlay) para diagnóstico
        if i == len(overlay_filtrado) - 1:
            logger.info(
                f"[legendas] CTA DIAGNÓSTICO: "
                f"text='{texto_original[:60]}' start={event.start}ms end={event.end}ms "
                f"duracao={event.end - event.start}ms fs_tag='{fs_tag}'"
            )

    if sem_lyrics:
        logger.info("[legendas] sem_lyrics=True: omitindo tracks de lyrics e tradução")
        return subs

    # Preparar lista de traduções por POSIÇÃO (match sequencial, não por index)
    precisa_traducao = idioma_versao != idioma_musica and traducao
    traducao_list = list(traducao) if precisa_traducao else []

    if precisa_traducao:
        logger.info(
            f"[legendas] Tradução: {len(traducao_list)} segs para {len(lyrics)} lyrics "
            f"(idioma_versao={idioma_versao}, idioma_musica={idioma_musica})"
        )

    # Tracks 2 e 3: Lyrics + Tradução (sincronizados por posição sequencial)
    lyrics_renderizados = 0
    lyrics_pulados = 0
    for i, seg in enumerate(lyrics):
        text = seg.get("texto_final", seg.get("text", ""))
        idx = seg.get("index", i + 1)

        if not text:
            logger.info(f"[legendas] Lyrics seg pos={i} idx={idx} pulado: texto vazio")
            lyrics_pulados += 1
            continue

        # Lyrics
        start_ms = seg_to_ms(seg.get("start", 0))
        end_ms = seg_to_ms(seg.get("end", 0))

        # ERR-055: Filtrar segmentos com duração <= 0
        if end_ms <= start_ms:
            logger.warning(
                f"[legendas] Lyrics seg pos={i} idx={idx} pulado: "
                f"duração zero ou negativa (start={start_ms}ms end={end_ms}ms)"
            )
            lyrics_pulados += 1
            continue

        # Se precisa tradução mas não tem para esta posição, pular
        if precisa_traducao and i >= len(traducao_list):
            logger.warning(
                f"[legendas] Lyrics seg pos={i} idx={idx} pulado: "
                f"sem tradução na posição {i} (traducao tem {len(traducao_list)} segs)"
            )
            lyrics_pulados += 1
            continue

        logger.info(f"[legendas] Lyrics segment: pos={i} idx={idx} {start_ms}-{end_ms}ms '{text[:30]}...'")

        event = pysubs2.SSAEvent()
        event.start = start_ms
        event.end = end_ms
        texto = text
        texto_original = texto
        texto = _truncar_texto(texto, lyrics_max)
        if texto != texto_original:
            logger.warning(f"[legendas] Lyrics truncado: '{texto_original[:50]}' ({len(texto_original)}→{len(texto)})")
        event.text = "{\\q2}" + texto
        event.style = "Lyrics"
        subs.events.append(event)
        lyrics_renderizados += 1

        # Tradução (mesmo timing que lyrics, match por posição)
        if precisa_traducao and i < len(traducao_list):
            trad_seg = traducao_list[i]
            texto_trad = trad_seg.get("traducao", "")
            if texto_trad:
                event_trad = pysubs2.SSAEvent()
                event_trad.start = event.start
                event_trad.end = event.end
                texto_trad_original = texto_trad
                texto_trad = _truncar_texto(texto_trad, traducao_max)
                if texto_trad != texto_trad_original:
                    logger.warning(f"[legendas] Tradução truncado: '{texto_trad_original[:50]}' ({len(texto_trad_original)}→{len(texto_trad)})")
                event_trad.text = texto_trad
                event_trad.style = "Traducao"
                subs.events.append(event_trad)
            else:
                logger.warning(f"[legendas] Tradução vazia na posição {i} para lyrics idx={idx}")

    logger.info(f"[legendas] Lyrics totais: {lyrics_renderizados} renderizados, {lyrics_pulados} pulados de {len(lyrics)}")

    return subs
