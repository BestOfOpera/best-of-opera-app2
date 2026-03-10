#!/usr/bin/env python3
"""Migra objetos R2 existentes para estrutura com prefixo de marca.

Uso:
    python scripts/migrate_r2_to_brand_prefix.py --dry-run     # mostra o que faria
    python scripts/migrate_r2_to_brand_prefix.py --execute      # executa de verdade
    python scripts/migrate_r2_to_brand_prefix.py --verify       # checa pos-migracao

Operacoes:
1. Lista TODOS os objetos no bucket R2
2. Para cada objeto:
   - Se ja comeca com BO/ -> skip (idempotente)
   - Se comeca com editor/ -> copiar pra BO/{path sem editor/}
   - Se bare (ex: Pavarotti - Nessun Dorma/...) -> copiar pra BO/{path}
   - Se comeca com reports/ -> skip (nao e por marca)
3. UPDATE editor_perfis SET r2_prefix='BO' WHERE sigla='BO'
4. NAO deleta originais (cleanup manual depois)

Seguranca:
- Idempotente (pode rodar multiplas vezes)
- Gera manifesto JSON (migration_manifest.json) com todas as operacoes
- Resumivel (le manifesto pra pular ja copiados)
- Rate-limited (sleep entre batches)
"""

import os
import sys
import json
import time
import argparse
import boto3
from pathlib import Path

# Config R2 (mesmas env vars do storage_service.py)
R2_ENDPOINT = os.getenv("R2_ENDPOINT", "")
R2_ACCESS_KEY = os.getenv("R2_ACCESS_KEY", "")
R2_SECRET_KEY = os.getenv("R2_SECRET_KEY", "")
R2_BUCKET = os.getenv("R2_BUCKET", "")

# DB (editor)
DATABASE_URL = os.getenv("DATABASE_URL", "")

TARGET_PREFIX = "BO"
KNOWN_PREFIXES = {"BO", "editor", "reports"}
MANIFEST_FILE = "migration_manifest.json"

def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=R2_ENDPOINT,
        aws_access_key_id=R2_ACCESS_KEY,
        aws_secret_access_key=R2_SECRET_KEY,
    )

def list_all_objects(client):
    """Lista todos os objetos no bucket."""
    objects = []
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=R2_BUCKET):
        for obj in page.get("Contents", []):
            objects.append({"key": obj["Key"], "size": obj["Size"]})
    return objects

def classify_object(key):
    """Classifica objeto e retorna (acao, novo_key)."""
    if key.startswith(f"{TARGET_PREFIX}/"):
        return "skip", key  # ja migrado
    if key.startswith("reports/"):
        return "skip", key  # nao e por marca
    if key.startswith("editor/"):
        # Render: editor/Artista - Musica/... -> BO/Artista - Musica/...
        new_key = f"{TARGET_PREFIX}/{key[len('editor/'):]}"
        return "copy", new_key
    # Bare: Artista - Musica/... -> BO/Artista - Musica/...
    new_key = f"{TARGET_PREFIX}/{key}"
    return "copy", new_key

def execute_migration(client, manifest, batch_size=100):
    """Executa copias do manifesto."""
    to_copy = [m for m in manifest if m["action"] == "copy" and not m.get("done")]
    print(f"  {len(to_copy)} objetos para copiar")

    for i, item in enumerate(to_copy):
        try:
            client.copy_object(
                Bucket=R2_BUCKET,
                CopySource={"Bucket": R2_BUCKET, "Key": item["old_key"]},
                Key=item["new_key"],
            )
            item["done"] = True
            if (i + 1) % 10 == 0:
                print(f"  {i+1}/{len(to_copy)} copiados")
        except Exception as e:
            item["error"] = str(e)
            print(f"  ERRO {item['old_key']}: {e}")

        if (i + 1) % batch_size == 0:
            # Salvar progresso e dar pausa
            with open(MANIFEST_FILE, "w") as f:
                json.dump(manifest, f, indent=2)
            time.sleep(1)

    # Salvar final
    with open(MANIFEST_FILE, "w") as f:
        json.dump(manifest, f, indent=2)

def update_database():
    """Atualiza r2_prefix na tabela editor_perfis."""
    if not DATABASE_URL:
        print("  DATABASE_URL nao definida, pulando update DB")
        return
    try:
        from sqlalchemy import create_engine, text
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            result = conn.execute(text(
                f"UPDATE editor_perfis SET r2_prefix = '{TARGET_PREFIX}' "
                f"WHERE sigla = '{TARGET_PREFIX}' AND (r2_prefix IS NULL OR r2_prefix != '{TARGET_PREFIX}')"
            ))
            conn.commit()
            print(f"  DB: {result.rowcount} perfil(s) atualizado(s)")
    except Exception as e:
        print(f"  DB update falhou: {e}")

def verify_migration(client, manifest):
    """Verifica integridade pos-migracao."""
    errors = 0
    to_verify = [m for m in manifest if m["action"] == "copy" and m.get("done")]
    for item in to_verify[:20]:  # spot-check 20
        try:
            obj = client.head_object(Bucket=R2_BUCKET, Key=item["new_key"])
            if obj["ContentLength"] != item["size"]:
                print(f"  Size mismatch: {item['new_key']}")
                errors += 1
        except Exception as e:
            print(f"  Missing: {item['new_key']}: {e}")
            errors += 1
    print(f"  Verificacao: {len(to_verify)} copiados, {errors} erros em {min(20, len(to_verify))} checados")

def main():
    parser = argparse.ArgumentParser(description="Migrar R2 para prefixo de marca")
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--batch-size", type=int, default=100)
    args = parser.parse_args()

    if not all([R2_ENDPOINT, R2_ACCESS_KEY, R2_SECRET_KEY, R2_BUCKET]):
        print("Variaveis R2 nao configuradas")
        sys.exit(1)

    client = get_s3_client()

    if args.verify:
        if not Path(MANIFEST_FILE).exists():
            print("Manifesto nao encontrado. Execute a migracao primeiro.")
            sys.exit(1)
        manifest = json.loads(Path(MANIFEST_FILE).read_text())
        verify_migration(client, manifest)
        return

    # Carregar manifesto existente ou criar novo
    if Path(MANIFEST_FILE).exists():
        manifest = json.loads(Path(MANIFEST_FILE).read_text())
        print(f"Manifesto existente: {len(manifest)} objetos")
    else:
        print("Listando objetos R2...")
        objects = list_all_objects(client)
        print(f"{len(objects)} objetos encontrados")

        manifest = []
        for obj in objects:
            action, new_key = classify_object(obj["key"])
            manifest.append({
                "old_key": obj["key"],
                "new_key": new_key,
                "size": obj["size"],
                "action": action,
            })

        with open(MANIFEST_FILE, "w") as f:
            json.dump(manifest, f, indent=2)

    # Stats
    skip_count = sum(1 for m in manifest if m["action"] == "skip")
    copy_count = sum(1 for m in manifest if m["action"] == "copy")
    done_count = sum(1 for m in manifest if m.get("done"))
    print(f"Stats -> Skip: {skip_count} | Copiar: {copy_count} | Ja copiados: {done_count}")

    if args.execute:
        print("EXECUTANDO migracao...")
        execute_migration(client, manifest, args.batch_size)
        update_database()
        print("Migracao concluida! Use --verify pra checar.")
    else:
        print("DRY-RUN. Use --execute pra executar de verdade.")
        # Mostrar amostra
        for m in manifest[:10]:
            if m["action"] == "copy":
                print(f"  {m['old_key']} -> {m['new_key']}")

if __name__ == "__main__":
    main()
