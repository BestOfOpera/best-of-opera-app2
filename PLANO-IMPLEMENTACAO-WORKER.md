# Plano de Implementação — Worker Sequencial + State Machine Resiliente

## Contexto

Este é um pipeline de edição de vídeo musical (ópera) rodando em FastAPI + Next.js no Railway (containers efêmeros). O problema central: tasks longas (tradução Gemini ~12min, render FFmpeg ~15min) usam `BackgroundTasks` fire-and-forget. Quando o container reinicia, o status fica preso no banco para sempre.

Estamos substituindo `BackgroundTasks` por um worker único com `asyncio.Queue`, sessões curtas de banco, heartbeat, e idempotência.

**Volume:** 1-3 edições/dia, concorrência = 1 (um vídeo por vez). Se um segundo usuário tentar processar enquanto outro roda, deve ver uma tela de "sistema ocupado".

## Regras de Implementação

1. **Sessões curtas do banco SEMPRE.** Nunca manter uma sessão SQLAlchemy aberta durante I/O externo (Gemini, FFmpeg). Padrão: abrir → ler/escrever → fechar → fazer I/O → abrir de novo para salvar resultado.
2. **Não usar `BackgroundTasks`** para nada que demore mais de 5 segundos. Tudo vai pela `task_queue`.
3. **Não adicionar Celery, Redis, ou qualquer infra nova.** Tudo roda no mesmo container.
4. **Não criar tabelas novas.** Apenas adicionar campos nas tabelas existentes.
5. **Não mudar nomes de endpoints existentes** — o frontend já os consome.
6. **Manter compatibilidade** com o banco PostgreSQL existente (gerar migration Alembic se necessário).

## Bloco 1 — Modelo e Migração

### Arquivo: `app/models/edicao.py`

Adicionar dois campos à classe `Edicao`:

```python
task_heartbeat = Column(DateTime, nullable=True)
progresso_detalhe = Column(JSON, default=dict)
```

### Migration Alembic

Gerar migration para adicionar `task_heartbeat` (DateTime, nullable) e `progresso_detalhe` (JSON, default={}) à tabela `editor_edicoes`.

## Bloco 2 — Worker e Lifespan

### Novo arquivo: `app/worker.py`

Criar módulo com:

**`task_queue`** — `asyncio.Queue` global, módulo-level.

**`worker_loop()`** — async function que roda em loop infinito:
- `await task_queue.get()`
- Cada item é uma tupla `(async_callable, edicao_id)`
- Executa `await task_func(edicao_id)`
- Try/except no loop: se a task falhar com exceção não tratada, logar e continuar (não matar o worker)
- Tratar `asyncio.CancelledError` para shutdown limpo

**`requeue_stale_tasks()`** — função sync chamada no startup:
- Abrir sessão curta
- Buscar edições com `status IN ("traducao", "renderizando", "preview")` E `task_heartbeat < utcnow() - 5 minutos`
- Para cada uma, colocar na `task_queue` a task correspondente ao status
- NÃO atualizar heartbeat aqui (a task faz isso quando começa a rodar)
- Fechar sessão
- Se `task_heartbeat` for NULL (edições antigas sem o campo), tratar como stale

**`is_worker_busy()`** — função que verifica se há task em processamento:
- Consulta banco: existe edição com status IN ("traducao", "renderizando", "preview")?
- Retorna dict com `ocupado: bool`, e se ocupado: `edicao_id`, `etapa`, `progresso`

### Arquivo: `app/main.py`

Modificar o `lifespan` existente:
- Após o setup atual (metadata, migrations, storage), adicionar:
  - `worker = asyncio.create_task(worker_loop())`
  - `requeue_stale_tasks()`
- No `yield` de saída:
  - `worker.cancel()` + `await worker` com try/except CancelledError

## Bloco 3 — Task de Tradução Refatorada

### Arquivo: `app/pipeline.py` (ou onde `_traducao_task` está hoje)

Substituir a `_traducao_task` existente por esta estrutura:

```
async def _traducao_task(edicao_id):
    try:
        # PASSO A — Ler estado (sessão curta)
        with SessionLocal() as db:
            - Buscar edição, validar que existe
            - Buscar idiomas já traduzidos (idempotência)
            - Calcular lista de faltantes
            - Setar status="traducao", heartbeat=now
            - Copiar dados necessários para variáveis locais (idioma_origem, metadados, segmentos)
            - Commit e fechar sessão

        # PASSO B — Loop de tradução (sem sessão aberta)
        for idioma in faltantes:
            # Heartbeat (sessão curta)
            with SessionLocal() as db:
                - Atualizar heartbeat e progresso_detalhe
                - Commit

            # I/O externo (banco FECHADO)
            resultado = await asyncio.wait_for(traduzir_letra(...), timeout=180)

            # Salvar resultado (sessão curta)
            with SessionLocal() as db:
                - Inserir TraducaoLetra
                - Commit

            # Se exceção no idioma: logar, continuar para o próximo

        # PASSO C — Finalização (sessão curta)
        with SessionLocal() as db:
            - Setar status="montagem", passo_atual=7, heartbeat=now
            - Commit

    except Exception as e:
        # ERRO GLOBAL — garantir que status não fica preso
        try:
            with SessionLocal() as db:
                - Setar status="erro", erro_msg=str(e)[:500]
                - Commit
        except Exception:
            logger.error("Não conseguiu salvar erro")
```

### Endpoint de tradução (mesmo arquivo)

Modificar `POST /edicoes/{edicao_id}/traducao-lyrics`:
- Remover `BackgroundTasks` do parâmetro
- Adicionar check-and-set atômico: só aceitar se status permite (ex: "montagem", "alinhamento", "erro")
- Se status não permite → retornar 409
- Se permitiu → `task_queue.put_nowait((_traducao_task, edicao_id))`
- Retornar 200

## Bloco 4 — Task de Render Refatorada

### Mesmo arquivo do pipeline

Substituir `_render_task` existente com a mesma estrutura de sessões curtas:

```
async def _render_task(edicao_id, idiomas_renderizar=None, is_preview=False):
    try:
        # PASSO A — Ler estado (sessão curta)
        with SessionLocal() as db:
            - Buscar edição
            - Determinar idiomas a renderizar
            - Buscar renders já concluídos (idempotência)
            - Calcular faltantes
            - Setar status e heartbeat
            - Copiar dados para variáveis locais
            - Commit

        # PASSO B — Loop de render (sem sessão aberta)
        renders_ok = 0
        for idioma in faltantes:
            # Heartbeat (sessão curta)
            with SessionLocal() as db:
                - Atualizar heartbeat e progresso_detalhe
                - Commit

            # I/O externo (banco FECHADO) — FFmpeg com timeout
            processo = await asyncio.create_subprocess_exec("ffmpeg", ...)
            try:
                await asyncio.wait_for(processo.wait(), timeout=600)
            except asyncio.TimeoutError:
                processo.kill()
                raise

            # Salvar resultado (sessão curta)
            with SessionLocal() as db:
                - Inserir Render com status="concluido" ou "erro"
                - Se concluido: renders_ok += 1
                - Commit

            # IMPORTANTE: Limpar arquivo local após upload pro R2
            # (disco efêmero do Railway é limitado)

        # PASSO C — Finalização
        with SessionLocal() as db:
            - Se is_preview E renders_ok > 0: status = "preview_pronto"
            - Se NOT is_preview E renders_ok > 0: status = "concluido"
            - Se renders_ok == 0: status = "erro", erro_msg = "Nenhum render concluído"
            - Commit

    except Exception:
        # ERRO GLOBAL — mesmo padrão da tradução
```

### Endpoints de render

Modificar `POST /edicoes/{edicao_id}/renderizar-preview` e o endpoint de render final:
- Mesma lógica: check-and-set atômico + enfileirar na `task_queue`
- Remover `BackgroundTasks`

## Bloco 5 — Endpoint de Fila e Desbloqueio

### Novo endpoint: `GET /fila/status`

```python
@router.get("/fila/status")
async def fila_status():
    with SessionLocal() as db:
        em_processamento = db.query(Edicao).filter(
            Edicao.status.in_(["traducao", "renderizando", "preview"])
        ).first()

    if em_processamento:
        return {
            "ocupado": True,
            "edicao_id": em_processamento.id,
            "etapa": em_processamento.status,
            "progresso": em_processamento.progresso_detalhe
        }
    return {"ocupado": False}
```

### Novo endpoint: `POST /edicoes/{edicao_id}/desbloquear`

- Abrir sessão curta
- Contar traduções existentes e renders concluídos para essa edição
- Inferir o status correto: se tem renders → "preview_pronto", se tem traduções → "montagem", senão → volta pro último passo seguro
- Limpar erro_msg
- Commit
- Retornar o novo status

## Bloco 6 — Frontend

### Hook de polling: `lib/hooks/use-polling.ts`

Substituir `usePollingWithTimeout` por polling adaptativo:
- Começa com interval de 3s
- Após 2 minutos, desacelera para 15s
- SEM timeout que para o polling — o backend define se algo travou via heartbeat
- Retornar `{ isSlowPolling: boolean }` em vez de `{ timedOut: boolean }`

### Componente de conclusão: `components/editor/conclusion.tsx`

- Substituir referências a `usePollingWithTimeout` pelo novo hook
- Remover lógica de `timedOut`
- Usar `progresso_detalhe` do backend para mostrar progresso granular (ex: "Traduzindo: en ✓, pt ✓, de ⟳...")

### Tela de "APP ocupado"

Nos componentes que disparam tradução ou render:
- Antes de mostrar o botão de ação, chamar `GET /fila/status`
- Se `ocupado: true`, mostrar banner informativo: "Sistema processando edição #{id} — {etapa}. Aguarde ou volte depois."
- O banner deve mostrar o progresso se disponível
- Botão de ação deve ficar desabilitado

## Ordem de Execução

Implementar nesta ordem, testando cada bloco antes de ir para o próximo:

1. **Bloco 1** — Migration primeiro (o resto depende dos campos novos)
2. **Bloco 2** — Worker + lifespan (infraestrutura base)
3. **Bloco 3** — Tradução (o caso mais problemático, testar bem)
4. **Bloco 4** — Render (mesma lógica, adaptar para FFmpeg)
5. **Bloco 5** — Endpoints auxiliares (fila/status + desbloquear)
6. **Bloco 6** — Frontend (último, quando backend estiver estável)

## O que NÃO fazer

- Não adicionar Celery, Redis, ou containers extras
- Não criar tabelas novas no banco
- Não mudar a estrutura de URLs dos endpoints existentes
- Não usar `with SessionLocal() as db:` envolvendo `await` de I/O externo
- Não setar status "concluido" ou "preview_pronto" se nenhum item teve sucesso
- Não atualizar heartbeat no `requeue_stale_tasks` (a task faz isso)
