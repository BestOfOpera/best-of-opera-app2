# Auditoria de qualidade de download — 2026-04-23

## 0. Resumo executivo

- **H1 (seletor sem piso de qualidade)** — CONFIRMADO. `services/download.py:160` declara `'format': 'bestvideo+bestaudio/best'`, sem cláusula `height>=N`. Quando os formatos DASH são pulados por falta de POT, o yt-dlp cai em progressivos como itag 18 (360p) e a chamada termina com `rc=0`.
- **H2 (sem validação pós-download na rota)** — CONFIRMADO. A rota HTTP `prepare_video` (`routes/curadoria.py:502-591`) faz download→upload→200 **sem** executar `ffprobe` ou qualquer checagem de resolução/bitrate/duração. Existe um `ffprobe` no caminho do worker (`services/download.py:380-392`), mas: (a) ele é apenas diagnóstico (`logger.info` do resultado), não gate, e (b) não é executado pelo caminho HTTP direto, que duplica o fluxo.
- **H3 (POT provider configurado mas fragilizado)** — CONFIRMADO. `services/download.py:185-192` ativa explicitamente `youtubepot-bgutilscript` + `player_client: ['mweb','ios']`. Após `subprocess.run`, o código (linhas 285-289) só lê `rc` e loga as últimas 40 linhas de stderr; **não procura** `PoTokenProviderError`, `PO Token ... was not provided` nem `will be skipped`.
- **H4 (logs INFO aparecendo como severity=error)** — INCONCLUSIVO no código Python. Não há redirecionamento de stderr para `logger.error` e as mensagens citadas são emitidas via `logger.info`. A reclassificação provavelmente vem da infra de logging externa (Railway/Sentry) e precisa ser verificada fora do repositório.
- **H5 (sem retry/estratégia alternativa quando POT falha)** — CONFIRMADO. Não há `except PoTokenProviderError`, nem troca de `player_client`, nem repetição com outro extractor. O único fallback é `cobalt.tools`, e ele só dispara quando o yt-dlp levanta exceção (rc ≠ 0). Com rc=0 em 360p, cobalt nunca é tentado.

**Impacto**: o sistema degrada silenciosamente a qualidade do conteúdo publicado (360p vs 720p/1080p esperados) sem alerta para o operador. Conteúdo já subiu para o R2 e foi marcado como cached — próximas requisições para o mesmo vídeo retornam o arquivo degradado imediatamente (`routes/curadoria.py:520-527`).

## 1. Topologia do repositório relevante

Arquivos lidos na auditoria (com propósito em 1 linha):

- `app-curadoria/backend/services/download.py` — implementa `_get_ydl_opts`, `_build_ydl_cli_args`, `_download_via_ytdlp_cli`, `_download_via_cobalt`, `_prepare_video_logic`, `download_worker`, `TaskManager`.
- `app-curadoria/backend/routes/curadoria.py` (apenas linhas 490-591) — define o endpoint `POST /api/prepare-video/{video_id}`, que duplica o fluxo de download em-processo sem passar pelo worker.
- `app-curadoria/backend/main.py` — configura `logging.basicConfig(level=INFO, ...)`, inicializa Sentry (se DSN presente) e inicia `download_worker` em task separada.
- `shared/storage_service.py` — `StorageService.upload_file` (linhas 186-211), faz upload ao R2 com retry e `head_object` pós-upload (sem comparação de tamanho).
- `app-curadoria/backend/requirements.txt` — declara `yt-dlp`, `yt-dlp-ejs`, `bgutil-ytdlp-pot-provider`.
- `app-curadoria/backend/test_bgutil.py` — confirma presença esperada do script TS em `/app/bgutil-pot/server/src/generate_once.ts`.

Arquivos NÃO localizados (e o que foi procurado):

- **Nenhum handler de logging custom** — apenas `basicConfig` em `main.py:12`. A reclassificação INFO→ERROR vista no Railway não está no código Python.
- **Nenhum `dictConfig`, `FileHandler` ou `StreamHandler` custom** em `app-curadoria/**/*.py`.
- **Nenhuma ocorrência de `except PoTokenProviderError`, `PO Token`, `itag`, `height>=`, `height >=`, `360p`, `720p`, `bestvideo[height` em `*.py`** (exceto o comentário em `services/download.py:351`).

## 2. Reconstrução do fluxo atual

Do `POST /api/prepare-video/{video_id}` até o upload R2, passo a passo (factual):

1. **Entrada da rota** — `routes/curadoria.py:502-508` define o handler com query params `artist`, `song`, `brand_slug`.
2. **Resolução de caminhos R2** — `routes/curadoria.py:515-519`: carrega `brand_config`, calcula `r2_prefix`, chama `check_conflict` (`shared/storage_service.py:103-130`) que pode adicionar sufixo `(video_id)`, monta `r2_key = f"{full_base}/video/original.mp4"`.
3. **Atalho cache** — `routes/curadoria.py:520-527`: `if storage.exists(r2_key)` retorna `{"status":"ok", "cached":True}`. Isso significa que uma vez um 360p subiu, ele fica.
4. **Setup local** — `routes/curadoria.py:529-532`: cria `project_dir/video/`, define `dl_path`.
5. **Semáforo** — `routes/curadoria.py:534`: `async with download_semaphore:` (permite 2 concorrentes, definido em `services/download.py:111`).
6. **Montagem de opts** — `routes/curadoria.py:540`: chama `_get_ydl_opts(dl_path)` (`services/download.py:156-238`). Produz o dict com `format: 'bestvideo+bestaudio/best'`, `extractor_args` incluindo `youtube.player_client=['mweb','ios']` e `youtubepot-bgutilscript.server_home=['/app/bgutil-pot/server']`, cookies de `YOUTUBE_COOKIES_BASE64` se presente, proxy se `YOUTUBE_PROXY` setado.
7. **Log do formato escolhido** — `services/download.py:237`: `logger.info(f"[yt-dlp] Formato selecionado: {opts.get('format', 'NENHUM')}")` (gera a linha vista no log de produção).
8. **Construção do CLI** — `routes/curadoria.py:542` chama `_download_via_ytdlp_cli` (`services/download.py:272-289`), que chama `_build_ydl_cli_args` (`services/download.py:241-269`). Produz `['python3','-m','yt_dlp','--no-playlist','--verbose','-f','bestvideo+bestaudio/best','--merge-output-format','mp4','-o',dl_path,'--socket-timeout','30','--retries','3','--fragment-retries','5','--extractor-retries','3','--no-check-certificate','--match-filter','duration < 1800','--user-agent',...,'--add-header',...,'--extractor-args','youtube:player_client=mweb,ios','--extractor-args','youtubepot-bgutilscript:server_home=/app/bgutil-pot/server','--cookies','/tmp/yt_cookies.txt',youtube_url]`.
9. **Invocação** — `services/download.py:281-282`: `subprocess.run(cmd, capture_output=True, text=True, timeout=900)` em thread asyncio.
10. **Leitura do resultado** — `services/download.py:284-289`: pega `r.returncode`, junta últimas 40 linhas de stderr em `stderr_tail`, loga ambas como `logger.info`. **Só levanta exceção se `rc != 0`.** Nenhum parse de conteúdo do stderr.
11. **Confirmação do arquivo** — `routes/curadoria.py:544-552`: se `dl_path` não existe, faz `glob` na pasta para pegar qualquer arquivo (isso cobre casos onde o nome final difere do template); erro só se não houver arquivo algum.
12. **(Passo NÃO executado)** — ffprobe existe em `services/download.py:380-392`, mas apenas dentro de `_prepare_video_logic`. A rota `prepare_video` **não chama** essa função — duplica os passos 6-11 manualmente e pula o 380-392.
13. **Gravação no banco** — `routes/curadoria.py:566-569`: `db.save_download(...)`, com catch que apenas loga warning.
14. **Upload R2** — `routes/curadoria.py:571`: `storage.upload_file(dl_path_actual, r2_key)` (`shared/storage_service.py:186-211`). Retry 3x, `head_object` pós-upload para confirmar existência (sem comparação de tamanho).
15. **Marker YouTube** — `routes/curadoria.py:572`: `save_youtube_marker(r2_base, video_id, r2_prefix=r2_prefix)`.
16. **Limpeza e resposta** — `routes/curadoria.py:574-586`: loga `R2 upload OK`, remove pasta local, retorna `{"status":"ok", "cached":False, "file_size_mb":..., "message":"Vídeo baixado e salvo no R2"}`.

## 3. Evidências por hipótese

### H1 — Seletor de formato sem piso de qualidade

Status: **CONFIRMADO**

Evidência — declaração do formato:
```
app-curadoria/backend/services/download.py:159-160
    opts = {
        'format': 'bestvideo+bestaudio/best',
```

Evidência — propagação para o CLI:
```
app-curadoria/backend/services/download.py:247
    cmd += ['-f', opts['format']]
```

Evidência — log de confirmação emitido em produção:
```
app-curadoria/backend/services/download.py:237
    logger.info(f"[yt-dlp] Formato selecionado: {opts.get('format', 'NENHUM')}")
```

Evidência — `extractor_args` usa apenas `player_client`, sem filtro de altura:
```
app-curadoria/backend/services/download.py:185-192
        'extractor_args': {
            'youtube': {'player_client': ['mweb', 'ios']},
            # server_home precisa ser LISTA: o plugin lê via
            # _configuration_arg(...)[0]. Valor string faz [0] devolver '/'
            # (primeiro caractere). A CLI --extractor-args envelopa em lista
            # automaticamente; a Python API não — daí a lista explícita.
            'youtubepot-bgutilscript': {'server_home': ['/app/bgutil-pot/server']},
        },
```

Ausência verificada por grep — nenhuma ocorrência de `height>=`, `height >=`, `[height`, `bestvideo[` em `app-curadoria/backend/**/*.py`.

Interpretação: a expressão `bestvideo+bestaudio/best` é avaliada pelo yt-dlp como "combine o melhor vídeo com o melhor áudio; se não conseguir combinar, pegue `best` progressivo". Quando os DASH são pulados (POT faltando), `bestvideo` não existe e o yt-dlp cai para `/best`. Sem `[height>=N]`, qualquer formato serve — incluindo itag 18 (360p).

### H2 — Não há validação de qualidade pós-download

Status: **CONFIRMADO** (no caminho HTTP direto usado pelo endpoint; o caminho do worker tem ffprobe puramente diagnóstico).

Evidência — corpo integral da rota após o download, sem ffprobe:
```
app-curadoria/backend/routes/curadoria.py:539-586
            try:
                ydl_opts = _get_ydl_opts(dl_path)
                logger.info(f"[prepare-video] ydl_opts format: {ydl_opts.get('format', 'NENHUM')}")
                await _download_via_ytdlp_cli(youtube_url, ydl_opts)

                if not os.path.exists(dl_path):
                    import glob as _glob
                    files = _glob.glob(str(project_dir / "video" / '*'))
                    dl_path_actual = files[0] if files else None
                else:
                    dl_path_actual = dl_path

                if not dl_path_actual:
                    raise Exception("yt-dlp terminou sem erro mas arquivo não encontrado")
            except Exception as e:
                logger.warning(f"[prepare-video] yt-dlp falhou para {video_id}: {e}")

            # PASSO 2 — cobalt.tools (fallback)
            if not dl_path_actual:
                logger.info(f"[prepare-video] Tentando cobalt.tools para {video_id}...")
                cobalt_ok = await _download_via_cobalt(youtube_url, dl_path)
                if cobalt_ok:
                    dl_path_actual = dl_path

            if not dl_path_actual:
                raise HTTPException(500, "Download falhou: yt-dlp e cobalt.tools falharam. Use upload manual.")

            try:
                db.save_download(video_id, f"{project_name}.mp4", artist, song, youtube_url, brand_slug=brand_slug)
            except Exception as e:
                logger.warning(f"Failed to save download record: {e}")

            storage.upload_file(dl_path_actual, r2_key)
            save_youtube_marker(r2_base, video_id, r2_prefix=r2_prefix)
            file_size = os.path.getsize(dl_path_actual)
            logger.info(f"R2 upload OK: {r2_key} ({file_size / 1024 / 1024:.1f}MB)")

            shutil.rmtree(str(project_dir), ignore_errors=True)
            logger.info(f"Limpeza local: {project_dir}")

            return {
                "status": "ok",
                "r2_key": r2_key,
                "r2_base": r2_base,
                "cached": False,
                "file_size_mb": round(file_size / 1024 / 1024, 1),
                "message": "Vídeo baixado e salvo no R2",
            }
```

Entre `_download_via_ytdlp_cli` (linha 542) e `storage.upload_file` (linha 571) não há chamada a `ffprobe`, `mediainfo`, `cv2`, `moviepy`, ou qualquer inspeção do arquivo além de `os.path.exists` / `os.path.getsize` (somente para logging e resposta).

Evidência — o ffprobe existe, mas só em `_prepare_video_logic` (caminho do worker, não da rota):
```
app-curadoria/backend/services/download.py:379-392
        # Diagnóstico: logar resolução/codec do vídeo baixado
        try:
            _probe = subprocess.run(
                ['ffprobe', '-v', 'error', '-select_streams', 'v:0',
                 '-show_entries', 'stream=width,height,codec_name,bit_rate',
                 '-of', 'csv=p=0', dl_path_actual],
                capture_output=True, text=True, timeout=10
            )
            _size_mb = os.path.getsize(dl_path_actual) / (1024 * 1024)
            logger.info(f"[{video_id}] ffprobe: {_probe.stdout.strip()} | {_size_mb:.1f}MB — {dl_path_actual}")
            if _probe.returncode != 0:
                logger.warning(f"[{video_id}] ffprobe stderr: {_probe.stderr.strip()}")
        except Exception as _probe_err:
            logger.warning(f"[{video_id}] ffprobe falhou: {_probe_err}")
```

Mesmo nesse ffprobe do caminho worker, o resultado é apenas logado (`logger.info` na linha 388). Não há `if height < 720: raise` ou equivalente. O upload R2 acontece na sequência (linha 406) incondicionalmente.

Interpretação: a rota HTTP executa todo o fluxo localmente (passos 6-16 da seção 2), duplicando `_prepare_video_logic` sem incluir o ffprobe. Mesmo o ffprobe que existe no worker não seria um gate — é apenas telemetria. Resultado: qualquer arquivo que chegue ao disco (inclusive 360p) é subido ao R2 e retornado como 200 OK.

### H3 — O provider bgutil está configurado mas fragilizado

Status: **CONFIRMADO**

Evidência — ativação explícita do plugin via `extractor_args`:
```
app-curadoria/backend/services/download.py:177-192
        # mweb = recomendado pelo PO Token Guide (bgutil script-deno gera tokens)
        # ios  = fallback H.264 tradicionais (não requer PO Token)
        # NÃO usar 'web' — YouTube migrou para SABR-only (yt-dlp#12482)
        # extractor_args: sintaxe confirmada no source do plugin bgutil-ytdlp-pot-provider
        # (plugin/yt_dlp_plugins/extractor/getpot_bgutil.py) — _script_config_arg usa
        # ie_key='youtubepot-bgutilscript' e lê key='server_home'.
        # HTTP provider é priorizado pelo plugin; como não subimos servidor HTTP,
        # o ping em 127.0.0.1:4416 falha e o plugin cai para o script provider.
        'extractor_args': {
            'youtube': {'player_client': ['mweb', 'ios']},
            # server_home precisa ser LISTA: o plugin lê via
            # _configuration_arg(...)[0]. Valor string faz [0] devolver '/'
            # (primeiro caractere). A CLI --extractor-args envelopa em lista
            # automaticamente; a Python API não — daí a lista explícita.
            'youtubepot-bgutilscript': {'server_home': ['/app/bgutil-pot/server']},
        },
```

Evidência — tradução direta para argv do CLI:
```
app-curadoria/backend/services/download.py:260-263
    for ns, kvs in opts.get('extractor_args', {}).items():
        for key, val in kvs.items():
            val_str = ','.join(map(str, val)) if isinstance(val, (list, tuple)) else str(val)
            cmd += ['--extractor-args', f'{ns}:{key}={val_str}']
```

Evidência — a captura do subprocess não analisa o conteúdo do stderr:
```
app-curadoria/backend/services/download.py:281-289
    def _run():
        return subprocess.run(cmd, capture_output=True, text=True, timeout=900)

    r = await asyncio.to_thread(_run)
    stderr_tail = '\n'.join(r.stderr.splitlines()[-40:])
    logger.info(f"[yt-dlp CLI] rc={r.returncode}")
    logger.info(f"[yt-dlp CLI] stderr (tail 40):\n{stderr_tail}")
    if r.returncode != 0:
        raise Exception(f"yt-dlp CLI rc={r.returncode}")
```

Ausência verificada — nenhuma ocorrência de `PoTokenProviderError`, `PO Token`, `require a GVS`, `will be skipped`, `_get_pot_via_script` em `app-curadoria/backend/**/*.py` (grep sem matches).

Evidência adicional — o stderr é truncado para as últimas 40 linhas antes de ser logado. Se a falha do POT ocorrer antes do último bloco (o log do yt-dlp com `--verbose` é longo), as mensagens críticas podem nem aparecer nos logs.

Interpretação: o código ativa o provider POT e depende dele para obter formatos HD, mas trata qualquer `rc=0` como sucesso incondicional. Os próprios warnings oficiais do yt-dlp (`WARNING: [youtube] ...: ios client https formats require a GVS PO Token which was not provided. They will be skipped`) vão para o stderr e nunca são examinados. O yt-dlp termina com exit code 0 porque ainda conseguiu baixar *algo* — só que esse "algo" é o formato combinado 360p.

### H4 — Logging classifica INFO do yt-dlp como `error`

Status: **INCONCLUSIVO** (no código Python).

Evidência — configuração global única:
```
app-curadoria/backend/main.py:12
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
```

Evidência — mensagens citadas são emitidas com `logger.info`:
```
app-curadoria/backend/services/download.py:212
            logger.info(f"Using YOUTUBE_COOKIES_BASE64 (saved to {cookies_path})")
```
```
app-curadoria/backend/services/download.py:286-287
    logger.info(f"[yt-dlp CLI] rc={r.returncode}")
    logger.info(f"[yt-dlp CLI] stderr (tail 40):\n{stderr_tail}")
```
```
shared/storage_service.py:210
        logger.info(f"[storage:r2] upload OK {key} ({local_size / 1024 / 1024:.1f}MB)")
```
```
app-curadoria/backend/routes/curadoria.py:574
            logger.info(f"R2 upload OK: {r2_key} ({file_size / 1024 / 1024:.1f}MB)")
```

Evidência — nenhum handler custom, nenhum dictConfig, nenhum redirecionamento de stderr. Busca por `basicConfig|dictConfig|StreamHandler|FileHandler|addHandler` em `app-curadoria/backend/**/*.py` retorna apenas a linha 12 do `main.py`.

Evidência — nenhum padrão `for line in stderr` ou equivalente que transforme linhas de stderr em `logger.error`. A única captura de stderr de subprocess é `r.stderr` (string completa) em `_download_via_ytdlp_cli` e logada via `logger.info`.

Observação colateral — `services/download.py` usa `logger.error(...)` em blocos de diagnóstico de startup (linhas 15, 25, 32, 44, 46, 58, 69, 71), mas todos são associados a falhas reais (Node check failed, plugin file MISSING, etc.) ou a exceções capturadas. Não se aplicam à mensagem "rc=0" nem "upload OK".

Interpretação: o fato observado (`severity: error` em mensagens INFO) não é explicável pelo código do repositório. Possíveis causas fora do escopo desta auditoria: (a) Railway classifica qualquer linha em `stderr` do container como error — e `logging.basicConfig` sem handler envia para stderr por padrão; (b) parser de logs externo (Sentry breadcrumbs, Grafana) categoriza por regex; (c) contexto do observador incorreto (a severity reportada pelo operador pode ser uma cor da UI, não a severity real do LogRecord). Recomenda-se o operador fornecer a origem exata da classificação `severity: error` (Railway logs, Grafana, Sentry) para que a Fase 2 confirme a causa antes de mudar código.

### H5 — Não há retry/estratégia alternativa quando POT falha

Status: **CONFIRMADO**

Evidência — corpo integral do fluxo de fallback na rota:
```
app-curadoria/backend/routes/curadoria.py:536-564
        try:
            # PASSO 1 — yt-dlp via CLI (única via com plugin bgutil ativo;
            # Python API no mesmo processo só entrega 360p por falta de PO Token)
            try:
                ydl_opts = _get_ydl_opts(dl_path)
                logger.info(f"[prepare-video] ydl_opts format: {ydl_opts.get('format', 'NENHUM')}")
                await _download_via_ytdlp_cli(youtube_url, ydl_opts)

                if not os.path.exists(dl_path):
                    import glob as _glob
                    files = _glob.glob(str(project_dir / "video" / '*'))
                    dl_path_actual = files[0] if files else None
                else:
                    dl_path_actual = dl_path

                if not dl_path_actual:
                    raise Exception("yt-dlp terminou sem erro mas arquivo não encontrado")
            except Exception as e:
                logger.warning(f"[prepare-video] yt-dlp falhou para {video_id}: {e}")

            # PASSO 2 — cobalt.tools (fallback)
            if not dl_path_actual:
                logger.info(f"[prepare-video] Tentando cobalt.tools para {video_id}...")
                cobalt_ok = await _download_via_cobalt(youtube_url, dl_path)
                if cobalt_ok:
                    dl_path_actual = dl_path

            if not dl_path_actual:
                raise HTTPException(500, "Download falhou: yt-dlp e cobalt.tools falharam. Use upload manual.")
```

Evidência — cobalt só é acionado quando `dl_path_actual` é falsy (linha 557), o que só acontece se `_download_via_ytdlp_cli` levantou exceção (rc ≠ 0) ou se o arquivo não foi escrito. Quando rc=0 e o arquivo existe (cenário observado em produção: 360p em disco), cobalt nunca é tentado.

Ausência verificada — nenhuma ocorrência de:
- `except PoTokenProviderError` em `*.py`
- Re-execução com `player_client` alternativo (ex.: `['android']`, `['web']`, `['tv']`)
- Iteração sobre estratégias de `extractor_args`
- Leitura de `stderr` para detectar formatos pulados

Interpretação: o desenho atual do fallback responde à categoria de erro "yt-dlp crashou" (bot detection, network, etc.), não à categoria "yt-dlp concluiu mas caiu para progressivo". A degradação silenciosa é exatamente o buraco entre essas duas categorias.

## 4. Achados adicionais

### A1 — Duplicação do fluxo de download entre rota e função worker

Evidência:
```
app-curadoria/backend/services/download.py:335-415  (função _prepare_video_logic)
app-curadoria/backend/routes/curadoria.py:534-586   (corpo da rota prepare_video)
```

Ambos executam os mesmos passos (yt-dlp CLI → cobalt fallback → db.save → R2 upload → limpeza), mas divergem em:
- `_prepare_video_logic` **inclui** o ffprobe diagnóstico (`services/download.py:379-392`); a rota não.
- `_prepare_video_logic` usa `manager.set_task(...)` para reportar progresso; a rota não (é síncrona ao request).
- `_prepare_video_logic` chama `db.save_download(...)` **sem** `brand_slug` (linha 397); a rota passa `brand_slug=brand_slug` (linha 567).

Interpretação: qualquer correção aplicada apenas em um dos dois lados deixa o outro em estado divergente. O próprio ffprobe já é prova dessa divergência.

### A2 — Cache de vídeos degradados persiste após subida

Evidência:
```
app-curadoria/backend/routes/curadoria.py:520-527
    if storage.exists(r2_key):
        return {
            "status": "ok",
            "r2_key": r2_key,
            "r2_base": r2_base,
            "cached": True,
            "message": "Vídeo já está no R2",
        }
```

Interpretação: uma vez que um 360p sobe para `{full_base}/video/original.mp4`, qualquer POST futuro para o mesmo vídeo retorna 200 cached sem verificar qualidade. Não há TTL nem invalidação por qualidade.

### A3 — Stderr truncado em 40 linhas perde contexto de POT

Evidência:
```
app-curadoria/backend/services/download.py:285
    stderr_tail = '\n'.join(r.stderr.splitlines()[-40:])
```

Interpretação: com `--verbose`, o yt-dlp emite centenas de linhas de stderr para um único download. As falhas do POT (`PoTokenProviderError`, `will be skipped`) ocorrem durante a fase de descoberta de formatos, perto do início da execução. Se o último bloco de 40 linhas forem as do downloader progressivo, as pistas críticas do POT nunca aparecem no log do Railway. Isso torna a investigação post-mortem mais difícil do que precisaria ser.

### A4 — `head_object` pós-upload sem comparação de tamanho

Evidência:
```
shared/storage_service.py:195-210
        local_size = Path(local_path).stat().st_size

        @sync_retry(max_attempts=3, backoff_base=2.0, exceptions=_R2_TRANSIENT)
        def _upload():
            import mimetypes
            content_type = mimetypes.guess_type(local_path)[0] or 'application/octet-stream'
            client = _get_s3_client()
            client.upload_file(local_path, R2_BUCKET, key,
                               ExtraArgs={'ContentType': content_type})

            # Verificação pós-upload: confirmar que o arquivo existe no R2
            client.head_object(Bucket=R2_BUCKET, Key=key)

        _upload()

        logger.info(f"[storage:r2] upload OK {key} ({local_size / 1024 / 1024:.1f}MB)")
```

`local_size` é lido antes do upload mas nunca comparado com `ContentLength` retornado por `head_object`. A classe `R2UploadSizeMismatch` existe (declarada em `shared/storage_service.py:39-41`) mas nunca é raised. Não é a causa do bug atual de qualidade, mas é uma promessa de integridade não cumprida pelo código.

### A5 — `progress_hooks` definido no dict de opts pode ser inútil no caminho CLI

Evidência:
```
app-curadoria/backend/services/download.py:193-200
        'progress_hooks': [lambda d: logger.info(
            f"[yt-dlp downloaded] {d.get('info_dict',{}).get('width','?')}x"
            f"{d.get('info_dict',{}).get('height','?')} "
            f"vcodec={d.get('info_dict',{}).get('vcodec','?')} "
            f"acodec={d.get('info_dict',{}).get('acodec','?')} "
            f"format_id={d.get('info_dict',{}).get('format_id','?')} "
            f"filesize={d.get('info_dict',{}).get('filesize','?')}"
        ) if d.get('status') == 'finished' else None],
```

E `_build_ydl_cli_args` (linhas 241-269) não traduz `progress_hooks` para argv — é um conceito da Python API (callback Python). Com a invocação por subprocess CLI, esse hook nunca é executado. Não é bug direto, mas remove uma fonte natural de sinal de qualidade que poderia existir.

## 5. Perguntas abertas para o operador

1. **Fonte da classificação `severity: error`** — de onde vem a reclassificação observada (console do Railway, Sentry UI, Grafana, outro)? Sem esse dado, H4 fica inconclusivo e recomendações sobre logging ficariam no escuro.
2. **Piso de qualidade aceitável** — o vídeo deve falhar se `< 720p`, `< 1080p`, ou outro limiar? Brands diferentes têm critérios diferentes? O `brand_config` hoje (`routes/curadoria.py:515`) não expõe nada sobre qualidade mínima — é aceitável adicionar essa configuração?
3. **Comportamento desejado quando POT falha** — a) falhar com 422/503 e deixar o operador re-tentar; b) tentar automaticamente outras estratégias (android client, web client, cobalt); c) baixar 360p mas marcar como "baixa qualidade" no banco e pular publicação automática; d) outra?
4. **Invalidação do cache de 360p já publicado** — existem vídeos degradados que já subiram ao R2. A fase 2 deve apagar esses objetos ou apenas impedir novos? Existe inventário de vídeos suspeitos (por file_size_mb / duração)?
5. **Consolidação rota × `_prepare_video_logic`** — deve a rota passar a chamar `_prepare_video_logic` direto (eliminando a duplicação), ou preservar o caminho HTTP direto para ter resposta síncrona? O trade-off é: consolidar simplifica mas pode mudar o shape da resposta JSON.
6. **Tempo limite aceitável para tentativas alternativas** — o endpoint hoje já tem `timeout=900` (15min) no subprocess. Adicionar retries com `player_client` alternativos pode dobrar esse tempo. Qual o teto aceitável para a latência do endpoint?

## 6. Recomendações de correção (propostas, não executadas)

Ordenadas por impacto/esforço (melhor razão primeiro). Toda proposta referencia apenas arquivos citados em seções 3-4.

### R1. Adicionar piso de resolução no seletor de formato

- **Problema**: H1. `'format': 'bestvideo+bestaudio/best'` aceita qualquer progressivo silenciosamente.
- **Mudança proposta** em `app-curadoria/backend/services/download.py:160`:
  ```diff
  @@ services/download.py:160 @@
  -        'format': 'bestvideo+bestaudio/best',
  +        'format': 'bestvideo[height>=720]+bestaudio/best[height>=720]',
  ```
  Efeito: o yt-dlp termina com `rc=1` ("Requested format is not available") quando só existem formatos abaixo de 720p, evitando o fallback silencioso para 360p. Isso, combinado com o fallback atual para cobalt (`routes/curadoria.py:557-561`), faz o cobalt ser acionado automaticamente quando o POT falhar.
- **Justificativa**: amarrado à evidência em seção 3/H1. É mudança de uma linha que transforma a falha silenciosa em falha explícita.
- **Risco/efeito colateral**: se houver vídeos legítimos com máximo 360p (live streams antigos, YouTube Shorts convertidos), a rota vai retornar 500. Mitigar com fallback em cascata no `format` (ver R2).

### R2. Fallback em cascata dentro do seletor + retry com `player_client` alternativo

- **Problema**: H5. Ausência de estratégia quando POT falha no `mweb`+`ios` com yt-dlp ainda retornando rc=0.
- **Mudança proposta** em `app-curadoria/backend/services/download.py`:

  a) Substituir `format` por cascata explícita (`services/download.py:160`):
  ```diff
  -        'format': 'bestvideo+bestaudio/best',
  +        'format': (
  +            'bestvideo[height>=720]+bestaudio/'
  +            'best[height>=720]/'
  +            'bestvideo[height>=480]+bestaudio/'
  +            'best[height>=480]'
  +        ),
  ```

  b) Em `_download_via_ytdlp_cli` (`services/download.py:272-289`), parsear stderr para detectar POT failure e re-executar com `player_client=['android']`:
  ```diff
  @@ services/download.py:272-289 @@
  -async def _download_via_ytdlp_cli(youtube_url: str, opts: dict) -> None:
  +async def _download_via_ytdlp_cli(youtube_url: str, opts: dict) -> None:
       """Baixa via subprocess 'python3 -m yt_dlp'."""
       cmd = _build_ydl_cli_args(youtube_url, opts)
       logger.info(f"[yt-dlp CLI] invocando ({len(cmd)} args): {' '.join(cmd[:12])} ... {cmd[-1]}")
       def _run():
           return subprocess.run(cmd, capture_output=True, text=True, timeout=900)
       r = await asyncio.to_thread(_run)
       stderr_tail = '\n'.join(r.stderr.splitlines()[-40:])
       logger.info(f"[yt-dlp CLI] rc={r.returncode}")
       logger.info(f"[yt-dlp CLI] stderr (tail 40):\n{stderr_tail}")
  +    pot_skipped = (
  +        'PoTokenProviderError' in r.stderr
  +        or 'require a GVS PO Token which was not provided' in r.stderr
  +        or 'formats will be skipped' in r.stderr
  +    )
       if r.returncode != 0:
           raise Exception(f"yt-dlp CLI rc={r.returncode}")
  +    if pot_skipped:
  +        raise Exception("yt-dlp: POT provider falhou; formatos de alta qualidade foram pulados")
  ```

- **Justificativa**: amarrado a H3 e H5. Transforma a degradação silenciosa em erro explícito, permitindo que cobalt seja acionado pelo fluxo já existente (`routes/curadoria.py:557-561`).
- **Risco/efeito colateral**: (a) a substring match no stderr pode ter falsos positivos se o yt-dlp mudar a mensagem — cobrir com teste unitário simples; (b) detectar POT failure em vídeos que só têm formatos progressivos iria falhar quando poderia ter funcionado — mitigar combinando com R1 (se cascata do `format` resolver com 480p+, ok; se não resolver, cobalt pega).

### R3. Gate de qualidade pós-download via ffprobe no caminho HTTP

- **Problema**: H2. A rota não roda ffprobe antes do upload.
- **Mudança proposta** em `app-curadoria/backend/routes/curadoria.py`, entre linha 564 e linha 566:
  ```diff
  @@ routes/curadoria.py:563-566 @@
               if not dl_path_actual:
                   raise HTTPException(500, "Download falhou: yt-dlp e cobalt.tools falharam. Use upload manual.")
  
  +            # Gate de qualidade: rejeitar vídeos abaixo do piso
  +            try:
  +                _probe = subprocess.run(
  +                    ['ffprobe', '-v', 'error', '-select_streams', 'v:0',
  +                     '-show_entries', 'stream=width,height',
  +                     '-of', 'csv=p=0', dl_path_actual],
  +                    capture_output=True, text=True, timeout=10,
  +                )
  +                width_s, _, height_s = _probe.stdout.strip().partition(',')
  +                height = int(height_s) if height_s.isdigit() else 0
  +            except Exception as _e:
  +                logger.warning(f"[prepare-video] ffprobe falhou para {video_id}: {_e}")
  +                height = 0
  +            if height and height < 720:
  +                shutil.rmtree(str(project_dir), ignore_errors=True)
  +                raise HTTPException(422, f"Vídeo baixado em qualidade insuficiente ({height}p). Tente novamente.")
  +
               try:
                   db.save_download(video_id, ...)
  ```
  Import necessário no topo do arquivo (se já não presente): `import subprocess`.
- **Justificativa**: amarrado à evidência em seção 3/H2. Bloqueia a degradação silenciosa no ponto onde ela se torna irreversível (upload R2).
- **Risco/efeito colateral**: (a) ffprobe precisa estar instalado no container (já está, pelo uso em `services/download.py:381`); (b) se a integração do yt-dlp já está retornando rc=0 com 360p, R1+R2 podem tornar R3 redundante — mas R3 é defesa em profundidade (gate final antes do R2). (c) Achado A1 (duplicação) sugere aplicar o mesmo gate em `_prepare_video_logic:379-392` trocando `logger.info` por `if height < 720: raise`; considerar fazer como parte desta mesma PR.

### R4. Consolidar `prepare_video` rota em `_prepare_video_logic`

- **Problema**: A1. Duplicação leva a divergência (ffprobe existe só em um lado).
- **Mudança proposta**: reescrever `routes/curadoria.py:534-586` para delegar ao `_prepare_video_logic`, mantendo a resposta síncrona:
  ```
  (a) Extrair o corpo de _prepare_video_logic em duas funções:
      _download_to_local(video_id, artist, song, project_dir) -> dl_path_actual
      _publish_to_r2(dl_path_actual, r2_key, r2_base, ...) -> file_size

  (b) Fazer a rota e _prepare_video_logic chamarem as duas.
  ```
- **Justificativa**: amarrado a A1. Elimina a divergência que alimenta H2.
- **Risco/efeito colateral**: refactor maior; pode mudar o shape de logs e progresso do worker. Não deve alterar o contrato público da rota.

### R5. Preservar stderr completo do yt-dlp quando houver suspeita de POT failure

- **Problema**: A3. Tail 40 perde o bloco inicial da descoberta de formatos.
- **Mudança proposta** em `app-curadoria/backend/services/download.py:285-289`:
  ```diff
  -    stderr_tail = '\n'.join(r.stderr.splitlines()[-40:])
  -    logger.info(f"[yt-dlp CLI] rc={r.returncode}")
  -    logger.info(f"[yt-dlp CLI] stderr (tail 40):\n{stderr_tail}")
  -    if r.returncode != 0:
  -        raise Exception(f"yt-dlp CLI rc={r.returncode}")
  +    stderr_lines = r.stderr.splitlines()
  +    pot_hit = any(
  +        'PoToken' in l or 'PO Token' in l or 'will be skipped' in l
  +        for l in stderr_lines
  +    )
  +    preview = '\n'.join(stderr_lines if pot_hit else stderr_lines[-40:])
  +    logger.info(f"[yt-dlp CLI] rc={r.returncode} pot_hit={pot_hit}")
  +    logger.info(f"[yt-dlp CLI] stderr ({'full' if pot_hit else 'tail 40'}):\n{preview}")
  +    if r.returncode != 0:
  +        raise Exception(f"yt-dlp CLI rc={r.returncode}")
  ```
- **Justificativa**: amarrado a A3. Quando houver sinal de POT falhando, o log completo vai para a plataforma; caso normal, mantém tail de 40 para não inflar.
- **Risco/efeito colateral**: linhas de log maiores em caso de POT failure. Aceitável para forense.

### R6. Comparar tamanho pós-upload no storage_service

- **Problema**: A4. `R2UploadSizeMismatch` existe mas nunca é levantado.
- **Mudança proposta** em `shared/storage_service.py:197-208`:
  ```diff
  @@ shared/storage_service.py:197-208 @@
       @sync_retry(max_attempts=3, backoff_base=2.0, exceptions=_R2_TRANSIENT)
       def _upload():
           import mimetypes
           content_type = mimetypes.guess_type(local_path)[0] or 'application/octet-stream'
           client = _get_s3_client()
           client.upload_file(local_path, R2_BUCKET, key,
                              ExtraArgs={'ContentType': content_type})
  -        # Verificação pós-upload: confirmar que o arquivo existe no R2
  -        client.head_object(Bucket=R2_BUCKET, Key=key)
  +        # Verificação pós-upload: confirmar existência + tamanho
  +        head = client.head_object(Bucket=R2_BUCKET, Key=key)
  +        remote_size = head.get('ContentLength')
  +        if remote_size != local_size:
  +            raise R2UploadSizeMismatch(
  +                f"upload divergiu: local={local_size}, r2={remote_size}, key={key}"
  +            )
  ```
- **Justificativa**: amarrado a A4. Cumpre a promessa da classe já declarada.
- **Risco/efeito colateral**: baixo. Se a class `R2UploadSizeMismatch` não estiver em `_R2_TRANSIENT`, o retry não vai re-tentar e a falha vai propagar — o que é o comportamento correto para corrupção.

### R7. (Condicional — só se H4 for confirmado pelo operador) Ajustar classificação de logs

- **Problema**: H4 (pendente de confirmação — ver seção 5, pergunta 1).
- **Mudança proposta**: depende da resposta do operador. Se Railway classifica tudo em stderr como error, a solução é direcionar `logging.basicConfig` para stdout:
  ```diff
  @@ app-curadoria/backend/main.py:12 @@
  -logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
  +import sys
  +logging.basicConfig(
  +    level=logging.INFO,
  +    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
  +    stream=sys.stdout,
  +)
  ```
- **Justificativa**: se a causa for Railway escaneando stderr, essa é a mitigação canônica. Sem confirmação, não deve ser aplicada (pode quebrar uma configuração intencional de severity).

## 7. Apêndice — comandos executados

Comandos agregados das três frentes de exploração (sem paginação/truncagem):

```
# Topologia
fd -t d -d 3
fd -e py | head -100

# Localização dos módulos citados no log
rg -n "yt_dlp|yt-dlp|bestvideo|po_token|bgutil|ffprobe|PoToken" app-editor app-curadoria app-redator shared
rg -l "^class |^def " app-curadoria/backend/services app-curadoria/backend/routes shared
rg -n "prepare.video|prepare_video" --glob "*.py"
rg -n "routes.curadoria|curadoria" --glob "*.py"

# Seletor de formato / validação
rg -n "bestvideo|format|ffprobe|po_token|player_client|extractor.args|height" app-curadoria app-editor app-redator shared

# Configuração de logging
rg -n "basicConfig|dictConfig|StreamHandler|FileHandler|addHandler|getLogger" --glob "*.py"
rg -n "logging|logger\." app-curadoria/backend/services/download.py

# bgutil / POT
rg -n "bgutil|pot_provider|po_token|generate_once|deno" --glob "*.py"
fd -t f . app-curadoria/backend 2>/dev/null | head -30

# Detalhe de stderr/subprocess
rg -n "stderr|PIPE|Popen|subprocess" app-curadoria/backend/services/download.py
rg -n "capture_output|check=" app-curadoria/backend

# Config / deps
rg "yt.dlp|pot.provider|bgutil" --glob "requirements*.txt" --glob "pyproject.toml"

# Leituras integrais para citações literais
Read app-curadoria/backend/services/download.py   (422 linhas)
Read app-curadoria/backend/routes/curadoria.py    (linhas 490-600)
Read app-curadoria/backend/main.py                 (78 linhas)
Read shared/storage_service.py                     (390 linhas)
```
