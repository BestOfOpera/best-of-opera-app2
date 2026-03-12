"""Serviço de fontes customizadas por marca.

Responsabilidades:
- Extrair o nome da família tipográfica de um arquivo .ttf/.otf
- Fazer upload da fonte para o R2
- Garantir que a fonte está disponível localmente para o FFmpeg
"""
import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

FONTS_LOCAL_DIR = Path("/tmp/custom-fonts")
FONTS_SYSTEM_DIR = Path("/usr/local/share/fonts/custom")


def extract_font_family(path: str) -> str:
    """Extrai o nome da família da fonte usando fonttools.

    Args:
        path: caminho local para o arquivo .ttf ou .otf

    Returns:
        Nome da família (ex: "Noto Serif") ou o nome base do arquivo se falhar

    Raises:
        ImportError: se fonttools não estiver instalado
    """
    try:
        from fontTools.ttLib import TTFont  # type: ignore
        font = TTFont(path)
        name_table = font["name"]
        # nameID 1 = Family Name (preferido); nameID 4 = Full Name (fallback)
        for name_id in (1, 4):
            for record in name_table.names:
                if record.nameID == name_id:
                    try:
                        return record.toUnicode()
                    except Exception:
                        pass
    except Exception as e:
        logger.warning(f"[font_service] Nao foi possivel extrair family name de {path}: {e}")

    # Fallback: nome do arquivo sem extensão
    return Path(path).stem


def upload_font_to_r2(local_path: str, slug: str, filename: str) -> str:
    """Faz upload da fonte para o R2 e retorna a chave R2.

    Chave R2: fonts/{slug}/{filename}

    Args:
        local_path: path local do arquivo de fonte
        slug: slug da marca (ex: "best-of-opera")
        filename: nome original do arquivo (ex: "MinhaFonte.ttf")

    Returns:
        R2 key do arquivo
    """
    from shared.storage_service import storage

    r2_key = f"fonts/{slug}/{filename}"
    storage.upload_file(local_path, r2_key)
    logger.info(f"[font_service] Fonte carregada no R2: {r2_key}")
    return r2_key


def ensure_font_local(r2_key: str) -> str:
    """Garante que a fonte está disponível localmente para uso pelo FFmpeg.

    1. Baixa do R2 para /tmp/custom-fonts/ (se necessário)
    2. Copia para /usr/local/share/fonts/custom/ (se necessário)
    3. Roda fc-cache para registrar a fonte no sistema

    Args:
        r2_key: chave R2 do arquivo de fonte

    Returns:
        Path local do arquivo de fonte em /tmp/custom-fonts/

    Raises:
        RuntimeError: se não conseguir baixar ou instalar a fonte
    """
    from shared.storage_service import storage

    filename = Path(r2_key).name

    FONTS_LOCAL_DIR.mkdir(parents=True, exist_ok=True)
    local_path = FONTS_LOCAL_DIR / filename

    # Baixar do R2 se não estiver em cache
    if not local_path.exists():
        try:
            storage.download_file(r2_key, str(local_path))
            logger.info(f"[font_service] Fonte baixada do R2: {r2_key} → {local_path}")
        except Exception as e:
            raise RuntimeError(f"Nao foi possivel baixar fonte {r2_key} do R2: {e}") from e

    # Copiar para dir do sistema e atualizar cache de fontes
    try:
        FONTS_SYSTEM_DIR.mkdir(parents=True, exist_ok=True)
        system_path = FONTS_SYSTEM_DIR / filename
        if not system_path.exists():
            shutil.copy2(str(local_path), str(system_path))
            logger.info(f"[font_service] Fonte instalada em {system_path}")
            _refresh_font_cache()
    except PermissionError:
        # Em ambiente dev sem permissão de escrita no /usr/local, ignorar
        logger.warning(f"[font_service] Sem permissao para instalar fonte em {FONTS_SYSTEM_DIR} — usando apenas /tmp")
    except Exception as e:
        logger.warning(f"[font_service] Falha ao instalar fonte no sistema: {e} — continuando com /tmp")

    return str(local_path)


def _refresh_font_cache() -> None:
    """Executa fc-cache para registrar novas fontes no sistema."""
    try:
        result = subprocess.run(
            ["fc-cache", "-f", str(FONTS_SYSTEM_DIR)],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            logger.info("[font_service] fc-cache atualizado com sucesso")
        else:
            logger.warning(f"[font_service] fc-cache retornou {result.returncode}: {result.stderr}")
    except FileNotFoundError:
        logger.warning("[font_service] fc-cache nao encontrado — fonte pode nao ser reconhecida pelo sistema")
    except Exception as e:
        logger.warning(f"[font_service] Erro ao rodar fc-cache: {e}")
