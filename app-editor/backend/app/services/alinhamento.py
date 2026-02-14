"""Serviço de alinhamento: fuzzy matching letra × timestamps."""
import re
import logging
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


def normalizar(texto: str) -> str:
    texto = texto.lower()
    texto = re.sub(r"\[.*?\]", "", texto)
    texto = re.sub(r"[^\w\s]", "", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def encontrar_melhor_match(texto: str, versos: list) -> tuple:
    """Encontra o verso mais similar via fuzzy matching."""
    texto_norm = normalizar(texto)
    melhor_score = 0
    melhor_verso = ""
    melhor_indice = None

    for i, verso in enumerate(versos):
        verso_norm = normalizar(verso)
        score = SequenceMatcher(None, texto_norm, verso_norm).ratio()
        if verso_norm in texto_norm or texto_norm in verso_norm:
            score = max(score, 0.85)
        if score > melhor_score:
            melhor_score = score
            melhor_verso = verso
            melhor_indice = i

    # Combinações de versos consecutivos
    for i in range(len(versos) - 1):
        combinado = versos[i] + " " + versos[i + 1]
        combinado_norm = normalizar(combinado)
        score = SequenceMatcher(None, texto_norm, combinado_norm).ratio()
        if score > melhor_score:
            melhor_score = score
            melhor_verso = combinado
            melhor_indice = i

    return melhor_verso, melhor_score, melhor_indice


def alinhar_letra_com_timestamps(letra_original: str, srt_gemini: list) -> dict:
    """Merge da letra original com timestamps do Gemini."""
    versos = [v.strip() for v in letra_original.split("\n") if v.strip()]
    versos_limpos = [re.sub(r"^\[.*?\]\s*", "", v) for v in versos]

    resultado = []

    for segmento in srt_gemini:
        texto_gemini = segmento.get("text", "")

        if "[TEXTO NÃO IDENTIFICADO" in texto_gemini:
            resultado.append({
                **segmento,
                "texto_final": texto_gemini,
                "flag": "ROXO",
                "confianca": 0.0,
            })
            continue

        eh_repeticao = "[REPETIÇÃO]" in texto_gemini
        if eh_repeticao:
            texto_gemini = texto_gemini.replace("[REPETIÇÃO]", "").strip()

        match, score, indice = encontrar_melhor_match(texto_gemini, versos_limpos)
        texto_original = versos[indice] if indice is not None else texto_gemini

        if score >= 0.85:
            resultado.append({
                **segmento,
                "texto_final": texto_original,
                "flag": "VERDE",
                "confianca": score,
                "eh_repeticao": eh_repeticao,
            })
        elif score >= 0.50:
            resultado.append({
                **segmento,
                "texto_final": texto_original,
                "texto_gemini": segmento.get("text", ""),
                "flag": "AMARELO",
                "confianca": score,
                "eh_repeticao": eh_repeticao,
            })
        else:
            resultado.append({
                **segmento,
                "texto_final": segmento.get("text", ""),
                "candidato_letra": texto_original,
                "flag": "VERMELHO",
                "confianca": score,
                "eh_repeticao": eh_repeticao,
            })

    confiancas = [s["confianca"] for s in resultado if s["flag"] != "ROXO"]
    media = sum(confiancas) / len(confiancas) if confiancas else 0
    vermelhos = sum(1 for s in resultado if s["flag"] == "VERMELHO")
    total = len(resultado)

    if media >= 0.85 and vermelhos == 0:
        rota = "A"
    elif media >= 0.60 and (vermelhos / total < 0.3 if total > 0 else True):
        rota = "B"
    else:
        rota = "C"

    return {
        "segmentos": resultado,
        "confianca_media": round(media, 3),
        "total_verde": sum(1 for s in resultado if s["flag"] == "VERDE"),
        "total_amarelo": sum(1 for s in resultado if s["flag"] == "AMARELO"),
        "total_vermelho": vermelhos,
        "total_roxo": sum(1 for s in resultado if s["flag"] == "ROXO"),
        "rota": rota,
    }


def _parse_timestamp_sec(ts: str) -> float:
    """Converte timestamp string para segundos.
    Suporta: HH:MM:SS,mmm | MM:SS,mmm | MM:SS:mmm (Gemini às vezes usa : no ms)."""
    if not ts:
        return 0.0
    ts = ts.replace(",", ".")
    parts = ts.split(":")
    try:
        if len(parts) == 3:
            a, b, c = parts
            c_val = float(c)
            # Se c >= 100, é milissegundos (formato MM:SS:mmm do Gemini)
            # Se c < 60, é segundos (formato HH:MM:SS)
            if c_val >= 100:
                # MM:SS:mmm → minutos:segundos:milissegundos
                return int(a) * 60 + int(b) + c_val / 1000.0
            else:
                # HH:MM:SS.frac
                return int(a) * 3600 + int(b) * 60 + c_val
        elif len(parts) == 2:
            m, s = parts
            return int(m) * 60 + float(s)
        else:
            return float(ts)
    except (ValueError, TypeError):
        return 0.0


def _seconds_to_ts(sec: float) -> str:
    """Converte segundos para MM:SS,mmm."""
    m = int(sec) // 60
    s = sec - m * 60
    whole = int(s)
    ms = int(round((s - whole) * 1000))
    return f"{m:02d}:{whole:02d},{ms:03d}"


def merge_transcricoes(cega: list, guiada: list, letra_original: str) -> dict:
    """Merge inteligente com âncoras + interpolação.

    Estratégia:
    1. Ordenar ambas por tempo
    2. Matching sequencial monotônico: cada guiado tenta match no próximo cego
    3. Segmentos guiados que matcham → âncoras (timestamp da cega)
    4. Segmentos guiados sem match → timestamps interpolados entre âncoras vizinhas
    5. Nunca usa timestamps "crus" da guiada (são imprecisos)
    """
    versos = [v.strip() for v in letra_original.split("\n") if v.strip()]
    versos_limpos = [re.sub(r"^\[.*?\]\s*", "", v) for v in versos]

    # Ordenar ambas por tempo
    def _sort_key(seg):
        return _parse_timestamp_sec(seg.get("start", "0"))

    guiada_sorted = sorted(guiada, key=_sort_key)
    cega_sorted = sorted(cega, key=_sort_key)

    # Pré-processar cegos
    cegos_info = []
    for seg in cega_sorted:
        cegos_info.append({
            "seg": seg,
            "text_norm": normalizar(seg.get("text", "")),
            "start_sec": _parse_timestamp_sec(seg.get("start", "")),
            "end_sec": _parse_timestamp_sec(seg.get("end", "")),
        })

    n_cegos = len(cegos_info)
    n_guiados = len(guiada_sorted)

    # ===== FASE 1: Matching sequencial monotônico =====
    # Para cada guiado, tentar match no próximo cego disponível (janela forward)
    matches = []  # lista de (guiado_idx, cego_idx, score)
    cursor_cego = 0

    for gi, seg_guiado in enumerate(guiada_sorted):
        texto_guiado = seg_guiado.get("text", "")
        guiado_norm = normalizar(texto_guiado.replace("[REPETIÇÃO]", "").strip())

        WINDOW = 6
        melhor_score = 0
        melhor_ci = None

        for ci in range(cursor_cego, min(n_cegos, cursor_cego + WINDOW)):
            info = cegos_info[ci]
            score = SequenceMatcher(None, guiado_norm, info["text_norm"]).ratio()
            # Bonus containment
            if info["text_norm"] and guiado_norm:
                if info["text_norm"] in guiado_norm or guiado_norm in info["text_norm"]:
                    score = max(score, 0.8)
            if score > melhor_score:
                melhor_score = score
                melhor_ci = ci

        if melhor_ci is not None and melhor_score >= 0.35:
            matches.append((gi, melhor_ci, melhor_score))
            cursor_cego = melhor_ci + 1
            logger.debug(
                f"ANCHOR gi={gi} ↔ ci={melhor_ci} score={melhor_score:.2f} | "
                f"'{guiado_norm[:30]}' ↔ '{cegos_info[melhor_ci]['text_norm'][:30]}'"
            )

    logger.info(f"MERGE fase 1: {len(matches)} âncoras de {n_guiados} guiados × {n_cegos} cegos")

    # ===== FASE 2: Construir resultado com interpolação =====
    # Cada guiado recebe timestamps: âncora direta ou interpolado entre âncoras

    # Criar mapa gi → (start_sec, end_sec, flag, confianca, fonte)
    anchor_map = {}
    for gi, ci, score in matches:
        info = cegos_info[ci]
        anchor_map[gi] = {
            "start_sec": info["start_sec"],
            "end_sec": info["end_sec"],
            "score": score,
        }

    # Para cada guiado não-âncora, interpolar entre âncoras vizinhas
    # Encontrar âncoras anterior e posterior
    anchor_gis = sorted(anchor_map.keys())

    def _find_prev_next_anchor(gi):
        prev_anchor = None
        next_anchor = None
        for a in anchor_gis:
            if a < gi:
                prev_anchor = a
            elif a > gi:
                next_anchor = a
                break
        return prev_anchor, next_anchor

    resultado = []
    for gi, seg_guiado in enumerate(guiada_sorted):
        texto_guiado = seg_guiado.get("text", "")
        eh_repeticao = "[REPETIÇÃO]" in texto_guiado
        texto_limpo = texto_guiado.replace("[REPETIÇÃO]", "").strip() if eh_repeticao else texto_guiado

        # Match com letra original
        match_letra, score_letra, indice_letra = encontrar_melhor_match(texto_limpo, versos_limpos)
        texto_final = versos[indice_letra] if indice_letra is not None else texto_guiado

        if gi in anchor_map:
            # Âncora direta: timestamp da cega
            anc = anchor_map[gi]
            flag = "VERDE" if anc["score"] >= 0.5 else "AMARELO"
            resultado.append({
                "index": gi + 1,
                "start": _seconds_to_ts(anc["start_sec"]),
                "end": _seconds_to_ts(anc["end_sec"]),
                "text": texto_guiado,
                "texto_final": texto_final,
                "flag": flag,
                "confianca": round(anc["score"], 3),
                "eh_repeticao": eh_repeticao,
                "fonte_timestamp": "cega",
            })
        else:
            # Interpolar entre âncoras vizinhas
            prev_gi, next_gi = _find_prev_next_anchor(gi)

            if prev_gi is not None and next_gi is not None:
                # Interpolação linear entre duas âncoras
                prev_end = anchor_map[prev_gi]["end_sec"]
                next_start = anchor_map[next_gi]["start_sec"]
                span = next_start - prev_end
                # Quantos segmentos sem âncora existem entre prev e next?
                n_between = next_gi - prev_gi - 1
                if n_between > 0 and span > 0:
                    pos_in_gap = gi - prev_gi  # 1-based position in gap
                    seg_duration = span / (n_between + 1)
                    start_sec = prev_end + (pos_in_gap - 0.5) * seg_duration
                    end_sec = start_sec + seg_duration * 0.9
                else:
                    start_sec = prev_end + 0.5
                    end_sec = start_sec + 3.0
                flag = "AMARELO"
                conf = 0.3
            elif prev_gi is not None:
                # Só âncora anterior: extrapolar para frente
                prev_end = anchor_map[prev_gi]["end_sec"]
                pos_after = gi - prev_gi
                start_sec = prev_end + pos_after * 3.0
                end_sec = start_sec + 3.0
                flag = "AMARELO"
                conf = 0.2
            elif next_gi is not None:
                # Só âncora posterior: extrapolar para trás
                next_start = anchor_map[next_gi]["start_sec"]
                pos_before = next_gi - gi
                start_sec = max(0, next_start - pos_before * 3.0)
                end_sec = start_sec + 3.0
                flag = "AMARELO"
                conf = 0.2
            else:
                # Nenhuma âncora: fallback para guiada
                start_sec = _parse_timestamp_sec(seg_guiado.get("start", "0"))
                end_sec = _parse_timestamp_sec(seg_guiado.get("end", "0"))
                flag = "VERMELHO"
                conf = 0.1

            resultado.append({
                "index": gi + 1,
                "start": _seconds_to_ts(start_sec),
                "end": _seconds_to_ts(end_sec),
                "text": texto_guiado,
                "texto_final": texto_final,
                "flag": flag,
                "confianca": round(conf, 3),
                "eh_repeticao": eh_repeticao,
                "fonte_timestamp": "interpolado",
            })

    # Garantir ordenação por tempo e sem sobreposições
    resultado.sort(key=lambda s: _parse_timestamp_sec(s.get("start", "0")))
    for i in range(len(resultado) - 1):
        cur_end = _parse_timestamp_sec(resultado[i]["end"])
        next_start = _parse_timestamp_sec(resultado[i + 1]["start"])
        if cur_end > next_start:
            resultado[i]["end"] = _seconds_to_ts(max(0, next_start - 0.1))

    # Reindexar
    for i, seg in enumerate(resultado):
        seg["index"] = i + 1

    # Estatísticas
    confiancas = [s["confianca"] for s in resultado]
    media = sum(confiancas) / len(confiancas) if confiancas else 0
    vermelhos = sum(1 for s in resultado if s["flag"] == "VERMELHO")
    total = len(resultado)

    if media >= 0.85 and vermelhos == 0:
        rota = "A"
    elif media >= 0.60 and (vermelhos / total < 0.3 if total > 0 else True):
        rota = "B"
    else:
        rota = "C"

    total_verde = sum(1 for s in resultado if s["flag"] == "VERDE")
    total_amarelo = sum(1 for s in resultado if s["flag"] == "AMARELO")
    total_roxo = sum(1 for s in resultado if s["flag"] == "ROXO")

    logger.info(
        f"MERGE resultado: {total_verde}V {total_amarelo}A {vermelhos}R {total_roxo}X | "
        f"confiança={media:.3f} rota={rota} | {len(matches)} âncoras"
    )

    return {
        "segmentos": resultado,
        "confianca_media": round(media, 3),
        "total_verde": total_verde,
        "total_amarelo": total_amarelo,
        "total_vermelho": vermelhos,
        "total_roxo": total_roxo,
        "rota": rota,
    }
