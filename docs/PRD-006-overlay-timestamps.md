# PRD-006 — Controle Determinístico de Timestamps do Overlay

**Data:** 23/03/2026
**Baseado em:** diagnóstico ao vivo na sessão 23/03 (conversa sobre overlay do perfil BO/RC)
**Status do ciclo: PENDENTE**

---

## 1. O que foi observado (ponto de partida)

Screenshot da tela "Aprovar Overlay" mostrou dois problemas visíveis:

1. **Intervalos de ~7s** entre legendas, mesmo com `overlay_interval_secs = 6` configurado nos perfis BO e RC
2. **Timestamps fora de ordem**: legenda 9 → `00:54`, legenda 10 → `00:52` (10 aparece antes de 9 cronologicamente)

---

## 2. Diagnóstico completo

### 2.1 — Por que os intervalos saem com ~7s em vez de 6s

**Arquivo:** `app-redator/backend/prompts/overlay_prompt.py`

O campo `overlay_interval_secs` do perfil é lido corretamente e passado ao prompt (`linha 52`). Porém, o prompt instrui o Claude com linguagem não-prescritiva:

```
"using ~{interval_secs}s as a flexible reference interval.
IMPORTANT: This interval is a GUIDE, not a rigid rule.
Cluster subtitles closer together during context-rich moments..."
```

O Claude interpreta "flexible guide" e gera ~7s. Não há nenhuma validação pós-geração que force os timestamps ao intervalo configurado.

**Efeito real do campo `overlay_interval_secs`:**
Ele só influencia a **quantidade** de legendas geradas via `count = duration / interval_secs`. O espaçamento real entre legendas é deixado ao critério do Claude. O campo não controla o que o nome sugere.

---

### 2.2 — Por que os timestamps saem fora de ordem

**Arquivo:** `app-redator/backend/services/claude_service.py` linhas 248–261

Existe uma validação (ERR-054) que ajusta o último timestamp caso ele ultrapasse `duration - 5s`:

```python
if ts_secs > limit:
    new_ts = max(0, duration_secs - 8)
    last_leg["timestamp"] = f"{mins:02d}:{secs:02d}"
```

**O problema:** se o vídeo tem 60s e Claude gerou legenda 10 em `00:57`, o ajuste move para `60 - 8 = 52s` → `00:52`. Mas se legenda 9 já estava em `00:54`, a ordem fica invertida: 9→`00:54`, 10→`00:52`.

O código corrigia o valor absoluto mas não verificava a ordem relativa com a legenda anterior.

---

### 2.3 — Impacto downstream dos timestamps fora de ordem

**Arquivo:** `app-redator/backend/services/srt_service.py` linhas 20–30

`generate_srt()` assume ordem cronológica e usa `overlay_json[i+1]["timestamp"]` para calcular o fim de cada legenda. Com ordem invertida, a legenda 9 receberia `end = 00:51` (1s antes de 00:52), que é **anterior ao seu próprio start `00:54`** — SRT inválido.

---

## 3. O que já foi corrigido nesta sessão (deployado em 23/03)

### Fix 1 — Prompt prescritivo
**Arquivo:** `app-redator/backend/prompts/overlay_prompt.py`
- Substituiu "flexible guide, not a rigid rule" por: *"CRITICAL: Space subtitles exactly {interval_secs}s apart. Do NOT vary the spacing."*
- Removeu "Vary the spacing organically" da regra 2 do prompt

**Limitação:** Claude é não-determinístico. O prompt melhora, mas não garante.

### Fix 2 — Ordem de timestamps após ajuste ERR-054
**Arquivo:** `app-redator/backend/services/claude_service.py`
- Após ajustar o último timestamp, verifica se `new_ts > penultima_ts`. Se não, usa `penultima_ts + 1`
- **Limitação:** cobre apenas o caso onde o ajuste ERR-054 causa a inversão. Não cobre timestamps fora de ordem gerados diretamente pelo Claude sem passar pelo ajuste.

**Commit:** `8b18555` — deployado em produção via Railway.

---

## 4. O que ainda falta fazer (escopo deste ciclo)

### Tarefa principal — Script Python de normalização de timestamps pós-geração

**Decisão tomada na sessão:** não depender do Claude para timestamps. O script deve ser a fonte autoritativa, não um fallback.

**Lógica:**
```python
def normalizar_timestamps(overlay_json: list[dict], interval_secs: int) -> list[dict]:
    for i, entry in enumerate(overlay_json):
        total_secs = i * interval_secs
        mins = total_secs // 60
        secs = total_secs % 60
        entry["timestamp"] = f"{mins:02d}:{secs:02d}"
    return overlay_json
```

**Onde aplicar:** em `claude_service.py`, dentro de `generate_overlay()`, após a limpeza de texto e após a validação ERR-054 existente.

**Por que não na aprovação:** o usuário pode editar timestamps manualmente na tela antes de aprovar — o script na aprovação sobrescreveria edições intencionais silenciosamente.

**O que o Claude passa a fazer:** gera apenas o **texto** e a **quantidade** correta de legendas. Os timestamps que ele retornar são descartados e substituídos pelo script.

---

### Tarefa secundária — Simplificar o prompt (reverter parcialmente o Fix 1)

Com o script garantindo os timestamps, as instruções prescritivas de intervalo no prompt se tornam redundantes. O prompt pode voltar a guiar apenas a **contagem** de legendas, sem mencionar espaçamento exato.

**Arquivo:** `app-redator/backend/prompts/overlay_prompt.py`
- `_calc_subtitle_count()`: remover as linhas `"CRITICAL: Space subtitles exactly..."` — manter apenas contagem
- Regra 2 do prompt: já foi simplificada no Fix 1, está OK

---

## 5. Arquivos envolvidos

| Arquivo | Papel | O que mudar |
|---------|-------|-------------|
| `app-redator/backend/services/claude_service.py` | Geração e validação do overlay | Adicionar chamada ao script de normalização após limpeza de texto |
| `app-redator/backend/prompts/overlay_prompt.py` | Prompt enviado ao Claude | Simplificar `_calc_subtitle_count()` — remover instruções de espaçamento exato |
| `app-redator/backend/services/srt_service.py` | Consome overlay_json | Nenhuma mudança — já funciona corretamente se timestamps estiverem em ordem |
| `app-redator/backend/routers/approval.py` | Salva overlay aprovado | Nenhuma mudança — respeita edição humana |

---

## 6. Riscos e mitigações

| Risco | Probabilidade | Mitigação |
|-------|--------------|-----------|
| Script sobrescreve timing intencional do Claude | Baixo — Claude já não respeita o intervalo | Prompt ainda guia a contagem; texto é gerado livremente |
| Script na aprovação sobrescreve edição do usuário | **Não se aplica** — decidido não aplicar na aprovação | — |
| Script gera timestamp além do `cut_end` (ex: 10 legendas × 6s = 60s em vídeo de 58s) | Médio | No script, limitar `total_secs < duration_secs - 2` como teto |
| Regressão no ERR-054 (último timestamp muito no fim) | Baixo | Manter a validação ERR-054 existente — script roda antes, ERR-054 fica como segunda camada |

---

## 7. Arquitetura final após o ciclo (defense in depth)

```
1. Prompt → Claude gera N legendas com texto (timestamps ignorados)
2. Script pós-geração → atribui timestamps: 0s, 6s, 12s... baseado em interval_secs do perfil
3. Validação ERR-054 → garante que último timestamp não ultrapassa duration - 5s
4. Tela de aprovação → usuário revisa e pode editar manualmente
5. approval.py → salva exatamente o que o usuário aprovou
```

---

## 8. O que NÃO está no escopo deste ciclo

- Alterações no frontend da tela de aprovação
- Validação de timestamps na aprovação (decisão: respeitar edição humana)
- Mudanças no `srt_service.py`
- Mudanças em `overlay_interval_secs` no banco ou na tela de perfil — o campo continua sendo usado pelo script com o mesmo valor

---

## 9. Contexto para o SPEC

Na sessão de SPEC, ler:
1. `app-redator/backend/services/claude_service.py` linhas 214–266 — função `generate_overlay()` completa, para saber exatamente onde inserir a chamada ao script
2. `app-redator/backend/prompts/overlay_prompt.py` linhas 12–45 — `_calc_subtitle_count()`, para simplificar as instruções de espaçamento
3. `app-editor/backend/app/models/perfil.py` linha 37 — confirmar que `overlay_interval_secs` tem default 6
4. `app-redator/backend/config.py` linhas 33–55 — confirmar que `interval_secs` chega corretamente via `brand_config`
