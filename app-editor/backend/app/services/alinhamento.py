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
    """Merge: texto da guiada + timestamps da cega.

    Estratégia:
    1. Busca global: cada guiado procura o melhor cego (texto + proximidade temporal)
    2. Mark-used: cegos já usados não são reutilizados
    3. Threshold 0.5: rejeita matches fracos
    4. Fallback: se não acha match, usa timestamps originais da guiada (reais, não inventados)
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
            "usado": False,
        })

    n_cegos = len(cegos_info)

    # ===== Matching global com mark-used =====
    resultado = []
    matched_count = 0

    for gi, seg_guiado in enumerate(guiada_sorted):
        texto_guiado = seg_guiado.get("text", "")
        eh_repeticao = "[REPETIÇÃO]" in texto_guiado
        texto_limpo = texto_guiado.replace("[REPETIÇÃO]", "").strip() if eh_repeticao else texto_guiado
        guiado_norm = normalizar(texto_limpo)
        guiado_start_sec = _parse_timestamp_sec(seg_guiado.get("start", "0"))

        # Match com letra original
        match_letra, score_letra, indice_letra = encontrar_melhor_match(texto_limpo, versos_limpos)
        texto_final = versos[indice_letra] if indice_letra is not None else texto_guiado

        # Buscar melhor cego (busca global, pula usados)
        melhor_score_total = 0
        melhor_ci = None

        for ci, info in enumerate(cegos_info):
            if info["usado"]:
                continue
            score_texto = SequenceMatcher(None, guiado_norm, info["text_norm"]).ratio()
            # Bonus containment
            if info["text_norm"] and guiado_norm:
                if info["text_norm"] in guiado_norm or guiado_norm in info["text_norm"]:
                    score_texto = max(score_texto, 0.85)
            # Penalidade temporal (quanto mais longe no tempo, pior)
            dist = abs(guiado_start_sec - info["start_sec"])
            score_temporal = max(0, 1.0 - dist / 30.0)
            score_total = score_texto * 0.7 + score_temporal * 0.3

            if score_total > melhor_score_total:
                melhor_score_total = score_total
                melhor_ci = ci

        if melhor_ci is not None and melhor_score_total >= 0.5:
            # Match encontrado: usar timestamps da cega
            info = cegos_info[melhor_ci]
            info["usado"] = True
            matched_count += 1

            flag = "VERDE" if melhor_score_total >= 0.75 else "AMARELO"
            resultado.append({
                "index": gi + 1,
                "start": _seconds_to_ts(info["start_sec"]),
                "end": _seconds_to_ts(info["end_sec"]),
                "text": texto_guiado,
                "texto_final": texto_final,
                "flag": flag,
                "confianca": round(melhor_score_total, 3),
                "eh_repeticao": eh_repeticao,
                "fonte_timestamp": "cega",
            })
        else:
            # Sem match: fallback para timestamps originais da guiada
            start_sec = _parse_timestamp_sec(seg_guiado.get("start", "0"))
            end_sec = _parse_timestamp_sec(seg_guiado.get("end", "0"))
            resultado.append({
                "index": gi + 1,
                "start": _seconds_to_ts(start_sec),
                "end": _seconds_to_ts(end_sec),
                "text": texto_guiado,
                "texto_final": texto_final,
                "texto_gemini": texto_guiado,
                "flag": "VERMELHO",
                "confianca": round(melhor_score_total, 3),
                "eh_repeticao": eh_repeticao,
                "fonte_timestamp": "guiada",
            })

    logger.info(f"MERGE: {matched_count} matches de {len(guiada_sorted)} guiados × {n_cegos} cegos")

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
