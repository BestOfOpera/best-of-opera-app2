# Diff pré vs pós Fase 3 — o que mudou e o que NÃO mudou

**Merge da Fase 3:** `90add64` (merge, 2026-04-22 01:53 local / 04:55 UTC)
**Parents:** `f4f74f2` (baseline pré) e `c17559a` (tip da branch de Fase 3)
**Range auditado:** `f4f74f2..90add64` (commits da Fase 3, inclusive merge)

## 1. Commits na Fase 3 (ordem cronológica)

```
7a1190b  docs(rc): investigação + anexos v3/v3.1 + plano execução
105491f  P1 — fix(redator): limite de 38 chars por linha (v3.1 baseline) em 5 pontos
77e6227  P2 — fix(redator): atualiza RC_CTA e RC_POST_CTA para tabela canônica v3 (F6.8)
df78ed5  P3 — feat(redator): automation prompt v3 com post_text e estratégias A/B/C (F5.2)
750ef6b  P4 — feat(redator): overlay v3.1 com fio dinâmico e cortes_aplicados (F3.1-F3.11)
039337c  P5 — feat(redator): rc_post_prompt v3 da SKILL + save_cta em _format_post_rc
4a1d717  P6 — feat(redator): incorpora regras v3 em _build_translation_prompt (Opção C)
1f7d61b  docs(rc): relatório de execução Fase 3 RC v3/v3.1 (P1-P6 aplicados)
fd36f92  fix(redator): filtro defensivo _is_audit_meta em build_rc_automation_prompt
d8b6d27  fix(redator): blindagem audit_meta em regenerate-overlay-entry + TODO SPEC-009
c17559a  docs(rc): registra bypass explícito do checklist pré-merge
90add64  merge: RC v3/v3.1 migration (Fase 3 da auditoria editorial)
```

11 commits. **Nenhum** dentro de `app-portal/`.

## 2. O que NÃO mudou na Fase 3

### 2.1 Frontend Next.js completo

```bash
$ git log --oneline f4f74f2..90add64 -- app-portal/
(saída vazia — zero commits)
```

**Prova empírica:** o frontend `app-portal/` não foi tocado por nenhum commit
da Fase 3. Todos os arquivos do portal estão idênticos ao estado pré-Fase 3.

Em particular:
- `app-portal/components/redator/approve-overlay.tsx` (365 linhas) — inalterado
- `app-portal/lib/api/redator.ts` interface `Project` — inalterado
- Ou seja, o portal **não sabe da existência** do sentinel `_is_audit_meta`.

### 2.2 Endpoint GET do projeto

```bash
$ git log --oneline f4f74f2..90add64 -- app-redator/backend/routers/projects.py
(saída vazia — zero commits)
```

`routers/projects.py:226-231` (`get_project`) continua idêntico ao pré-Fase 3:
devolve `project` cru via `ProjectOut`, sem nenhum filtro do sentinel antes de
serializar.

### 2.3 Schemas Pydantic

```bash
$ git log --oneline f4f74f2..90add64 -- app-redator/backend/schemas.py
(saída vazia — zero commits)
```

`ProjectOut.overlay_json: Optional[list] = None` e
`ApproveOverlayRequest.overlay_json: list` continuam sem tipar o item. O
schema nunca foi atualizado para refletir que a lista agora é heterogênea.

## 3. O que MUDOU na Fase 3 — mudanças relevantes para a regressão

### 3.1 P4 — `750ef6b` — introdução do sentinel `_is_audit_meta`

`git blame` de `app-redator/backend/services/claude_service.py:1031-1041`
aponta **todas** as linhas da introdução do sentinel para `750ef6ba`:

```
750ef6ba (2026-04-22 01:07:36)  audit_fields = ("fio_unico_identificado", ...)
750ef6ba (2026-04-22 01:07:36)  if any(field in response for field in audit_fields):
750ef6ba (2026-04-22 01:07:36)      audit_item = {
750ef6ba (2026-04-22 01:07:36)          "_is_audit_meta": True,
750ef6ba (2026-04-22 01:07:36)          "fio_unico_identificado": ...,
750ef6ba (2026-04-22 01:07:36)          "pontes_planejadas": ...,
750ef6ba (2026-04-22 01:07:36)          "verificacoes": ...,
750ef6ba (2026-04-22 01:07:36)      }
750ef6ba (2026-04-22 01:07:36)      overlay_json.append(audit_item)
```

**Este é o commit responsável pela mudança de shape que causa a regressão.**

O mesmo commit atualiza internamente `_validate_overlay_rc`, `srt_service` e
`translate_service` para filtrar o sentinel. **Não atualiza:**
- O endpoint `GET /api/projects/{id}` (fora da cadeia de geração)
- O frontend Next.js (fora do escopo do redator backend)
- O schema Pydantic `ProjectOut` / `ApproveOverlayRequest`

### 3.2 Hardening posterior ao P4 — `fd36f92` + `d8b6d27`

Dois commits adicionais de hardening (filtros defensivos em
`build_rc_automation_prompt` e `regenerate-overlay-entry`). São filtros
backend, não tocam no frontend nem no endpoint GET.

### 3.3 Mensagem de commit do merge sobre o bypass

```
Bypass explícito dos 6 itens do checklist "Pending before merge"
autorizado pelo operador — ver docs/rc_v3_migration/NOTAS_EXECUCAO.md
entrada "BYPASS EXPLÍCITO" de 2026-04-22. Risco assumido.
```

Indicação de que o merge ocorreu sem os smoke tests do checklist. Ver
A.7 no relatório final (por que escapou dos testes).

## 4. Mapa da cascata — o sentinel escapa ou é contido?

| Consumer                                         | Filtra? | Evidência (path:linha)                            | Fase 3 atualizou? |
|--------------------------------------------------|---------|---------------------------------------------------|-------------------|
| `_validate_overlay_rc`                           | sim     | `claude_service.py:1048-1051`                     | P4 `750ef6b` sim  |
| `srt_service.generate_srt`                       | sim     | `srt_service.py:18-21`                            | P4 `750ef6b` sim  |
| `translate_service.translate_overlay_json`       | sim     | `translate_service.py:540`                        | P4 `750ef6b` sim  |
| `translate_service.translate_one_claude`         | sim     | `translate_service.py:853`                        | P4 `750ef6b` sim  |
| `translate_service._chunk_and_translate`         | sim     | `translate_service.py:960`                        | P4 `750ef6b` sim  |
| `routers/generation.regenerate-overlay-entry`    | sim     | `generation.py:187-190`                           | `d8b6d27` sim     |
| `prompts/rc_automation_prompt.build_rc_automation_prompt` | sim | `rc_automation_prompt.py:46-51`               | `fd36f92` sim     |
| **`routers/projects.get_project`**               | **NÃO** | **`projects.py:226-231`**                         | **não alterado**  |
| **`app-portal/components/redator/approve-overlay.tsx`** | **NÃO** | **`approve-overlay.tsx:47, 216-250`**      | **não alterado**  |
| `app-editor/backend/app/routes/importar.py`      | sim (acidental, via `.get("text", "").strip()`) | `importar.py:253-256` | não tocado |

O sentinel só escapa por uma via: `get_project` → portal. A rota do editor é
coberta por um filtro que já existia desde antes (filtra por ausência de
texto), não é regressão.

## 5. Interpretação

A regressão é uma consequência direta e previsível da decisão do P4 de
**mudar o shape persistido** (`overlay_json` deixou de ser homogêneo) sem
mudar:

1. O ponto de saída que devolve esse shape ao mundo externo
   (`get_project`).
2. O consumidor externo existente desse ponto de saída
   (`approve-overlay.tsx`).

O comentário no próprio código (`claude_service.py:1029-1030`) já
anunciava o risco:

> "Consumidores que precisam filtrar devem checar _is_audit_meta."

A Fase 3 atualizou 7 consumers internos mas deixou os dois externos
(endpoint HTTP + frontend) órfãos. Não há no repo nenhum commit, nem
TODO, nem issue registrando essa lacuna.

## 6. SHA responsável (para a seção "Causa-raiz" do relatório)

- **Commit de origem da regressão:** `750ef6b` (P4)
- **Commit que consolidou via merge:** `90add64`
- **Branch de origem:** merged em `main` em 2026-04-22 01:53 BRT (04:55 UTC)
- **Autor:** jmancini800 <jmancini.ort@gmail.com>
