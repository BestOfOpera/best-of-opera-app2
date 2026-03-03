# DECISIONS.md — Decisões Técnicas

## 2026-03-03: Reforço de idioma nos prompts do Redator (language leak fix)

**Problema:** O Claude às vezes finalizava o texto gerado em português, mesmo quando o hook estava em outro idioma (inglês, alemão, italiano, etc.). A última frase "escapava" para português.

**Causa raiz:** A instrução de idioma aparecia apenas uma vez no prompt ("Write ALL content in the SAME LANGUAGE as the Hook/angle field"), sem reforço. O Claude tem tendência de "fechar" a geração no idioma predominante do treinamento.

**Correção em 3 pontos:**

### PONTO 1 — Reforço de idioma no final de cada prompt
Adicionado bloco `ATENÇÃO FINAL` ao final de todos os prompts de geração (overlay, post, youtube), incluindo variantes `_with_custom`. O texto é gerado dinamicamente por `build_language_reinforcement(project)` em `hook_helper.py`.

**Antes (final do prompt overlay):**
```
Write ALL subtitle text in the SAME LANGUAGE as the Hook/angle field. Match the hook's language exactly.
```

**Depois:**
```
Write ALL subtitle text in the SAME LANGUAGE as the Hook/angle field. Match the hook's language exactly.

ATENÇÃO FINAL: Todo o texto acima deve estar 100% em {idioma}. A última frase, assim como todas as outras, deve estar obrigatoriamente em {idioma}. Não finalize em português.
```

### PONTO 2 — System prompt com instrução de idioma
Adicionado system message em `_call_claude()` para todas as gerações de conteúdo:
```
You must write ALL output exclusively in {idioma}. Never switch to Portuguese, even in the final sentence.
```

**Antes:** `_call_claude(prompt)` sem system message.
**Depois:** `_call_claude(prompt, system=system)` com enforcement de idioma.

### PONTO 3 — Validação pós-geração (warning, não bloqueio)
Adicionada função `_check_language_leak()` em `claude_service.py`. Após cada geração, verifica se a última frase contém >= 3 palavras comuns em português (e, de, do, da, que, com, para, uma, um, os, as). Se detectado em idioma não-português, loga:
```
ALERTA: possível trecho em português detectado na geração — revisar manualmente.
```
Não bloqueia — apenas alerta no log para revisão manual.

**Detecção de idioma:** `detect_hook_language(project)` em `hook_helper.py` identifica o idioma do hook via heurística de palavras-chave. Categorias predefinidas = português. Hooks customizados = detecção por frequência de marcadores linguísticos.

**Arquivos alterados:**
- `app-redator/backend/prompts/hook_helper.py` — `detect_hook_language()`, `build_language_reinforcement()`
- `app-redator/backend/prompts/overlay_prompt.py` — reforço no final
- `app-redator/backend/prompts/post_prompt.py` — reforço no final
- `app-redator/backend/prompts/youtube_prompt.py` — reforço no final
- `app-redator/backend/services/claude_service.py` — system prompt + `_check_language_leak()`

---

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
