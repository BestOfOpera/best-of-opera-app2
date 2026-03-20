---
status: CONCLUÍDO
data: 2026-03-20
---

# SPEC-006 — Atualização do modelo Claude + redução do intervalo de overlay

## Contexto
Duas mudanças pontuais no app-redator:
1. Atualizar o modelo Claude de `claude-sonnet-4-5-20250929` para `claude-sonnet-4-6`
2. Reduzir o intervalo de referência entre legendas de overlay de 15s para 6s

Com 6s de intervalo, um vídeo de 60s passará a gerar ~10 legendas (vs ~4 atualmente).

---

## Tarefa 1 — Atualizar modelo Claude

**Arquivo:** `app-redator/backend/services/claude_service.py` (linha 19)

```python
# Antes
MODEL = "claude-sonnet-4-5-20250929"

# Depois
MODEL = "claude-sonnet-4-6"
```

**Status:** ✅ CONCLUÍDO em 2026-03-20

---

## Tarefa 2 — Reduzir intervalo de overlay de 15s → 6s

Alterar o default de `overlay_interval_secs` em todos os pontos da cadeia.

### 2.1 — `app-redator/backend/config.py`
Localizar o fallback dict com `overlay_interval_secs` e alterar de `15` para `6`.

**Status:** ✅ CONCLUÍDO em 2026-03-20

### 2.2 — `app-editor/backend/app/models/perfil.py`
Localizar o campo `overlay_interval_secs` (linha ~37) e alterar `default=15` para `default=6`.

**Status:** ✅ CONCLUÍDO em 2026-03-20

### 2.3 — `app-editor/backend/app/main.py`
Localizar a SQL migration com `overlay_interval_secs DEFAULT 15` (linha ~348) e alterar para `DEFAULT 6`.

**Status:** ✅ CONCLUÍDO em 2026-03-20

### 2.4 — `app-editor/backend/app/routes/admin_perfil.py`
Localizar o schema Pydantic com `Optional[int] = 15` (linha ~123) e alterar para `Optional[int] = 6`.

**Status:** ✅ CONCLUÍDO em 2026-03-20

### 2.5 — `app-editor/backend/app/services/perfil_service.py`
Localizar o fallback `or 15` (linha ~43) e alterar para `or 6`.

**Status:** ✅ CONCLUÍDO em 2026-03-20

---

## Critério de "feito"
- Modelo atualizado e respondendo (verificar nos logs do app-redator)
- Gerar overlay de um projeto de ~60s e confirmar que produz ~10 legendas
- Sem regressão no pipeline de renderização

## Notas de impacto (pesquisa feita em 2026-03-20)
- Frontend `approve-overlay.tsx`: funciona, mas exibe mais linhas (sem paginação — aceitável)
- FFmpeg/renderização: sem limite de legendas, sem impacto
- Não existe limite hardcoded de quantidade de legendas em nenhuma parte do código
- A validação da última legenda em `claude_service.py` (linha ~253) usa `duration_secs - 5` — continua funcional com o novo intervalo
