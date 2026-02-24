"""Serviço de storage unificado: Cloudflare R2 (produção) com fallback local (dev).

Estrutura de pastas no R2 — uma pasta-mãe por vídeo:

    {Artista} - {Musica}/
    ├── video/
    │   ├── original.mp4
    │   ├── audio_completo.ogg
    │   ├── video_cortado.mp4
    │   └── video_cru.mp4
    ├── {Artista} - {Musica} - EN/
    │   ├── final.mp4
    │   ├── post.txt
    │   ├── subtitles.srt
    │   └── youtube.txt
    ├── ...outros idiomas...
    └── export/
        └── pacote.zip

Uso:
    from shared.storage_service import storage, project_base, lang_prefix
    base = project_base("Pavarotti", "Nessun Dorma")
    storage.upload_file("/tmp/v.mp4", f"{base}/video/original.mp4")
    local = storage.ensure_local(f"{base}/video/original.mp4")
    storage.upload_file("/tmp/p.txt", f"{lang_prefix(base, 'EN')}/post.txt")
"""
import os
import re
import shutil
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ─── Configuração R2 via variáveis de ambiente ───
R2_ENDPOINT = os.getenv("R2_ENDPOINT", "")
R2_ACCESS_KEY = os.getenv("R2_ACCESS_KEY", "")
R2_SECRET_KEY = os.getenv("R2_SECRET_KEY", "")
R2_BUCKET = os.getenv("R2_BUCKET", "")

# Diretório local para cache temporário
LOCAL_TMP = os.getenv("STORAGE_TMP", "/tmp/r2-cache")

# Fallback local quando R2 não está configurado (dev)
LOCAL_STORAGE = os.getenv("STORAGE_PATH", "/storage")


# ─── Helpers de naming ───

def sanitize_name(s: str) -> str:
    """Remove caracteres problemáticos para uso como nome de pasta no R2/filesystem."""
    s = re.sub(r'[<>:"/\\|?*]', '', s)
    s = s.strip('. ')
    return s[:200] if s else 'unknown'


def project_base(artista: str, musica: str, youtube_video_id: str = "") -> str:
    """Gera a chave-base do projeto no R2.

    Formato: "{Artista} - {Musica}" (sanitizado).
    Se youtube_video_id fornecido e já existir uma pasta com mesmo nome
    mas vídeo diferente, adiciona o ID como sufixo.

    Args:
        artista: nome do artista
        musica: nome da música/ária
        youtube_video_id: ID do YouTube (opcional, para desambiguação)
    Returns:
        String como "Pavarotti - Nessun Dorma"
    """
    base = sanitize_name(f"{artista} - {musica}")
    if not base or base == '-':
        base = "unknown"
    # Sufixo de desambiguação: verificação lazy —
    # quem chama pode adicionar o sufixo se detectar conflito via check_conflict()
    return base


def lang_prefix(base: str, idioma: str) -> str:
    """Gera o prefixo da subpasta de idioma.

    Ex: lang_prefix("Pavarotti - Nessun Dorma", "EN")
        → "Pavarotti - Nessun Dorma/Pavarotti - Nessun Dorma - EN"
    """
    return f"{base}/{base} - {idioma.upper()}"


def check_conflict(artista: str, musica: str, youtube_video_id: str) -> str:
    """Verifica conflito de nomes e retorna base com sufixo se necessário.

    Se já existir uma pasta com o mesmo {Artista} - {Musica} mas
    contendo um vídeo de outro youtube_video_id, adiciona (video_id) ao nome.
    """
    base = project_base(artista, musica)

    if not youtube_video_id:
        return base

    # Verificar se existe pasta com marcador de outro vídeo
    marker_key = f"{base}/video/.youtube_id"
    if storage.exists(marker_key):
        try:
            local = storage.ensure_local(marker_key)
            existing_id = Path(local).read_text().strip()
            if existing_id and existing_id != youtube_video_id:
                # Conflito: outro vídeo com mesmo artista/música
                return sanitize_name(f"{artista} - {musica} ({youtube_video_id})")
        except Exception:
            pass

    return base


def save_youtube_marker(base: str, youtube_video_id: str):
    """Salva marcador com youtube_video_id na pasta do projeto."""
    if not youtube_video_id:
        return
    import tempfile
    marker_key = f"{base}/video/.youtube_id"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as tmp:
        tmp.write(youtube_video_id)
        tmp_path = tmp.name
    try:
        storage.upload_file(tmp_path, marker_key)
    finally:
        os.unlink(tmp_path)


# ─── Infra R2 ───

def _r2_configured() -> bool:
    return bool(R2_ENDPOINT and R2_ACCESS_KEY and R2_SECRET_KEY and R2_BUCKET)


def _get_s3_client():
    """Cria cliente boto3 configurado para Cloudflare R2."""
    import boto3
    return boto3.client(
        "s3",
        endpoint_url=R2_ENDPOINT,
        aws_access_key_id=R2_ACCESS_KEY,
        aws_secret_access_key=R2_SECRET_KEY,
        region_name="auto",
    )


def _local_path_for_key(key: str) -> str:
    """Retorna path local no /tmp para cache de um key R2."""
    p = Path(LOCAL_TMP) / key
    p.parent.mkdir(parents=True, exist_ok=True)
    return str(p)


def _fallback_path(key: str) -> str:
    """Retorna path no storage local (dev) para um key."""
    p = Path(LOCAL_STORAGE) / key
    p.parent.mkdir(parents=True, exist_ok=True)
    return str(p)


# ─── StorageService ───

class StorageService:
    """Interface unificada de storage: R2 em produção, filesystem local em dev."""

    def upload_file(self, local_path: str, key: str) -> str:
        """Upload arquivo local para R2. Retorna o key."""
        if not _r2_configured():
            dest = _fallback_path(key)
            if os.path.abspath(local_path) != os.path.abspath(dest):
                shutil.copy2(local_path, dest)
            logger.debug(f"[storage:local] {local_path} → {dest}")
            return key

        client = _get_s3_client()
        client.upload_file(local_path, R2_BUCKET, key)
        logger.info(f"[storage:r2] upload {key} ({Path(local_path).stat().st_size / 1024 / 1024:.1f}MB)")
        return key

    def download_file(self, key: str, local_path: Optional[str] = None) -> str:
        """Baixa arquivo do R2 para disco local. Retorna path local."""
        dest = local_path or _local_path_for_key(key)

        if not _r2_configured():
            src = _fallback_path(key)
            if os.path.abspath(src) != os.path.abspath(dest):
                Path(dest).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest)
            return dest

        Path(dest).parent.mkdir(parents=True, exist_ok=True)
        client = _get_s3_client()
        client.download_file(R2_BUCKET, key, dest)
        logger.info(f"[storage:r2] download {key} → {dest}")
        return dest

    def ensure_local(self, key: str) -> str:
        """Garante que o arquivo está disponível localmente.

        Verifica cache /tmp primeiro. Se não tem, baixa do R2.
        Para dev (sem R2), retorna o path local direto.
        """
        if not _r2_configured():
            if os.path.isabs(key) and os.path.exists(key):
                return key
            local = _fallback_path(key)
            if os.path.exists(local):
                return local
            raise FileNotFoundError(f"Arquivo não encontrado: {key}")

        cached = _local_path_for_key(key)
        if os.path.exists(cached):
            return cached

        return self.download_file(key, cached)

    def get_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        """Gera URL temporária para download direto do R2."""
        if not _r2_configured():
            return f"/local-storage/{key}"

        client = _get_s3_client()
        url = client.generate_presigned_url(
            "get_object",
            Params={"Bucket": R2_BUCKET, "Key": key},
            ExpiresIn=expires_in,
        )
        return url

    def exists(self, key: str) -> bool:
        """Verifica se o arquivo existe no R2."""
        if not _r2_configured():
            return os.path.exists(_fallback_path(key))

        try:
            client = _get_s3_client()
            client.head_object(Bucket=R2_BUCKET, Key=key)
            return True
        except Exception:
            return False

    def delete(self, key: str) -> bool:
        """Remove arquivo do R2."""
        if not _r2_configured():
            path = _fallback_path(key)
            if os.path.exists(path):
                os.remove(path)
                return True
            return False

        try:
            client = _get_s3_client()
            client.delete_object(Bucket=R2_BUCKET, Key=key)
            logger.info(f"[storage:r2] delete {key}")
            return True
        except Exception as e:
            logger.warning(f"[storage:r2] delete falhou {key}: {e}")
            return False

    def list_files(self, prefix: str) -> list:
        """Lista arquivos no R2 com dado prefixo."""
        if not _r2_configured():
            base = Path(LOCAL_STORAGE) / prefix
            if not base.exists():
                return []
            return [
                str(f.relative_to(LOCAL_STORAGE))
                for f in base.rglob("*") if f.is_file()
            ]

        client = _get_s3_client()
        result = []
        paginator = client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=R2_BUCKET, Prefix=prefix):
            for obj in page.get("Contents", []):
                result.append(obj["Key"])
        return result

    def upload_text(self, key: str, content: str) -> str:
        """Escreve texto no R2 (cria temp file, faz upload, apaga)."""
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        try:
            return self.upload_file(tmp_path, key)
        finally:
            os.unlink(tmp_path)

    def read_text(self, key: str) -> str:
        """Lê conteúdo de texto de um arquivo no R2."""
        local = self.ensure_local(key)
        return Path(local).read_text(encoding="utf-8")


# Singleton
storage = StorageService()
