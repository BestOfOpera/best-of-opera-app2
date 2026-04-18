import subprocess, os

server_home = '/app/bgutil-pot/server'
script_path = os.path.join(server_home, 'src', 'generate_once.ts')

print(f"Server home: {server_home}")
print(f"Script exists: {os.path.exists(script_path)}")
print(f"Deno: {subprocess.run(['which', 'deno'], capture_output=True, text=True).stdout.strip()}")

# 1) Rodar generate_once.ts direto via Deno — revela erro de runtime/modulo
try:
    result = subprocess.run(
        ['deno', 'run', '--allow-all', script_path],
        capture_output=True, text=True, timeout=30,
        cwd=server_home,
    )
    print(f"STDOUT: {result.stdout[:500]}")
    print(f"STDERR: {result.stderr[:500]}")
    print(f"Return code: {result.returncode}")
except Exception as e:
    print(f"ERRO: {e}")

# 2) yt-dlp --verbose com o mesmo extractor_args usado em producao
print("\n=== TESTE YT-DLP COM VERBOSE ===")
try:
    result = subprocess.run(
        ['python3', '-m', 'yt_dlp',
         '--verbose',
         '--extractor-args', 'youtube:player_client=mweb,ios',
         '--extractor-args', f'youtubepot-bgutilscript:server_home={server_home}',
         '--skip-download',
         '--print', 'formats',
         'https://www.youtube.com/watch?v=dQw4w9WgXcQ'],
        capture_output=True, text=True, timeout=60,
    )
    print(f"STDOUT (primeiros 2000): {result.stdout[:2000]}")
    print(f"STDERR (primeiros 2000): {result.stderr[:2000]}")
    print(f"Return code: {result.returncode}")
except Exception as e:
    print(f"ERRO: {e}")
