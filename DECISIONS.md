# DECISIONS.md — Decisões Técnicas

## 2026-02-27: aplicar-corte DEVE enfileirar tradução (deadlock silencioso)

**Contexto:** No Teste 1 (edição ID 48), o endpoint `aplicar-corte` setou
`status="traducao"` no banco mas NÃO enfileirou a task na `asyncio.Queue`.
O frontend ficou preso em "traducao" sem nenhum worker processando.

**Causa raiz:** O código original fazia `db.commit()` com status="traducao"
mas não chamava `task_queue.put_nowait()`. A tradução só era disparada
quando o usuário clicava o botão no frontend — mas o frontend exibia
spinner de "traduzindo" automaticamente ao ver status="traducao", criando
deadlock silencioso.

**Decisão:** O fluxo `corte → traducao` é automático. Sempre que
`aplicar-corte` seta `status="traducao"`, a task DEVE ser enfileirada
no worker. Regra absoluta:

> **Em NENHUM cenário deve existir `status="traducao"` sem task enfileirada.**

**Implementação (commit `9d50ec7` + hardening):**
1. `_aplicar_corte_impl()` chama `task_queue.put_nowait((_traducao_task, edicao_id))`
   imediatamente após `db.commit()`.
2. Se o enqueue falhar (improvável mas possível), o status é revertido para
   `"erro"` com mensagem descritiva — nunca fica preso em "traducao".
3. O endpoint `traducao-lyrics` também enfileira (para re-trigger manual).
4. `requeue_stale_tasks()` no startup marca "traducao" sem worker como "erro".

**Fluxo de status confirmado:**
```
corte → traducao (auto-enfileira) → montagem → preview → preview_pronto → renderizando → concluido
```

Para instrumentais: `corte → montagem` (pula tradução).

**Alternativa descartada:** Deixar o frontend disparar tradução manualmente
após corte. Descartada porque cria passo desnecessário e risco de esquecimento.
