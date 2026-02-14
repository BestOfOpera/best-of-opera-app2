"""Serviço régua: overlay define a janela de corte automático."""


def timestamp_to_seconds(ts: str) -> float:
    """Converte timestamp para segundos.

    Formatos aceitos:
    - HH:MM:SS,mmm (SRT padrão)
    - HH:MM:SS.mmm
    - MM:SS:mmm (formato Gemini — 3 partes onde última < 1000)
    - MM:SS.mmm
    - MM:SS
    """
    ts = ts.replace(",", ".")
    parts = ts.split(":")
    if len(parts) == 3:
        # Detectar se é HH:MM:SS ou MM:SS:mmm
        # Se a terceira parte é >= 1000 ou a primeira parte é <= 59 e terceira <= 999
        # e o valor total faria mais sentido como MM:SS:mmm
        third = float(parts[2])
        if third > 59:
            # É MM:SS:mmm (milissegundos na terceira parte)
            return float(parts[0]) * 60 + float(parts[1]) + third / 1000
        else:
            return float(parts[0]) * 3600 + float(parts[1]) * 60 + third
    elif len(parts) == 2:
        return float(parts[0]) * 60 + float(parts[1])
    return float(parts[0])


def seconds_to_timestamp(sec: float) -> str:
    """Converte segundos para timestamp SRT (HH:MM:SS,mmm)."""
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = sec % 60
    ms = int((s % 1) * 1000)
    return f"{h:02d}:{m:02d}:{int(s):02d},{ms:03d}"


def extrair_janela_do_overlay(overlay_srt: list) -> dict:
    """Lê overlay e extrai início/fim da janela de corte."""
    if not overlay_srt:
        return {"janela_inicio_sec": 0, "janela_fim_sec": 0, "duracao_corte_sec": 0}

    # Aceitar formatos variados de campo de timestamp
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
            # Estimar fim: início + 4 segundos padrão
            return timestamp_to_seconds(seg["timestamp"]) + 4
        return get_start(seg) + 4

    inicio = get_start(overlay_srt[0])
    fim = get_end(overlay_srt[-1])
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
    return resultado


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
    return dentro
