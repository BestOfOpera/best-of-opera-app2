"""Serviço de busca de letras no Genius."""
import logging

from app.config import GENIUS_API_TOKEN

logger = logging.getLogger(__name__)

_client = None


def _get_client():
    global _client
    if _client is None:
        if not GENIUS_API_TOKEN:
            return None
        import lyricsgenius
        _client = lyricsgenius.Genius(
            GENIUS_API_TOKEN,
            verbose=False,
            remove_section_headers=True,
        )
    return _client


def buscar_letra_genius(musica: str, artista: str = "") -> str | None:
    """Busca letra no Genius. Retorna o texto ou None se não encontrar."""
    genius = _get_client()
    if not genius:
        logger.info("Genius API token não configurado, pulando busca")
        return None

    try:
        # Buscar só pelo nome da música (mais confiável para ópera)
        song = genius.search_song(musica, artist=artista if artista else None)
        if song and song.lyrics:
            # Limpar: remover header do Genius e rodapé
            lyrics = song.lyrics
            # Remover primeira linha se for o título (ex: "Casta Diva Lyrics")
            lines = lyrics.split("\n")
            if lines and "Lyrics" in lines[0]:
                lines = lines[1:]
            # Remover rodapé do Genius (ex: "123Embed")
            if lines and lines[-1].strip().endswith("Embed"):
                lines[-1] = lines[-1].rsplit("Embed", 1)[0]
                # Remover números no final
                import re
                lines[-1] = re.sub(r"\d+$", "", lines[-1]).strip()
            lyrics = "\n".join(lines).strip()
            if lyrics:
                logger.info(f"Letra encontrada no Genius: {musica}")
                return lyrics
    except Exception as e:
        logger.warning(f"Erro ao buscar no Genius: {e}")

    return None
