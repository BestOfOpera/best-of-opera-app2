# Fase 2 — Plano revisado (não executado)

> Este plano incorpora as revisões do operador sobre `AUDIT_REPORT.md`. Nenhum patch
> deve ser aplicado sem uma nova aprovação explícita ("pode executar PR-X").

## Contexto

A auditoria (ver `AUDIT_REPORT.md`) confirmou H1, H2, H3, H5 e marcou H4 como
inconclusivo. O operador aprovou o relatório como base factual e definiu ajustes
sobre a seção 6 antes da execução. Este documento consolida o plano de execução
com:

- Recomendações aprovadas e suas revisões.
- Ordem obrigatória de PRs.
- Baseline de observabilidade antes dos fixes.
- Procedimento de limpeza R2 e testes empíricos obrigatórios.
- Comandos de rollback por patch.
- Risco residual explícito (bgutil POT provider).

## 1. Decisões sobre a seção 6 do relatório

| Item | Status | Observação |
|---|---|---|
| R1 — piso 720p duro | **APROVADO** | Aplicar exatamente o diff original de R1. |
| R2(a) — cascata 720→480 | **REJEITADO** | Reabriria o buraco da degradação silenciosa em 480p. Não aplicar. |
| R2(b) — detectar POT no stderr | **APROVADO COM MODIFICAÇÃO** | Rebaixar de `raise` para `logger.warning`. Gate de qualidade é ffprobe (R3), não grep em stderr — grep tem falso positivo quando `mweb` funciona mas `ios` é pulado. |
| R3 — gate ffprobe na rota | **APROVADO COM MODIFICAÇÃO** | Trocar `if height and height < 720` por `if height < 720`. Se `ffprobe` falhar (height=0), **rejeitar** o vídeo (não aprovar). |
| R4 — consolidar rota ↔ `_prepare_video_logic` | **APROVADO, APLICAR PRIMEIRO** | Antes de R1 e R3, para não escrever o gate em dois lugares e depois fundir. |
| R5 — stderr completo em POT hit | **APROVADO** | Sem modificação. |
| R6 — size check pós-upload R2 | **APROVADO** | Sem modificação. |
| R7 — `stream=sys.stdout` no logging | **PENDENTE** | Só aplicar se H4 for confirmado com origem concreta (Railway/Sentry/Grafana). |

## 2. Revisões de diff (texto final aprovado)

### R2(b) — warning (não raise)

Em `app-curadoria/backend/services/download.py`, substituir o diff original de
R2(b) por:

```diff
@@ services/download.py:285-289 @@
     stderr_tail = '\n'.join(r.stderr.splitlines()[-40:])
     logger.info(f"[yt-dlp CLI] rc={r.returncode}")
     logger.info(f"[yt-dlp CLI] stderr (tail 40):\n{stderr_tail}")
+    pot_skipped = (
+        'PoTokenProviderError' in r.stderr
+        or 'require a GVS PO Token which was not provided' in r.stderr
+        or 'formats will be skipped' in r.stderr
+    )
+    if pot_skipped:
+        logger.warning("[yt-dlp CLI] POT provider falhou; formatos podem ter sido pulados. Gate ffprobe valida a qualidade final.")
     if r.returncode != 0:
         raise Exception(f"yt-dlp CLI rc={r.returncode}")
```

Racional: quando `mweb` consegue POT mas `ios` é pulado, o yt-dlp pode ainda
entregar 1080p via mweb. Raise causaria falha falsa. O gate autoritativo é o
ffprobe pós-download (R3).

### R3 — rejeitar quando ffprobe falha

Em `app-curadoria/backend/routes/curadoria.py`, bloco proposto com a lógica
corrigida:

```diff
@@ routes/curadoria.py:563-566 @@
             if not dl_path_actual:
                 raise HTTPException(500, "Download falhou: yt-dlp e cobalt.tools falharam. Use upload manual.")

+            # Gate de qualidade: ffprobe é autoridade. Se falhar, rejeita.
+            height = 0
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
+                # height permanece 0 e cai no gate abaixo
+            if height < 720:
+                shutil.rmtree(str(project_dir), ignore_errors=True)
+                raise HTTPException(
+                    422,
+                    f"Vídeo reprovado no gate de qualidade "
+                    f"(height={height}; piso=720). Tente novamente.",
+                )
+
             try:
                 db.save_download(video_id, ...)
```

Racional: `height=0` significa que não confirmamos a qualidade. Tratar como
reprovação é conservador; o operador pode re-tentar.

Após R4 ter sido mergeada, este gate deve ficar dentro da função consolidada
(`_prepare_video_logic` ou sucessora), não na rota diretamente.

## 3. Ordem de execução obrigatória

Cada item abaixo é um PR separado, merge sequencial, com a limpeza R2 e os 3
testes empíricos obrigatórios (seções 4 e 5) antes do merge de cada PR que
afete qualidade ou fluxo de download (PR-0, PR-A, PR-B, PR-C).

### PR-0 — Baseline de observabilidade (precede todos os fixes)

**Objetivo**: obter número de baseline de height/bitrate/file_size_mb antes de
qualquer mudança, para poder comparar pré/pós.

**Arquivo**: `shared/storage_service.py`

**Patch** (adicionar depois do `upload_file` existir, sem mexer na lógica atual):

```diff
@@ shared/storage_service.py:186-211 @@
     def upload_file(self, local_path: str, key: str) -> str:
         """Upload arquivo local para R2 com verificação de existência. Retorna o key."""
         if not _r2_configured():
             dest = _fallback_path(key)
             if os.path.abspath(local_path) != os.path.abspath(dest):
                 shutil.copy2(local_path, dest)
             logger.debug(f"[storage:local] {local_path} → {dest}")
             return key

         local_size = Path(local_path).stat().st_size

+        # Baseline observability: ffprobe é soft — se falhar, mantém upload
+        probe_info = ""
+        if local_path.lower().endswith('.mp4'):
+            try:
+                import subprocess as _sp
+                _p = _sp.run(
+                    ['ffprobe', '-v', 'error', '-select_streams', 'v:0',
+                     '-show_entries', 'stream=width,height,bit_rate',
+                     '-of', 'csv=p=0', local_path],
+                    capture_output=True, text=True, timeout=10,
+                )
+                probe_info = f" probe={_p.stdout.strip()}"
+            except Exception as _e:
+                probe_info = f" probe=FAIL({_e})"
+
         @sync_retry(max_attempts=3, backoff_base=2.0, exceptions=_R2_TRANSIENT)
         def _upload():
             import mimetypes
             content_type = mimetypes.guess_type(local_path)[0] or 'application/octet-stream'
             client = _get_s3_client()
             client.upload_file(local_path, R2_BUCKET, key,
                                ExtraArgs={'ContentType': content_type})
             client.head_object(Bucket=R2_BUCKET, Key=key)

         _upload()

-        logger.info(f"[storage:r2] upload OK {key} ({local_size / 1024 / 1024:.1f}MB)")
+        logger.info(f"[storage:r2] upload OK {key} ({local_size / 1024 / 1024:.1f}MB){probe_info}")
         return key
```

Racional: esta mudança é puramente aditiva e não altera nenhum contrato. Após
merge, rodar ~10 requisições normais e coletar os logs para ter uma referência
numérica ("antes dos fixes, height médio era X").

**Rollback**: `git revert <sha-do-PR-0>` ou aplicar o diff invertido no trecho
acima.

### PR-A — Consolidação (R4)

**Objetivo**: eliminar a duplicação `routes/curadoria.py:534-586` × `services/download.py:335-415`
para que o gate R3 seja escrito em um único lugar.

**Escopo**:
- Extrair duas funções em `services/download.py`:
  - `_download_to_local(video_id, artist, song, project_dir) -> str | None` (retorna `dl_path_actual`; contém yt-dlp CLI + cobalt fallback + ffprobe diagnóstico atual).
  - `_publish_to_r2(dl_path_actual, r2_key, r2_base, r2_prefix, video_id, artist, song, project_name, youtube_url, brand_slug) -> int` (retorna `file_size`; contém `db.save_download`, `storage.upload_file`, `save_youtube_marker`).
- Reescrever corpo da rota `prepare_video` em `routes/curadoria.py:534-586` para chamar as duas.
- Reescrever corpo de `_prepare_video_logic` em `services/download.py:335-415` para chamar as duas; preservar `manager.set_task(...)` do worker.
- Garantir que a rota continua passando `brand_slug` para `db.save_download` (divergência A1) — se o worker não receber brand_slug, passar `brand_slug=None` nas chamadas do worker até um PR futuro corrigir.

**Critério de aceitação**: antes e depois do merge, `POST /api/prepare-video/a1X4jVgAshc`
deve ter o mesmo shape de resposta JSON. O corpo pode mudar mas o contrato público não.

**Rollback**: `git revert <sha-do-PR-A>`. Como é refactor puro, o revert não
afeta nada além de voltar à duplicação original.

### PR-B — R1 + R3 (fixes de qualidade)

**Objetivo**: transformar a degradação silenciosa em falha explícita.

**Escopo**:
- Aplicar R1 em `services/download.py:160` (diff do `AUDIT_REPORT.md` seção 6.R1).
- Aplicar R3 (versão revisada da seção 2 acima) no ponto consolidado vindo de PR-A.
- Se a ordem for invertida (PR-B antes de PR-A), aplicar R3 tanto em `routes/curadoria.py` quanto em `services/download.py:_prepare_video_logic`. **Evitar esse cenário: executar PR-A primeiro.**

**Rollback**: `git revert <sha-do-PR-B>`. Após revert, o bug da auditoria
volta — só revert em caso de regressão inesperada.

### PR-C — R2(b) (warning de POT no stderr)

**Objetivo**: telemetria para correlacionar falha do POT com reprovação em ffprobe.

**Escopo**: aplicar diff da seção 2 acima (`logger.warning`, não `raise`).

**Rollback**: `git revert <sha-do-PR-C>`. Impacto de rollback: voltamos a não
ter essa correlação nos logs; sem efeito funcional.

### PR-D — R5 (stderr completo em POT hit)

**Objetivo**: preservar o stderr inteiro quando houver sinal de POT failure,
para forense.

**Escopo**: aplicar diff de R5 do `AUDIT_REPORT.md`, sem alteração.

**Rollback**: `git revert <sha-do-PR-D>`. Sem efeito funcional.

### PR-E — R6 (size check no upload R2)

**Objetivo**: cumprir a promessa de `R2UploadSizeMismatch`.

**Escopo**: aplicar diff de R6 do `AUDIT_REPORT.md`, sem alteração.

**Rollback**: `git revert <sha-do-PR-E>`. Efeito de rollback: volta a não
detectar corrupção por tamanho.

### PR-Z (condicional) — R7

**Pré-condição**: operador confirma que Railway/Sentry/Grafana está
classificando linhas de stderr como `severity: error`.

**Escopo**: aplicar diff de R7 do `AUDIT_REPORT.md`.

**Rollback**: `git revert <sha-do-PR-Z>`.

## 4. Procedimento de limpeza R2 (obrigatório antes de cada teste end-to-end)

O cache em `routes/curadoria.py:520-527` devolve o arquivo existente sem
baixar de novo. Para que o teste end-to-end mude um resultado de 360p→720p,
**é obrigatório** apagar o arquivo e o marker antes de cada teste que use
`a1X4jVgAshc`:

**Keys a apagar** (prefixo deduzido do `r2_prefix` da brand `reels-classics` —
confirmar com `load_brand_config('reels-classics')` antes de executar):

```
ReelsClassics/projetos_/Aida Garifullina - O Mio Babbino Caro (Gianni Schicchi  by Giacomo Puccini)/video/original.mp4
ReelsClassics/projetos_/Aida Garifullina - O Mio Babbino Caro (Gianni Schicchi  by Giacomo Puccini)/video/.youtube_id
```

(atenção ao espaço duplo entre "Schicchi" e "by" — preservado conforme
sanitização de `sanitize_name` em `shared/storage_service.py:60`).

**Origem das variáveis de ambiente**

- `R2_ENDPOINT`, `R2_ACCESS_KEY`, `R2_SECRET_KEY`, `R2_BUCKET` são lidas de
  `os.getenv(...)` em `shared/storage_service.py:46-49`.
- Em desenvolvimento local, as variáveis vivem em `.env.railway` na raiz do
  repositório (é como `scripts/railway-env.sh:10` carrega a configuração:
  `source "$ENV_FILE"`). O arquivo está listado em `.gitignore` e não é versionado.
- Forma recomendada para exportar as variáveis para a shell atual (o `source` do
  `railway-env.sh` as mantém locais à função):
  ```bash
  set -a
  source .env.railway
  set +a
  ```

**Script de limpeza parametrizado** (primeira tarefa do PR-0; criado em
`scripts/cleanup_r2_video.py` e versionado no mesmo PR do baseline de
observabilidade):

```bash
# Uso padrão (o script lista antes de apagar e é idempotente)
python scripts/cleanup_r2_video.py \
  "ReelsClassics/projetos_/Aida Garifullina - O Mio Babbino Caro (Gianni Schicchi  by Giacomo Puccini)"
```

Saída esperada: lista de objetos em `.../video/`, depois remoção de
`original.mp4` e `.youtube_id`, depois contagem final. Se as env vars não
estiverem carregadas o script sai com erro descritivo (não faz chamada parcial).

**Se escolher outros vídeos para os testes (b) e (c)** da seção 5, repetir a
limpeza para suas keys correspondentes antes de cada teste, passando o
`<r2_base_key>` apropriado para o mesmo script.

## 5. Testes empíricos obrigatórios antes do merge de cada PR que toca qualidade/fluxo

Aplicar para: **PR-0, PR-A, PR-B, PR-C**. Opcional mas recomendado para PR-D e PR-E.

### Vídeos de teste

- **(a)** `a1X4jVgAshc` — o vídeo que falhou em 2026-04-23 (reproduzir o bug).
- **(b)** Um vídeo 1080p saudável conhecido — escolher um da brand `reels-classics`
  que já tenha sido processado sem incidente. Registrar o `video_id` escolhido
  no PR. Sugestão de seleção: qualquer vídeo que, no inventário R2 atual, esteja
  com `file_size_mb >= 30` para ~180 s de duração.
- **(c)** Um vídeo só-360p — **TODO pendente, confirmar com operador antes de
  abrir PR-B**. Critérios de elegibilidade:
    1. Todos os formatos reportados pelo `yt-dlp -F <video_id>` devem ter
       `height < 720`. Verificar antes com:
       `python3 -m yt_dlp -F https://www.youtube.com/watch?v=<video_id>`.
    2. Preferir vídeo já cadastrado na brand `reels-classics` para que o fluxo
       de `brand_slug` seja exercitado.
    3. Candidatos típicos: uploads antigos do YouTube (pré-2012), live streams
       arquivados de baixa qualidade, Shorts específicos cuja fonte original
       é 480p ou menos. Evitar vídeos com restrição regional / idade — o fluxo
       de cookies muda o comportamento e polui o teste.
    4. Duração < 1800 s (o `--match-filter` em `services/download.py:256` já
       rejeita acima disso).
  Processo: antes de abrir PR-B, apresentar ao operador uma shortlist de
  2–3 candidatos com o output de `yt-dlp -F` de cada, operador escolhe 1.
  Registrar o `video_id` aprovado na PR description de PR-B. Isto é o teste-ácido
  do piso R1: a chamada **deve** falhar em 422, não entregar 360p silenciosamente.

### Protocolo por vídeo

Para cada vídeo (a), (b), (c):

1. **Limpeza R2**: executar o procedimento da seção 4 apontando para a pasta do vídeo.
2. **Chamada HTTP**: `POST /api/prepare-video/{video_id}?artist=...&song=...&brand_slug=reels-classics`.
   - Registrar: status code, corpo completo da resposta JSON, `file_size_mb` retornado.
3. **ffprobe do arquivo gerado**: se o upload R2 completou, baixar o `original.mp4`
   e rodar:
   ```
   ffprobe -v error -select_streams v:0 \
     -show_entries stream=width,height,codec_name,bit_rate \
     -of csv=p=0 original.mp4
   ```
   Registrar width, height, codec, bitrate.
4. **stderr do yt-dlp**: copiar a seção "stderr (tail 40)" ou "stderr (full)"
   dos logs da request e anexar ao ticket. Procurar explicitamente por
   `PoTokenProviderError`, `PO Token`, `will be skipped`.

### Matriz de aceitação

| Vídeo | Pré-fix (bug atual) | Pós PR-B (R1+R3) |
|---|---|---|
| (a) `a1X4jVgAshc` | 200, file_size ≈ 8.6 MB, height=360 | 200 com height≥720 OU 422 com mensagem de qualidade |
| (b) 1080p saudável | 200, height≥720 | 200, height≥720 (sem regressão) |
| (c) só-360p | 200, height=360 (bug!) | 422 "gate de qualidade" |

Qualquer divergência desta matriz pós-merge é motivo para rollback do PR.

## 6. Comando de rollback por patch

Registrar o SHA de cada PR no PR description. Comando padrão:

```bash
# Rollback de um PR específico
git checkout main
git pull
git revert --no-edit <sha-do-PR>
git push origin main  # (apenas com autorização explícita — regra CLAUDE.md)
```

Se múltiplos PRs precisarem ser revertidos em cadeia, reverter em ordem
inversa de merge: último PR primeiro, primeiro PR por último.

Para cada PR, também documentar o diff invertido no PR description — útil
como referência rápida quando `git revert` não é possível (ex.: merge de
squash alterou o SHA).

## 7. Risco residual explícito

Nenhum dos patches R1–R6 **corrige** a causa raiz observada no log:

```
PoTokenProviderError("_get_pot_via_script failed: Unable to run script (caused by IndexError('pop from empty list'))")
```

O erro vem de `/app/bgutil-pot/server/src/generate_once.ts`, que é um submódulo
externo (`bgutil-ytdlp-pot-provider`) e está fora do escopo desta auditoria
(regra 5 da Fase 1). Os patches acima são **mitigação**: transformam o sintoma
(degradação silenciosa) em erro explícito e acionam fallback via cobalt.

Enquanto a causa raiz não for resolvida, o sistema vai operar em regime
degradado: muitos vídeos passarão pelo cobalt como fallback, com latência
maior, e alguns vídeos que o cobalt também não consegue baixar vão falhar
em 500.

**Bloqueador paralelo (rastrear fora deste plano)**:
- Investigar por que `bgutil-pot/server/src/generate_once.ts` dispara `IndexError('pop from empty list')`. Opções:
  - Atualizar `bgutil-ytdlp-pot-provider` para a última versão publicada (se houver fix upstream).
  - Trocar do `script-deno` para o `http` provider (requer subir servidor interno — ver comentário em `services/download.py:183-184`).
  - Trocar de estratégia POT (ex.: provider nativo do yt-dlp com cookie-based POT, ou desistir do POT e usar `player_client=['android']` puro enquanto o YouTube não fecha o Android client também).

Este trabalho **não** é coberto pelos PR-0 a PR-E acima. Criar issue separada.

## 8. Arquivos que serão modificados pelos PRs

Nenhum arquivo novo é criado. Todos já foram auditados na Fase 1.

| PR | Arquivo(s) | Linhas aproximadas |
|---|---|---|
| PR-0 | `shared/storage_service.py` | 186-211 |
| PR-A | `app-curadoria/backend/services/download.py`, `app-curadoria/backend/routes/curadoria.py` | 335-415 em services; 534-586 em routes |
| PR-B | mesmos de PR-A + `app-curadoria/backend/services/download.py:160` | 160 (R1) + bloco do gate consolidado |
| PR-C | `app-curadoria/backend/services/download.py` | 285-289 |
| PR-D | `app-curadoria/backend/services/download.py` | 285-289 (mesmo bloco de PR-C, ampliado) |
| PR-E | `shared/storage_service.py` | 197-208 |
| PR-Z | `app-curadoria/backend/main.py` | 12 |

## 9. Cronograma sugerido (sem datas — depende da aprovação)

1. **Aprovação deste plano pelo operador.**
2. PR-0 (baseline) — merge + 24 h de coleta em produção.
3. PR-A (refactor) — merge + smoke test (a), (b), (c).
3.5. **Checkpoint obrigatório pós-PR-A, antes de abrir PR-B**: executar pelo
   menos UMA requisição real `POST /api/prepare-video/{video_id}` em
   staging/produção usando o vídeo (b) saudável (o 1080p escolhido) e comparar
   com a baseline do PR-0. Critério de não-regressão: `height`, `bit_rate` e
   `file_size_mb` no log `[storage:r2] upload OK ... probe=...` devem bater com
   os números pré-refactor (tolerância < 5% no bitrate por variação de encoder).
   **Reportar o resultado ao operador e aguardar sinal verde antes de abrir PR-B.**
   Se a chamada regredir, abrir PR de revert de PR-A e investigar antes de
   continuar.
4. PR-B (R1+R3) — merge + testes obrigatórios (a), (b), (c). Se (a) voltar a 720p+, sucesso; se (a) cair em 422, também sucesso (cobalt não conseguiu — registrar).
5. PR-C (R2b) — merge + confirmar que warnings aparecem nos logs quando (a) falha.
6. PR-D (R5) + PR-E (R6) — podem ser paralelos, merge independente.
7. Só depois do sinal verde do operador, abrir issue separada para o bloqueador do bgutil (seção 7).

Nenhum PR deve ser mergeado sem:
- Aprovação explícita do operador ("pode fazer o merge de PR-X").
- Execução do procedimento de limpeza R2 (seção 4) antes do teste end-to-end.
- Registro dos 3 testes empíricos (seção 5) no PR description.

## 10. O que este plano NÃO inclui

- Apagar vídeos degradados já publicados além de `a1X4jVgAshc` (pergunta 4 da seção 5 do `AUDIT_REPORT.md` — pendente de resposta).
- Inventário automatizado de vídeos suspeitos no R2 (file_size_mb / duração baixos).
- Modificação em `bgutil-pot/server/` — submódulo externo, fora do escopo.
- Alteração em `app-editor/` ou `app-redator/` — esses backends não importam yt-dlp.
- Mudança no `download_worker` do worker assíncrono além do estritamente necessário para R4.
