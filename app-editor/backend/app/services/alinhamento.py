"""Serviço de alinhamento: fuzzy matching letra × timestamps."""
import re
from difflib import SequenceMatcher


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
