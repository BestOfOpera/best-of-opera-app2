#!/usr/bin/env python3
"""Apaga `video/original.mp4` e `video/.youtube_id` de uma pasta R2 antes de
teste end-to-end do endpoint `POST /api/prepare-video/{video_id}`.

Sem isso, o curto-circuito em `routes/curadoria.py:520-527` devolve o arquivo
cacheado e mascara mudanças de qualidade.

Uso:
    python scripts/cleanup_r2_video.py "<r2_base_key>"

Exemplo:
    python scripts/cleanup_r2_video.py \\
      "ReelsClassics/projetos_/Aida Garifullina - O Mio Babbino Caro (Gianni Schicchi  by Giacomo Puccini)"

Requer variáveis de ambiente (mesmas que `shared/storage_service.py:46-49`):
    R2_ENDPOINT, R2_ACCESS_KEY, R2_SECRET_KEY, R2_BUCKET

Forma recomendada de carregar as env vars na shell atual:
    set -a
    source .env.railway
    set +a
"""
import os
import sys

import boto3
from botocore.exceptions import ClientError

R2_ENDPOINT = os.getenv("R2_ENDPOINT", "")
R2_ACCESS_KEY = os.getenv("R2_ACCESS_KEY", "")
R2_SECRET_KEY = os.getenv("R2_SECRET_KEY", "")
R2_BUCKET = os.getenv("R2_BUCKET", "")


def _client():
    return boto3.client(
        "s3",
        endpoint_url=R2_ENDPOINT,
        aws_access_key_id=R2_ACCESS_KEY,
        aws_secret_access_key=R2_SECRET_KEY,
        region_name="auto",
    )


def _exists(client, key: str) -> bool:
    try:
        client.head_object(Bucket=R2_BUCKET, Key=key)
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] in ("404", "NoSuchKey"):
            return False
        raise


def main() -> int:
    if not (R2_ENDPOINT and R2_ACCESS_KEY and R2_SECRET_KEY and R2_BUCKET):
        print(
            "ERRO: R2_ENDPOINT / R2_ACCESS_KEY / R2_SECRET_KEY / R2_BUCKET "
            "nao estao no ambiente.",
            file=sys.stderr,
        )
        print(
            "      Carregue as env vars de .env.railway antes de rodar "
            "(set -a; source .env.railway; set +a).",
            file=sys.stderr,
        )
        return 1
    if len(sys.argv) != 2:
        print(f"Uso: {sys.argv[0]} '<r2_base_key>'", file=sys.stderr)
        print(
            f"Ex:  {sys.argv[0]} 'ReelsClassics/projetos_/Artista - Musica'",
            file=sys.stderr,
        )
        return 1

    base = sys.argv[1].rstrip("/")
    video_key = f"{base}/video/original.mp4"
    marker_key = f"{base}/video/.youtube_id"

    client = _client()

    print(f"Listando s3://{R2_BUCKET}/{base}/video/ :")
    try:
        resp = client.list_objects_v2(Bucket=R2_BUCKET, Prefix=f"{base}/video/")
        contents = resp.get("Contents") or []
        if not contents:
            print("  (vazio)")
        for obj in contents:
            print(f"  - {obj['Key']}  ({obj['Size']} B)")
    except ClientError as e:
        print(f"Falha ao listar: {e}", file=sys.stderr)
        return 2

    removed = 0
    for key in (video_key, marker_key):
        if _exists(client, key):
            client.delete_object(Bucket=R2_BUCKET, Key=key)
            print(f"Removido: {key}")
            removed += 1
        else:
            print(f"Ja ausente: {key}")

    print(f"\nOK. {removed} objeto(s) removido(s). Rode o teste end-to-end.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
