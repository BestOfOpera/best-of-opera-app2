---
status: CONCLUÍDO
data: 2026-03-20
atualizado: 2026-03-24
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

## Deploy
Commit `8928bb8` — push para `origin/main` em 2026-03-20. Railway faz deploy automático.

**Atenção pós-deploy:** perfis existentes no banco têm `overlay_interval_secs = 15` salvo. Atualizar manualmente via painel admin (ou SQL) o perfil Best of Opera para `6`.

## Critério de "feito"
- Modelo atualizado e respondendo (verificar nos logs do app-redator)
- Gerar overlay de um projeto de ~60s e confirmar que produz ~10 legendas
- Sem regressão no pipeline de renderização

## Notas de impacto (pesquisa feita em 2026-03-20)
- Frontend `approve-overlay.tsx`: funciona, mas exibe mais linhas (sem paginação — aceitável)
- FFmpeg/renderização: sem limite de legendas, sem impacto
- Não existe limite hardcoded de quantidade de legendas em nenhuma parte do código
- A validação da última legenda em `claude_service.py` (linha ~253) usa `duration_secs - 5` — continua funcional com o novo intervalo

---

## Ciclo 2 — Controle determinístico de timestamps (adicionado em 2026-03-24)

**Origem:** PRD-006 — diagnóstico ao vivo em 23/03/2026
**Problema:** Claude gera timestamps com ~7s de intervalo em vez de 6s, e eventualmente fora de ordem. O campo `overlay_interval_secs` só controlava a *quantidade* de legendas — o espaçamento real era deixado ao Claude (comportamento não-determinístico).
**Decisão:** o script passa a ser a fonte autoritativa de timestamps. Claude é responsável apenas pelo texto e quantidade.

---

### Tarefa 3 — Script de normalização de timestamps em `claude_service.py`

**Arquivo:** `app-redator/backend/services/claude_service.py`

**Onde inserir:** dentro de `generate_overlay()`, após a limpeza de texto (ERR-056) e **antes** da validação ERR-054.

**O que adicionar:**

```python
# Normalize timestamps deterministically (PRD-006)
# Claude generates text only — timestamps are rewritten by this script.
if parsed and brand_config:
    interval_secs = (brand_config or {}).get("overlay_interval_secs", 6)
    duration_secs_norm = 0
    if project.cut_start and project.cut_end:
        try:
            s_parts = project.cut_start.split(":")
            e_parts = project.cut_end.split(":")
            duration_secs_norm = (int(e_parts[0]) * 60 + int(e_parts[1])) - (int(s_parts[0]) * 60 + int(s_parts[1]))
        except (ValueError, IndexError):
            pass
    elif project.original_duration:
        try:
            parts = project.original_duration.split(":")
            duration_secs_norm = int(parts[0]) * 60 + int(parts[1])
        except (ValueError, IndexError):
            pass

    ceiling = max(0, duration_secs_norm - 2) if duration_secs_norm > 0 else None
    for i, entry in enumerate(parsed):
        total = i * interval_secs
        if ceiling is not None and total > ceiling:
            total = ceiling
        entry["timestamp"] = f"{total // 60:02d}:{total % 60:02d}"
    print(f"[generate_overlay] Timestamps normalized: {interval_secs}s interval, {len(parsed)} subtitles")
```

**Critério de feito:** overlay gerado com `interval_secs=6` deve ter timestamps `00:00`, `00:06`, `00:12`... independentemente do que o Claude retornou.

**Status:** ✅ CONCLUÍDO em 2026-03-24

---

### Tarefa 4 — Simplificar prompt em `overlay_prompt.py`

**Arquivo:** `app-redator/backend/prompts/overlay_prompt.py`

**Onde:** função `_calc_subtitle_count()` — remover as linhas prescritivas de espaçamento exato (que foram adicionadas no Fix 1 do commit `8b18555`). Com o script garantindo os timestamps, essas instruções são redundantes e podem confundir o Claude.

**Antes (linhas atuais 38–40):**
```python
f"CRITICAL: Space subtitles exactly {interval_secs} seconds apart. "
f"Each subtitle timestamp must be exactly {interval_secs}s after the previous one. "
f"Do NOT vary the spacing — consistent {interval_secs}s intervals are required."
```

**Depois:**
```python
f"Space subtitles evenly across the video."
```

**Critério de feito:** prompt não menciona mais espaçamento exato — instrui apenas contagem e distribuição uniforme.

**Status:** ✅ CONCLUÍDO em 2026-03-24

---

### Arquitetura final após Ciclo 2 (defense in depth)

```
1. Prompt → Claude gera N legendas com texto (timestamps ignorados)
2. Script pós-geração (Tarefa 3) → atribui 00:00, 00:06, 00:12... baseado em interval_secs do perfil
3. Validação ERR-054 → garante que último timestamp não ultrapassa duration - 5s (segunda camada)
4. Tela de aprovação → usuário revisa e pode editar manualmente
5. approval.py → salva exatamente o que o usuário aprovou
```
