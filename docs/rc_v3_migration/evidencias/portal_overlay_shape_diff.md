# Diff de shape — frontend espera vs backend retorna (projeto #355, RC, pós-Fase 3)

> Fontes:
> - Frontend: `app-portal/lib/api/redator.ts:5-51` + `components/redator/approve-overlay.tsx:29,216-263`
> - Backend: `app-redator/backend/services/claude_service.py:932-1043` (produz) + `routers/projects.py:226-231` (serve)
> - Schema v3.1 do LLM: `docs/rc_v3_migration/rc_overlay_prompt_v3_1.py:587-660`

## A) Campos do PROJETO (nível raiz do payload)

| Campo                 | Frontend espera? (redator.ts:5-51)   | Backend retorna? (schemas.py:90-136) | Tipo bate? |
|-----------------------|--------------------------------------|---------------------------------------|------------|
| `id`                  | sim                                  | sim                                   | sim        |
| `overlay_json`        | `Item[] \| null`                     | `Optional[list]` (sem item tipado)    | **divergente** — ver B |
| `post_text`           | `string \| null`                     | `Optional[str]`                       | sim        |
| `brand_slug`          | `string`                             | `str`                                 | sim        |
| `automation_json`     | `Record<string, any> \| null`        | `Optional[dict]`                      | sim        |
| `hooks_json`          | estrutura tipada com `ganchos[]`     | `Optional[dict]`                      | ok (dict livre) |
| `warnings`            | `string[]?`                          | `List[str] = []`                      | sim        |

Nenhum campo raiz desaparece na Fase 3. Só o `overlay_json` muda de shape
interno — ver B.

## B) Itens dentro de `overlay_json` (lista heterogênea pós-Fase 3)

Colunas:
- **FE espera**: sim (não-opcional), sim? (opcional), não
- **BE retorna (v3.1)**: indica em QUAIS variantes do item o campo aparece
- **Crash no frontend?**: se o acesso sem guard quebra quando o campo está ausente

### B.1 — Itens normais (gancho / corpo / cta) — itens 0 a N-1

| Campo                        | FE espera | BE retorna (v3.1) | Tipo bate? | Observação                         |
|------------------------------|-----------|-------------------|------------|------------------------------------|
| `text`                       | sim       | sim               | string     | OK                                 |
| `timestamp`                  | sim       | sim               | "MM:SS"    | OK                                 |
| `type`                       | sim?      | sim               | "gancho"\|"corpo"\|"cta" | OK                   |
| `_is_cta`                    | sim?      | sim               | boolean    | OK                                 |
| `end`                        | sim?      | **não retorna**   | —          | Tipo FE é opcional; sem problema   |
| `numero`                     | não       | não (`_process_overlay_rc` descarta — claude_service.py:971-976) | — | schema do LLM tem, mas backend corta |
| `linhas`                     | não       | não (descartado)  | —          | idem                               |
| `funcao`                     | não       | não (descartado)  | —          | idem                               |
| `evento_mapa`                | não       | não (descartado)  | —          | idem                               |

Todos os itens normais passam sem dificuldade pelo `.map()`. O shape foi
preservado (4 campos: `text`, `timestamp`, `type`, `_is_cta`).

### B.2 — Item SENTINEL `_is_audit_meta` — item N (último, só pós-Fase 3)

Produzido em `claude_service.py:1031-1039` quando a resposta do LLM traz
qualquer um de `fio_unico_identificado`, `pontes_planejadas`, `verificacoes`.
O prompt v3.1 (`rc_overlay_prompt_v3_1.py:587-649`) sempre os produz.

| Campo                        | FE espera | BE retorna (v3.1) | Tipo bate? | **Crash no frontend?** |
|------------------------------|-----------|-------------------|------------|------------------------|
| `text`                       | sim (não-opcional) | **AUSENTE** | — | **SIM — `.split("\\n")` em undefined — linha 250** |
| `timestamp`                  | sim (não-opcional) | **AUSENTE** | — | não (Input recebe undefined) |
| `type`                       | opcional  | ausente           | —          | não                    |
| `_is_cta`                    | opcional  | ausente           | —          | não (undefined === true → false) |
| `_is_audit_meta`             | **não conhecido** | `true`    | boolean    | não (só não é lido)    |
| `fio_unico_identificado`     | **não conhecido** | string    | string     | não (nunca acessado)   |
| `pontes_planejadas`          | **não conhecido** | `string[]`| array      | não                    |
| `verificacoes`               | **não conhecido** | objeto aninhado | object| não                    |
| `verificacoes.cortes_aplicados` | **não conhecido** | `{tipo,texto_candidato,motivo}[]` | array | não |

O sentinel é o vetor de regressão. Ele existe agora porque a v3.1 o produz
(`claude_service.py:1031-1039`) e sobrevive até o frontend porque o endpoint
`GET /api/projects/{id}` não filtra (`routers/projects.py:226-231`).

## C) Localização exata do crash

```
app-portal/components/redator/approve-overlay.tsx:216  overlay.map((entry, i) => {
app-portal/components/redator/approve-overlay.tsx:217    const isCta = entry._is_cta === true   // sentinel: false
app-portal/components/redator/approve-overlay.tsx:248    (() => {
app-portal/components/redator/approve-overlay.tsx:249      if (isRC) {                          // #355: true
app-portal/components/redator/approve-overlay.tsx:250        const longest = Math.max(...(entry.text.split("\n").map((l: string) => l.length)), 0)
                                                    ^                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                                    |                         TypeError: Cannot read properties of undefined (reading 'split')
                                                    └── entry é o sentinel
```

**Determinístico** para qualquer projeto RC (`brand_slug === "reels-classics"`)
cujo overlay foi gerado com o prompt v3.1 — ou seja, todo overlay novo de RC
desde o merge `90add64` em 2026-04-22.

Para projetos NÃO-RC (brand_slug != "reels-classics") o branch `else` (linha
258) seria executado: `entry.text.length` em undefined retorna `undefined`,
`undefined > 70` é `false`, e o DOM renderiza `"undefined/70"` — **feio**, mas
**não crasha**. Isso explica por que o operador viu o sintoma especificamente
ao abrir um projeto RC.

## D) Campos que existiam pré-Fase 3 e continuam presentes

Não houve remoção. Os 4 campos dos itens normais (`text`, `timestamp`, `type`,
`_is_cta`) estão idênticos ao shape pré-Fase 3 — confirmação em A.5 via diff de
`_process_overlay_rc`.

## E) Por que o `updateEntry` e `handleApprove` não quebram na mesma hora

- `updateEntry` (linha 116) só é chamado em `onChange` de Input/Textarea. O
  sentinel não tem interação — mas se o usuário editasse o campo do sentinel
  (que não existe visualmente por causa do crash anterior), o spread
  preservaria `_is_audit_meta`.
- `handleApprove` (linha 146) só roda no clique final. O usuário não chega lá
  porque a tela de erro aparece antes.

Esses caminhos não são evidência de crash, mas são vetores para corrupção de
dados no banco se o sentinel for reenviado após aprovação futura (p. ex., em
projeto NÃO-RC onde não há crash imediato).
