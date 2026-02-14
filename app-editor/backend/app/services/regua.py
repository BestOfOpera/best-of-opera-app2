"""Serviço régua: overlay define a janela de corte automático.

REGRAS DE TIMESTAMPS (NUNCA VIOLAR):
- Formato canônico interno: SEMPRE float em segundos
- Formato canônico de saída: SEMPRE HH:MM:SS,mmm (SRT padrão)
- Toda entrada de timestamp passa por timestamp_to_seconds() que aceita qualquer formato
- Toda saída passa por seconds_to_timestamp() que produz SRT canônico
- Validação: nenhum timestamp pode ser negativo ou > 24h (86400s)
- Segmentos: start < end SEMPRE; end[i] <= start[i+1] SEMPRE
"""
import logging

logger = logging.getLogger(__name__)

# Limite máximo razoável: 24 horas
MAX_SECONDS = 86400.0


def timestamp_to_seconds(ts: str) -> float:
    """Converte QUALQUER formato de timestamp para float em segundos.

    Formatos aceitos:
    - HH:MM:SS,mmm (SRT padrão — ex: 00:01:25,300 → 85.3s)
    - HH:MM:SS.mmm (variante com ponto)
    - MM:SS:mmm (Gemini — terceira parte >= 100: ex: 1:25:300 → 85.3s)
    - MM:SS.mmm (ex: 1:25.300 → 85.3s)
    - MM:SS (ex: 1:25 → 85s)
    - SS.mmm (ex: 25.3 → 25.3s)

    Regra de desambiguação para 3 partes (A:B:C):
    - Se C >= 100 → formato MM:SS:mmm (Gemini) → A*60 + B + C/1000
    - Se C < 100  → formato HH:MM:SS.frac (SRT)  → A*3600 + B*60 + C
    """
    if not ts or not isinstance(ts, str):
        return 0.0
    ts = ts.strip().replace(",", ".")
    parts = ts.split(":")
    try:
        if len(parts) == 3:
            a, b, c = float(parts[0]), float(parts[1]), float(parts[2])
            if c >= 100:
                result = a * 60 + b + c / 1000
            else:
                result = a * 3600 + b * 60 + c
        elif len(parts) == 2:
            result = float(parts[0]) * 60 + float(parts[1])
        else:
            result = float(parts[0])
    except (ValueError, TypeError):
        logger.warning(f"Timestamp inválido: '{ts}' → retornando 0")
        return 0.0

    # Validação: nunca negativo, nunca absurdamente grande
    if result < 0:
        logger.warning(f"Timestamp negativo: '{ts}' → {result}s, clipando para 0")
        return 0.0
    if result > MAX_SECONDS:
        logger.warning(f"Timestamp absurdo: '{ts}' → {result}s (>{MAX_SECONDS}s), clipando")
        return MAX_SECONDS

    return result


def seconds_to_timestamp(sec: float) -> str:
    """Converte segundos para timestamp SRT canônico (HH:MM:SS,mmm).

    SEMPRE produz este formato — é a representação única e canônica.
    """
    sec = max(0.0, min(sec, MAX_SECONDS))
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = sec % 60
    ms = int(round((s % 1) * 1000))
    return f"{h:02d}:{m:02d}:{int(s):02d},{ms:03d}"


def normalizar_segmentos(segmentos: list) -> list:
    """Normaliza e valida TODOS os timestamps de uma lista de segmentos.

    Garante:
    1. Todos os timestamps em formato canônico SRT
    2. start < end para cada segmento
    3. Sem sobreposições: end[i] <= start[i+1]
    4. Nenhum valor negativo ou absurdo
    """
    if not segmentos:
        return []

    resultado = []
    for seg in segmentos:
        novo = dict(seg)

        if "start" in seg:
            start_sec = timestamp_to_seconds(str(seg["start"]))
            novo["start"] = seconds_to_timestamp(start_sec)
        if "end" in seg:
            end_sec = timestamp_to_seconds(str(seg["end"]))
            novo["end"] = seconds_to_timestamp(end_sec)
        if "timestamp" in seg:
            ts_sec = timestamp_to_seconds(str(seg["timestamp"]))
            novo["timestamp"] = seconds_to_timestamp(ts_sec)

        # Garantir start < end
        if "start" in novo and "end" in novo:
            s = timestamp_to_seconds(novo["start"])
            e = timestamp_to_seconds(novo["end"])
            if e <= s:
                novo["end"] = seconds_to_timestamp(s + 2.0)

        resultado.append(novo)

    # Garantir sem sobreposições (end[i] <= start[i+1])
    for i in range(len(resultado) - 1):
        if "end" in resultado[i] and "start" in resultado[i + 1]:
            cur_end = timestamp_to_seconds(resultado[i]["end"])
            next_start = timestamp_to_seconds(resultado[i + 1]["start"])
            if cur_end > next_start:
                resultado[i]["end"] = seconds_to_timestamp(max(0, next_start - 0.05))

    return resultado


def extrair_janela_do_overlay(
    overlay_srt: list,
    corte_inicio_override: str = None,
    corte_fim_override: str = None,
) -> dict:
    """Lê overlay e extrai início/fim da janela de corte.

    Se corte_inicio_override / corte_fim_override forem fornecidos
    (timestamps string do APP2 cut_start/cut_end), usam-se esses
    valores em vez dos calculados a partir do overlay.
    """
    if not overlay_srt and not corte_inicio_override:
        return {"janela_inicio_sec": 0, "janela_fim_sec": 0, "duracao_corte_sec": 0}

    def get_start(seg):
        if "start" in seg:
            return timestamp_to_seconds(seg["start"])
        if "timestamp" in seg:
            return timestamp_to_seconds(seg["timestamp"])
        return 0

    def get_end(seg):
        if "end" in seg:
            return timestamp_to_seconds(seg["end"])
        if "timestamp" in seg:
            return timestamp_to_seconds(seg["timestamp"]) + 4
        return get_start(seg) + 4

    inicio = get_start(overlay_srt[0]) if overlay_srt else 0
    fim = get_end(overlay_srt[-1]) if overlay_srt else 0

    if corte_inicio_override:
        inicio = timestamp_to_seconds(corte_inicio_override)
    if corte_fim_override:
        fim = timestamp_to_seconds(corte_fim_override)

    # Validação
    if fim <= inicio:
        logger.warning(f"Janela inválida: inicio={inicio} >= fim={fim}")
        fim = inicio + 120  # fallback 2 minutos

    return {
        "janela_inicio_sec": inicio,
        "janela_fim_sec": fim,
        "duracao_corte_sec": fim - inicio,
    }


def reindexar_timestamps(segmentos: list, janela_inicio_sec: float) -> list:
    """Subtrai janela_inicio de todos os timestamps (rebasa para 0:00)."""
    resultado = []
    for seg in segmentos:
        novo = dict(seg)
        if "start" in seg:
            inicio = timestamp_to_seconds(seg["start"]) - janela_inicio_sec
            novo["start"] = seconds_to_timestamp(max(0, inicio))
        if "end" in seg:
            fim = timestamp_to_seconds(seg["end"]) - janela_inicio_sec
            novo["end"] = seconds_to_timestamp(max(0, fim))
        if "timestamp" in seg:
            t = timestamp_to_seconds(seg["timestamp"]) - janela_inicio_sec
            novo["timestamp"] = seconds_to_timestamp(max(0, t))
        resultado.append(novo)
    return normalizar_segmentos(resultado)


def recortar_lyrics_na_janela(
    lyrics_completo: list, janela_inicio_sec: float, janela_fim_sec: float
) -> list:
    """Filtra lyrics dentro da janela + reindexa."""
    dentro = []
    for seg in lyrics_completo:
        seg_inicio = timestamp_to_seconds(seg.get("start", "0:0:0"))
        seg_fim = timestamp_to_seconds(seg.get("end", "0:0:0"))
        if seg_fim > janela_inicio_sec and seg_inicio < janela_fim_sec:
            novo_inicio = max(seg_inicio, janela_inicio_sec) - janela_inicio_sec
            novo_fim = min(seg_fim, janela_fim_sec) - janela_inicio_sec
            dentro.append({
                **seg,
                "start": seconds_to_timestamp(novo_inicio),
                "end": seconds_to_timestamp(novo_fim),
            })
    return normalizar_segmentos(dentro)
