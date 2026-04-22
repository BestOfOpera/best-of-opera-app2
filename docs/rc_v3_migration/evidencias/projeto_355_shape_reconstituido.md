# Shape reconstituído do payload `/api/projects/355` — pós-Fase 3

> Reconstituição estática. Captura direta bloqueada pelo Railway edge (ver `BLOQUEIO_CAPTURA.md`).
> Fonte 1: `app-redator/backend/services/claude_service.py:932-1043` (função `_process_overlay_rc`)
> Fonte 2: `app-redator/backend/routers/projects.py:226-231` (endpoint `GET /api/projects/{id}`)
> Fonte 3: `app-redator/backend/schemas.py:90-136` (`class ProjectOut`)
> Fonte 4: `docs/rc_v3_migration/rc_overlay_prompt_v3_1.py:587-660` (seção `<format>` do prompt v3.1)

## Endpoint

```python
# app-redator/backend/routers/projects.py:226-231
@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: int, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    return project
```

O handler devolve o projeto cru, sem transformar `overlay_json`. **Não há filtro
do sentinel `_is_audit_meta` aqui.** (Contraste: `srt_service.py:18-21`,
`translate_service.py:540,853,960` e `generation.py:187-190` filtram.)

## Shape do campo `overlay_json` no payload

```jsonc
// ProjectOut.overlay_json — schemas.py:115
// overlay_json: Optional[list] = None
//
// Lista heterogênea com 3 variantes de item. Ordem:
//   [gancho, corpo_1, corpo_2, ..., fechamento, cta, audit_meta?]

[
  // Itens narrativos e gancho (claude_service.py:971-976)
  {
    "text":       "Entre os 13 e 16 anos de idade...",   // string — pode conter "\n"
    "timestamp":  "00:00",                                // string "MM:SS"
    "type":       "gancho" | "corpo" | "cta",             // string
    "_is_cta":    false                                   // boolean
  },
  // ... N-1 itens como acima ...
  {
    "text":       "Siga, o melhor da música clássica,\ndiariamente no seu feed. ❤️",
    "timestamp":  "00:47",
    "type":       "cta",
    "_is_cta":    true
  },

  // ÚLTIMO ITEM (v3.1, novo — claude_service.py:1031-1039)
  // Aparece sempre que `response` do LLM traz qualquer um dos campos de
  // auditoria `fio_unico_identificado`, `pontes_planejadas` ou `verificacoes`.
  // O prompt v3.1 (rc_overlay_prompt_v3_1.py:587-649) sempre os produz, logo
  // este item está SEMPRE presente em overlays gerados pós-Fase 3.
  {
    "_is_audit_meta": true,
    "fio_unico_identificado": "…frase única descrevendo o fio narrativo…",
    "pontes_planejadas": [
      "ponte 1: entre X e Y",
      "ponte 2: entre A e B"
    ],
    "verificacoes": {
      "total_legendas": 10,
      "fio_unico_respeitado": true,
      "pontes_causais_inseridas": ["legenda X liga A e B"],
      "ancoragens_causais": ["legenda Y: descrição"],
      "ancoragens_descritivas": ["legenda Z: descrição"],
      "cenas_especificas": ["legenda W: cena"],
      "gancho_fechamento_ecoam": "explicação do espelhamento",
      "paralelismos_encontrados": 0,
      "metaforas_sensoriais": 0,
      "travessoes": 0,
      "cortes_aplicados": [
        {
          "tipo": "fio_secundario | evidente | cena_generica | repeticao",
          "texto_candidato": "…",
          "motivo": "…"
        }
      ]
    }
    // AUSENTES neste item, propositalmente: text, timestamp, type, _is_cta
  }
]
```

## Diferença crucial face ao shape pré-Fase 3

**Pré-Fase 3** (commit `f4f74f2`, baseline do merge `90add64`): todos os itens de
`overlay_json` tinham o shape uniforme `{text, timestamp, type, _is_cta}`.

**Pós-Fase 3** (commit P4 `750ef6b`): a lista passa a conter um último item
heterogêneo (`_is_audit_meta`) que **não tem** `text` nem `timestamp`. A decisão
está documentada em `claude_service.py:1027-1030`:

> "Shape preservada como lista (não dict) para compatibilidade com ~14
> consumidores que iteram overlay_json. Consumidores que precisam filtrar devem
> checar _is_audit_meta."

Todos os consumidores internos do backend (SRT, translate, regenerate-entry)
foram atualizados para filtrar. O frontend Next.js (`app-portal/`) **não foi
alterado pela Fase 3** — verificar em A.5 se isso é o caso — e, portanto,
recebe o sentinel sem filtro explícito.

## Consumers backend e estado de filtro

| Consumer | Arquivo | Filtra sentinel? |
|---|---|---|
| `GET /api/projects/{id}` | `routers/projects.py:226-231` | **NÃO** |
| `srt_service.generate_srt` | `services/srt_service.py:18-21` | sim |
| `translate_service.translate_overlay_json` | `services/translate_service.py:540` | sim |
| `translate_service.translate_one_claude` | `services/translate_service.py:853` | sim |
| `translate_service._chunk_and_translate` | `services/translate_service.py:960` | sim |
| `routers/generation.regenerate-overlay-entry` | `routers/generation.py:187-190` | sim |
| `prompts/rc_automation_prompt.build_rc_automation_prompt` | `prompts/rc_automation_prompt.py:46-51` | sim |
| `_validate_overlay_rc` | `services/claude_service.py:1048-1051` | sim |

Conclusão: o único ponto que devolve `overlay_json` ao mundo externo (e,
portanto, ao frontend Next.js) é o `GET /api/projects/{id}` — e ele não filtra.
