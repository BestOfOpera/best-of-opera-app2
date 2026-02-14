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
    """Converte timestamp string para segundos. Suporta HH:MM:SS,mmm e MM:SS:mmm."""
    if not ts:
        return 0.0
    ts = ts.replace(",", ".")
    parts = ts.split(":")
    try:
        if len(parts) == 3:
            h, m, s = parts
            return int(h) * 3600 + int(m) * 60 + float(s)
        elif len(parts) == 2:
            m, s = parts
            return int(m) * 60 + float(s)
        else:
            return float(ts)
    except (ValueError, TypeError):
        return 0.0


def merge_transcricoes(cega: list, guiada: list, letra_original: str) -> dict:
    """Merge inteligente: texto da guiada + timestamps da cega.

    Para cada segmento guiado, busca o melhor match na transcrição cega
    via fuzzy matching de texto + proximidade temporal.
    Usa timestamps da cega (mais precisos) com texto da guiada (correto).
    """
    versos = [v.strip() for v in letra_original.split("\n") if v.strip()]
    versos_limpos = [re.sub(r"^\[.*?\]\s*", "", v) for v in versos]

    # Pré-processar segmentos cegos com timestamps em segundos
    cegos_info = []
    for seg in cega:
        cegos_info.append({
            "seg": seg,
            "text_norm": normalizar(seg.get("text", "")),
            "start_sec": _parse_timestamp_sec(seg.get("start", "")),
            "end_sec": _parse_timestamp_sec(seg.get("end", "")),
            "usado": False,
        })

    resultado = []

    for segmento_guiado in guiada:
        texto_guiado = segmento_guiado.get("text", "")
        guiado_start = _parse_timestamp_sec(segmento_guiado.get("start", ""))
        guiado_norm = normalizar(texto_guiado)

        # Encontrar melhor match na transcrição cega
        melhor_score_total = 0
        melhor_cego_idx = None

        for i, ci in enumerate(cegos_info):
            if ci["usado"]:
                continue

            # Score de similaridade textual
            score_texto = SequenceMatcher(None, guiado_norm, ci["text_norm"]).ratio()

            # Bonus se um contém o outro
            if ci["text_norm"] in guiado_norm or guiado_norm in ci["text_norm"]:
                score_texto = max(score_texto, 0.85)

            # Score de proximidade temporal (penaliza distância > 10s)
            dist_temporal = abs(guiado_start - ci["start_sec"])
            score_temporal = max(0, 1.0 - dist_temporal / 30.0)

            # Score combinado: texto pesa mais (70%) que temporal (30%)
            score_total = score_texto * 0.7 + score_temporal * 0.3

            if score_total > melhor_score_total:
                melhor_score_total = score_total
                melhor_cego_idx = i

        # Determinar texto final via match com letra original
        eh_repeticao = "[REPETIÇÃO]" in texto_guiado
        texto_limpo = texto_guiado.replace("[REPETIÇÃO]", "").strip() if eh_repeticao else texto_guiado
        match_letra, score_letra, indice_letra = encontrar_melhor_match(texto_limpo, versos_limpos)
        texto_final = versos[indice_letra] if indice_letra is not None else texto_guiado

        if melhor_cego_idx is not None and melhor_score_total >= 0.5:
            # Match bom: usar timestamps da cega, texto da guiada
            cego_seg = cegos_info[melhor_cego_idx]["seg"]
            cegos_info[melhor_cego_idx]["usado"] = True

            score_texto_puro = SequenceMatcher(
                None, guiado_norm, cegos_info[melhor_cego_idx]["text_norm"]
            ).ratio()

            resultado.append({
                "index": segmento_guiado.get("index"),
                "start": cego_seg.get("start"),
                "end": cego_seg.get("end"),
                "text": texto_guiado,
                "texto_final": texto_final,
                "flag": "VERDE",
                "confianca": round(score_texto_puro, 3),
                "eh_repeticao": eh_repeticao,
                "fonte_timestamp": "cega",
            })
            logger.debug(
                f"MERGE #{segmento_guiado.get('index')}: "
                f"match={score_texto_puro:.2f} | "
                f"cego='{cego_seg.get('text', '')[:40]}' → guiado='{texto_guiado[:40]}'"
            )
        else:
            # Match fraco: fallback para timestamps da guiada
            flag = "AMARELO"
            if score_letra < 0.5:
                flag = "VERMELHO"

            resultado.append({
                "index": segmento_guiado.get("index"),
                "start": segmento_guiado.get("start"),
                "end": segmento_guiado.get("end"),
                "text": texto_guiado,
                "texto_final": texto_final,
                "flag": flag,
                "confianca": round(melhor_score_total, 3),
                "eh_repeticao": eh_repeticao,
                "fonte_timestamp": "guiada",
            })
            logger.debug(
                f"MERGE #{segmento_guiado.get('index')}: SEM MATCH (score={melhor_score_total:.2f}) | "
                f"fallback guiada='{texto_guiado[:40]}'"
            )

    # Segmentos da cega sem correspondência na guiada → ROXO (possível texto extra)
    for ci in cegos_info:
        if not ci["usado"]:
            texto_cego = ci["seg"].get("text", "")
            if normalizar(texto_cego):  # ignorar segmentos vazios
                resultado.append({
                    "index": None,
                    "start": ci["seg"].get("start"),
                    "end": ci["seg"].get("end"),
                    "text": texto_cego,
                    "texto_final": texto_cego,
                    "flag": "ROXO",
                    "confianca": 0.0,
                    "fonte_timestamp": "cega",
                })

    # Reindexar
    for i, seg in enumerate(resultado):
        seg["index"] = i + 1

    # Estatísticas
    confiancas = [s["confianca"] for s in resultado if s["flag"] not in ("ROXO",)]
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
        f"confiança={media:.3f} rota={rota}"
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
