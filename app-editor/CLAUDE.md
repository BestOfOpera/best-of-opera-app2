# app-editor — Regras de Código

> Leia ANTES de editar qualquer arquivo do app-editor.
> Para contexto geral: `CLAUDE.md` da raiz.
> Para arquitetura completa: `CONTEXTO-CODIGO-FINAL.md`.

## Padrão de task do worker
Antes de criar ou editar qualquer task, leia `_traducao_task` em `routes/pipeline.py` como REFERÊNCIA do padrão correto. Toda task DEVE seguir esse mesmo padrão:

- Imports DENTRO do try-except (nunca fora)
- except BaseException (nunca Exception)
- CancelledError faz re-raise após salvar erro
- Sessões curtas: abrir banco → ler/escrever → fechar → I/O externo → abrir de novo
- Heartbeat (task_heartbeat) atualizado antes de CADA operação pesada
- Idempotência: verificar o que já foi feito antes de refazer
- asyncio.wait_for com timeout em toda chamada externa
- Upload R2 + deletar arquivo local após cada render/download

## Checklist pré-commit
- [ ] Imports dentro do try?
- [ ] except BaseException?
- [ ] CancelledError → re-raise?
- [ ] Sessões curtas (zero sessão aberta durante I/O)?
- [ ] Heartbeat antes de operação pesada?
- [ ] Idempotente?
- [ ] Timeout em chamada externa?
- [ ] Upload R2 + delete local?
- [ ] Check-and-set atômico nos endpoints que mudam status?

## Endpoints que mudam status
DEVEM usar UPDATE atômico com WHERE status IN (...). Ver exemplos em `routes/pipeline.py`. Nunca permitir transição de status sem validar o status atual.

## Referências rápidas (ler do código, não decorar)
| Preciso de... | Ler... |
|---------------|--------|
| Status flow completo | `routes/pipeline.py` (constantes _STATUS_PERMITIDOS_*) |
| Padrão de task | `_traducao_task` em `routes/pipeline.py` |
| Estilos de legenda | `services/legendas.py` (ESTILOS_PADRAO) |
| Geometria do frame | `services/legendas.py` (comentários no topo) |
| Modelo principal | `models/edicao.py` |
| Worker e recovery | `worker.py` |
| Variáveis de ambiente | `config.py` |
| Abstração de storage | `shared/storage_service.py` |
