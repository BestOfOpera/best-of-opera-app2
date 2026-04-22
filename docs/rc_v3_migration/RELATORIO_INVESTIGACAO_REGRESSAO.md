# Relatório de Investigação — Regressão Overlay + Erradicação de Truncamentos (PARCIAL — Bloco A apenas)

> **Status:** Bloco A concluído em sessão PROMPT 5A (2026-04-22).
> Blocos B e C a serem investigados em sessões separadas (PROMPT 5B e PROMPT 5C).
> **Nenhum patch aplicado nesta sessão.** Entregável é exclusivamente diagnóstico + evidências.

---

## 0. Sumário executivo (só do Bloco A)

A tela "Ocorreu um erro inesperado" que o portal exibe ao abrir o overlay de qualquer projeto Reels Classics pós-merge `90add64` é causada por um `TypeError` em `app-portal/components/redator/approve-overlay.tsx:250` — `entry.text.split("\n")` quebra quando `entry` é o sentinel `_is_audit_meta` anexado pelo patch P4 (`750ef6b`) em `app-redator/backend/services/claude_service.py:1031-1039`. O sentinel escapa ao frontend porque o endpoint `GET /api/projects/{id}` (`routers/projects.py:226-231`) não filtra — a Fase 3 atualizou 7 consumers backend mas não tocou nem no endpoint HTTP nem no frontend Next.js.

**Confiança:** causa-raiz determinada por análise estática cruzada (shape produzido pelo backend + shape consumido pelo frontend + ausência de filtro no endpoint + string exata "Ocorreu um erro inesperado" gravada em `app-portal/app/error.tsx:29`). Confirmação final por stack trace do console JS fica pendente de captura pelo operador (`evidencias/portal_console_error.txt` tem slot reservado).

**Próximos passos:** Bloco A sozinho precisa de fix em 2 pontos (endpoint backend + componente frontend). Patching é objeto de sessão separada, não deste relatório. Blocos B e C seguem como investigações independentes.

---

## 1. Bloco A — Regressão visual do overlay

### 1.1 Sintoma confirmado

**Relato do operador:** ao tentar visualizar/editar o overlay do projeto #355 (Itzhak Perlman — Chopin Nocturne em Dó# menor; `brand_slug === "reels-classics"`) no portal Next.js após o merge da Fase 3, aparece a tela "Ocorreu um erro inesperado". Backend retornou HTTP 200 em toda a cadeia de geração (Etapas 1-3 completas).

**Confirmação do sintoma por código:** a string literal "Ocorreu um erro inesperado" existe exatamente em `app-portal/app/error.tsx:29`:

```tsx
// app-portal/app/error.tsx:9-20
export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    Sentry.captureException(error)
    console.error("Global Error Boundary caught:", error)
  }, [error])
```

Isso é o Global Error Boundary do Next.js 15 — qualquer exceção que sobe até o boundary raiz renderiza esse componente. Logo, o relato do operador corresponde ao comportamento esperado do boundary quando a árvore abaixo dele lança.

**Captura direta do payload de #355 foi bloqueada** pela edge do Railway. Todas as URLs públicas devolvem HTTP 403 "Host not in allowlist" (sandbox não está no allowlist). Railway CLI não disponível. Token Sentry ausente no MCP. A captura foi substituída por reconstituição estática — detalhado em `evidencias/BLOQUEIO_CAPTURA.md` e `evidencias/projeto_355_shape_reconstituido.md`.

### 1.2 Fluxo de exibição mapeado

Cadeia completa do dado, do banco à tela:

```
DB: projects.overlay_json (JSON, lista heterogênea pós-Fase 3)
    │
    └─► GET /api/projects/{id}  (app-redator/backend/routers/projects.py:226-231)
        │                       ↑ NÃO FILTRA sentinel
        │
        └─► redatorApi.getProject (app-portal/lib/api/redator.ts:138)
            │
            └─► RedatorApproveOverlay.useEffect (approve-overlay.tsx:44-49)
                │    setOverlay(p.overlay_json || [])  ← NÃO FILTRA sentinel
                │
                └─► overlay.map((entry, i) => …)  (approve-overlay.tsx:216)
                    │
                    └─► entry.text.split("\n")     (approve-overlay.tsx:250)
                        ↑ CRASH quando entry é o sentinel
```

**Arquivos auditados nesta cadeia:**

| Papel | Arquivo | Linhas relevantes |
|---|---|---|
| Rota Next.js | `app-portal/app/(app)/redator/projeto/[id]/overlay/page.tsx` | 1-9 (só delega) |
| Componente UI | `app-portal/components/redator/approve-overlay.tsx` | 44-49 (carga), 216-321 (render) |
| Client HTTP | `app-portal/lib/api/redator.ts` | 5-51 (`Project`), 138 (`getProject`) |
| Handler backend | `app-redator/backend/routers/projects.py` | 226-231 |
| Schema Pydantic | `app-redator/backend/schemas.py` | 90-136 (`ProjectOut`) |

O componente renderiza a lista com `overlay.map(...)` e, **para cada item**, executa em `approve-overlay.tsx:250`:

```ts
const longest = Math.max(...(entry.text.split("\n").map((l: string) => l.length)), 0)
```

Esse `.split("\n")` é acessado quando `isRC === true` (linha 249), o que vale para todo projeto com `brand_slug === "reels-classics"` — inclusive o #355. Não há guard verificando a existência de `entry.text`.

**Interface TypeScript declarada** (`app-portal/lib/api/redator.ts:30`):

```ts
overlay_json:
  { timestamp: string; text: string; _is_cta?: boolean; end?: string; type?: string }[]
  | null
```

Declara `text: string` e `timestamp: string` como não-opcionais. Contrato quebrado em runtime pelo sentinel (que não tem nem um nem outro). TypeScript nominal não detecta — o tipo vem de `request<Project>(...)` sem validação.

Mapeamento detalhado do componente (todos os acessos de campo e guards) em `evidencias/portal_overlay_componente.md`.

### 1.3 Comparativo shape esperado vs retornado

Tabela condensada. Versão completa (com raiz + variantes de item) em `evidencias/portal_overlay_shape_diff.md`.

**Itens normais (gancho / corpo / cta)** — itens 0 a N-1 de `overlay_json`:

| Campo | FE espera (redator.ts:30) | BE retorna (claude_service.py:971-976) | Match |
|---|---|---|---|
| `text` | `string` (não-opcional) | `string` | sim |
| `timestamp` | `string` (não-opcional) | `"MM:SS"` | sim |
| `type` | `string?` | `"gancho" \| "corpo" \| "cta"` | sim |
| `_is_cta` | `boolean?` | `boolean` | sim |

Itens normais passam sem problema. Shape inalterado desde o pré-Fase 3.

**Item SENTINEL `_is_audit_meta`** — último item pós-Fase 3 (claude_service.py:1031-1039):

| Campo | FE espera | BE retorna no sentinel | **Crash no FE?** |
|---|---|---|---|
| `text` | sim, não-opcional | **AUSENTE** | **SIM — `.split("\n")` em `undefined` em `approve-overlay.tsx:250`** |
| `timestamp` | sim, não-opcional | **AUSENTE** | não (`<Input value={undefined}>` só vira uncontrolled) |
| `type` | opcional | ausente | não |
| `_is_cta` | opcional | ausente | não (`undefined === true` é `false`) |
| `_is_audit_meta` | não conhecido pelo FE | `true` | não (não é lido) |
| `fio_unico_identificado` | não conhecido | `string` | não |
| `pontes_planejadas` | não conhecido | `string[]` | não |
| `verificacoes` (+ subcampos) | não conhecido | `object` aninhado | não |

O sentinel é produzido pelo prompt v3.1 sempre que a resposta do LLM traz qualquer um dos campos `fio_unico_identificado`, `pontes_planejadas`, `verificacoes` (claude_service.py:1031-1032). O prompt v3.1 (`docs/rc_v3_migration/rc_overlay_prompt_v3_1.py:587-649`) produz sempre os três — logo o sentinel está **sempre** presente em overlays RC gerados pós-Fase 3.

**Campos que existiam pré-Fase 3 e continuam presentes:** todos. Nenhum campo foi removido. A regressão vem puramente da adição de um item heterogêneo ao array.

**Projeto NÃO-RC:** o branch `else` em `approve-overlay.tsx:258` acessa `entry.text.length` — em `undefined` isso não lança (retorna `undefined`), mas renderiza `"undefined/70"` no DOM. Feio, mas não crasha. Explica por que o crash só aparece em projetos RC como o #355.

### 1.4 Erro JS reproduzido (ou hipótese declarada)

**Status nesta sessão:** hipótese declarada, não confirmada por console JS (sandbox sem navegador; operador confirmou que tentará capturar em desktop nas próximas horas — slot reservado em `evidencias/portal_console_error.txt`).

**Hipótese declarada:**

```
TypeError: Cannot read properties of undefined (reading 'split')
    at RedatorApproveOverlay (app-portal/components/redator/approve-overlay.tsx:250)
    at Array.map (<anonymous>)
    at RedatorApproveOverlay (app-portal/components/redator/approve-overlay.tsx:216)
    …
```

**Linha exata:**

```ts
// app-portal/components/redator/approve-overlay.tsx:250
const longest = Math.max(...(entry.text.split("\n").map((l: string) => l.length)), 0)
```

**Reprodução determinística esperada:**

1. Projeto RC (`brand_slug === "reels-classics"`) gerado pós-`750ef6b` → banco contém sentinel.
2. `GET /api/projects/{id}` devolve `overlay_json` com o sentinel (sem filtro em `routers/projects.py:226-231`).
3. Frontend `setOverlay(p.overlay_json || [])` em `approve-overlay.tsx:47` armazena sem filtro.
4. `overlay.map(...)` em `approve-overlay.tsx:216` itera todos os itens, inclusive o sentinel.
5. `isRC === true` (definido em `approve-overlay.tsx:51` via `project.brand_slug === "reels-classics"`).
6. No render do sentinel, `entry.text` é `undefined` e `.split("\n")` lança `TypeError`.
7. React propaga até o `GlobalError` (`app-portal/app/error.tsx:9-20`) que grava no Sentry, imprime `"Global Error Boundary caught: …"` no console e renderiza "Ocorreu um erro inesperado" (linha 29 do mesmo arquivo).

**Confirmação empírica cabível** (a ser feita pelo operador):
- DevTools → Console → procurar pela linha `"Global Error Boundary caught:"` e inspecionar o `Error` logo após;
- **ou** abrir Sentry (`arias-conteudo-k2`, projeto do portal via `NEXT_PUBLIC_SENTRY_DSN` declarado em `dados-relevantes/sentry-access.md`) e filtrar por mensagem `"Cannot read properties of undefined (reading 'split')"` com breadcrumb `"/redator/projeto/355/overlay"`.

Três evidências estáticas independentes apontam para a mesma causa:
1. Shape do sentinel produzido (`claude_service.py:1031-1039`) não tem `text`.
2. Único caller que não filtra é o `get_project` + `approve-overlay.tsx` (ver 1.5).
3. Ponto único de crash em `approve-overlay.tsx:250` com path acionado somente quando `isRC === true`.

Se o operador capturar o stack e ele divergir desta hipótese, revisitar esta seção.

### 1.5 Comparativo pré-Fase 3 vs pós-Fase 3

**Baseline pré-Fase 3:** `f4f74f2` (primeiro parent do merge `90add64`).
**Range auditado:** `f4f74f2..90add64` (11 commits + merge).

**Prova empírica: frontend não foi tocado.**

```
$ git log --oneline f4f74f2..90add64 -- app-portal/
(saída vazia)
```

**Prova empírica: endpoint GET não foi tocado.**

```
$ git log --oneline f4f74f2..90add64 -- app-redator/backend/routers/projects.py
(saída vazia)
```

**Prova empírica: schemas Pydantic não foram tocados.**

```
$ git log --oneline f4f74f2..90add64 -- app-redator/backend/schemas.py
(saída vazia)
```

**Commit responsável pela introdução do sentinel:** `750ef6b` (P4 — overlay v3.1). `git blame` de `app-redator/backend/services/claude_service.py:1031-1041` aponta **todas** as linhas da introdução do sentinel para `750ef6ba (jmancini800 2026-04-22 01:07:36 -0300)`:

```
750ef6ba  1031  audit_fields = ("fio_unico_identificado", "pontes_planejadas", "verificacoes")
750ef6ba  1032  if any(field in response for field in audit_fields):
750ef6ba  1033      audit_item = {
750ef6ba  1034          "_is_audit_meta": True,
750ef6ba  1035          "fio_unico_identificado": response.get("fio_unico_identificado", ""),
750ef6ba  1036          "pontes_planejadas": response.get("pontes_planejadas", []),
750ef6ba  1037          "verificacoes": response.get("verificacoes", {}),
750ef6ba  1038      }
750ef6ba  1039      overlay_json.append(audit_item)
```

**Consumers e estado de filtro após Fase 3:**

| Consumer | Filtra? | Atualizado na Fase 3? |
|---|---|---|
| `_validate_overlay_rc` (`claude_service.py:1048-1051`) | sim | sim (P4) |
| `srt_service.generate_srt` (`srt_service.py:18-21`) | sim | sim (P4) |
| `translate_service.translate_overlay_json` (`translate_service.py:540`) | sim | sim (P4) |
| `translate_service.translate_one_claude` (`translate_service.py:853`) | sim | sim (P4) |
| `translate_service._chunk_and_translate` (`translate_service.py:960`) | sim | sim (P4) |
| `routers/generation.regenerate-overlay-entry` (`generation.py:187-190`) | sim | sim (`d8b6d27`) |
| `prompts/rc_automation_prompt.build_rc_automation_prompt` (`rc_automation_prompt.py:46-51`) | sim | sim (`fd36f92`) |
| **`routers/projects.get_project` (`projects.py:226-231`)** | **NÃO** | **não alterado** |
| **`app-portal/components/redator/approve-overlay.tsx`** | **NÃO** | **não alterado** |
| `app-editor/backend/app/routes/importar.py:253-256` | sim (acidental — filtro por presença de `text`) | não tocado |

**Conclusão do diff:** a Fase 3 mudou o shape de `overlay_json` em 7 consumers internos, mas deixou dois consumers externos (endpoint HTTP + frontend) sem atualização. O comentário em `claude_service.py:1029-1030` já anunciava o risco:

> "Shape preservada como lista (não dict) para compatibilidade com ~14 consumidores que iteram overlay_json. Consumidores que precisam filtrar devem checar _is_audit_meta."

O bypass explícito dos 6 itens do checklist pré-merge (documentado no corpo do merge `90add64` e em `NOTAS_EXECUCAO.md` entrada "BYPASS EXPLÍCITO" de 2026-04-22) pulou os passos de validação end-to-end que teriam exposto esse gap.

Diff completo e lista de commits da Fase 3 em `evidencias/diff_fase3_relevante.md`.

### 1.6 Causa-raiz consolidada

**Causa-raiz primária (mudança de shape):**

`app-redator/backend/services/claude_service.py:1031-1039` (commit `750ef6b` / P4) anexa, ao final de `overlay_json`, um item sentinel `{_is_audit_meta: True, fio_unico_identificado, pontes_planejadas, verificacoes}` que **não tem** `text` nem `timestamp`. Esse sentinel é persistido em `projects.overlay_json` e flui para o frontend sem ser filtrado.

**Causa-raiz secundária (filtro ausente no ponto de saída):**

`app-redator/backend/routers/projects.py:226-231` (`get_project`) devolve `overlay_json` cru via `ProjectOut`, sem filtrar o sentinel — ao contrário de todos os outros consumers backend atualizados pela Fase 3.

**Ponto de crash (consequência):**

`app-portal/components/redator/approve-overlay.tsx:250`:

```ts
const longest = Math.max(...(entry.text.split("\n").map((l: string) => l.length)), 0)
```

`undefined.split(...)` lança `TypeError` → `GlobalError` boundary (`app-portal/app/error.tsx:9-29`) renderiza "Ocorreu um erro inesperado" e envia ao Sentry.

**Confiança:** hipótese declarada, suportada por três evidências estáticas independentes e ainda pendente de confirmação empírica por stack trace do console (slot reservado em `evidencias/portal_console_error.txt`). A hipótese é determinística: para qualquer projeto com `brand_slug === "reels-classics"` cujo overlay foi gerado pós-`750ef6b`, o crash deve ocorrer no primeiro render.

**Cascata para o app-editor** (investigada incidentalmente em A.5):

| Local | Risco | Evidência |
|---|---|---|
| `app-editor/backend/app/routes/importar.py:253-256` | **absorvido** por acidente feliz | O filtro `if s.get("text", "").strip() or s.get("_is_cta")` descarta o sentinel (que não tem nenhum dos dois). O editor não quebra. |
| Outros consumers potenciais dentro de `app-editor` | não audit-ado exaustivamente | Deixado como ambiguidade (seção 4 do relatório). `grep -rn overlay_json` em `app-editor/backend/` retornou apenas o `importar.py`. |

**Violação dos princípios editoriais:**

- **Princípio 1** ("Operador nunca vê JSON cru"): cumprido no caminho feliz; no caminho de erro, o Global Error Boundary substitui a lista visual pela tela de erro — o operador não vê JSON, mas fica sem UI funcional. A própria introdução do sentinel como item heterogêneo no array de `overlay_json` empurra o controle visual para camadas externas ao editor redacional, o que é a contraparte sistêmica da violação.
- **Princípio 2** ("Nunca cortar silenciosamente"): não é violação direta do Bloco A, mas o bypass do checklist de smoke testing (ver 1.7) pode ter mascarado violações latentes — a investigar no Bloco B.
- **Princípio 3** ("Editor não faz análise de caracteres"): violação residual observada em `approve-overlay.tsx:250-254` — o próprio componente de edição do portal faz análise de chars (`longest > 33`), o que é análise de caracteres no cliente de redação e viola o princípio. Anotado para Bloco B.

### 1.7 Por que escapou dos smoke tests

**Lacuna de cobertura identificada:** a Fase 3 não executou — e o merge commit `90add64` registra isso explicitamente — um teste end-to-end que abrisse a UI de overlay RC após gerar um overlay com o prompt v3.1. Os testes executados foram todos unitários/backend, em caminhos que já filtram o sentinel (`srt_service`, `translate_service`, etc.).

**Evidência documental** — o corpo do merge `90add64` diz:

> "Bypass explícito dos 6 itens do checklist 'Pending before merge' autorizado pelo operador — ver docs/rc_v3_migration/NOTAS_EXECUCAO.md entrada 'BYPASS EXPLÍCITO' de 2026-04-22. Risco assumido."

O commit `c17559a` (último da Fase 3 antes do merge) é dedicado a documentar esse bypass.

**Qual teste deveria ter pego:** um smoke de pipeline completo que gerasse overlay RC v3.1 num projeto-teste e abrisse a rota `/redator/projeto/{id}/overlay` no portal. Não precisaria ser automatizado — bastaria execução manual. A ausência dessa verificação não está implícita: ela é parte do checklist dos 6 itens pendentes que foi explicitamente bypassado.

**Agravantes:**

1. **TypeScript nominal mascara a divergência em tempo de compilação.** A interface `Project` declara `overlay_json` como `{ timestamp: string; text: string; ... }[]` (`redator.ts:30`), mas `request<Project>(...)` assume o shape sem validação em runtime. Sem validação de borda (Zod, io-ts ou equivalente), o tipo existe só no papel.
2. **Comentário de "aviso" no próprio código-fonte** em `claude_service.py:1029-1030` diz explicitamente "Consumidores que precisam filtrar devem checar _is_audit_meta" — mas nenhum commit da Fase 3 adicionou esse filtro no endpoint `get_project` nem no portal. O aviso não foi traduzido em ação.
3. **Não há teste de shape de API.** Nenhum teste bateu na rota `GET /api/projects/{id}` assertando que todo item de `overlay_json` tem `text` e `timestamp` (ou que o sentinel está segregado em outro campo).

**Gap estrutural (sugestão para o relatório do Bloco C):** a Fase 3 tratou `overlay_json` como estrutura interna do pipeline e subestimou que ela também é API pública consumida pelo portal e (via `importar.py`) pelo editor.

### 1.8 Dependências e risco atual

**Risco atual em produção:**

- **Pipeline RC bloqueado na Etapa 4 (aprovação visual do overlay)**: operadores não conseguem visualizar nem editar overlays de nenhum projeto RC gerado após `90add64` (2026-04-22 04:55 UTC). O crash é determinístico — todo projeto RC novo que atinja a tela `/redator/projeto/{id}/overlay` quebra no primeiro render.
- **Dados do banco já contaminados pelo sentinel**: todos os projetos RC gerados após `750ef6b` têm `projects.overlay_json` com o item `_is_audit_meta` persistido. Mesmo um fix só no frontend precisa prever essa contaminação existente (não basta gerar novos — precisa lidar com os existentes).
- **Projetos RC que foram `approve`d antes do crash**: se algum projeto já passou pelo `handleApprove` com o sentinel no array, o sentinel foi reenviado ao backend via `approveOverlay` (app-portal/lib/api/redator.ts → backend) e persistido. Anotar para verificação.

**Dependências que consomem o mesmo payload:**

| Consumidor | Status | Ação necessária |
|---|---|---|
| Portal Next.js (`approve-overlay.tsx`) | **QUEBRADO** | filtrar sentinel no useEffect (linha 47) OU no endpoint |
| Endpoint `GET /api/projects/{id}` (`routers/projects.py`) | passa sentinel adiante | candidato a filtrar antes de serializar — propaga fix para qualquer outro consumer HTTP |
| Endpoint `PUT /api/projects/{id}` (`routers/projects.py:234-245`) | aceita qualquer lista em `overlay_json` | risco latente de re-persistência do sentinel pelo `handleApprove`; audit-ar se necessário |
| `app-editor/backend/app/routes/importar.py` | absorve por acidente (linha 253-256) | baixo risco; documentar dependência do filtro acidental para não quebrar em refactor futuro |
| Qualquer `app-portal` que leia `overlay_json` (ex: pages de review, export-page.tsx, new-project.tsx) | `grep` de A.2 encontrou 4 arquivos além do `approve-overlay.tsx` | audit-ar cada um — não feito nesta sessão |

**Cascata ao Editor (conclusiva para A.5):**

Apesar do `importar.py:253-256` absorver o sentinel por acidente, **o risco é estrutural**: o filtro `if s.get("text", "").strip() or s.get("_is_cta")` existe para outro fim (descartar legendas sem texto) e cobre o sentinel só por coincidência do shape. Qualquer refactor que mude esse filtro pode reabrir o problema no editor.

**Bloqueador operacional:** nenhum novo Reel Classics pode ser produzido pelo pipeline até que a regressão seja corrigida. Este é o impacto mais urgente do Bloco A.

**Recomendações (apenas para referência do Bloco A — patching fora do escopo desta sessão):**

1. Fix mínimo imediato: filtrar `_is_audit_meta` em `approve-overlay.tsx:47` (`setOverlay((p.overlay_json || []).filter(e => !e._is_audit_meta))`).
2. Fix defensivo no endpoint: aplicar o mesmo filtro em `get_project` antes de devolver (reduz risco para todos os consumers HTTP, não só o portal).
3. Fix estrutural (mais profundo): mover `fio_unico_identificado`/`pontes_planejadas`/`verificacoes` de dentro do array `overlay_json` para um campo novo (`overlay_audit_meta`) no modelo `Project` e no schema `ProjectOut`. Evita a dependência de convenção "item mágico no array" e permite que o tipo TS do item volte a ser homogêneo. Sugerir como parte do Bloco C (cleanup estrutural da Fase 3).

Nenhuma dessas recomendações é executada nesta sessão; ficam para decisão do operador e sessão de patching subsequente.

---

## 2. Bloco B — [a investigar em PROMPT 5B]

Escopo (segundo o plano consolidado):
- Truncamentos silenciosos residuais em qualquer camada (log `[RC LineBreak]` já observado fora do redator, limites hardcoded ainda ativos, `_enforce_line_breaks_rc` aplicado em pontos indevidos, etc.).
- Violação do Princípio 2 (nunca cortar silenciosamente).
- Violação do Princípio 3 (editor não faz análise de chars).

Não investigado nesta sessão.

Anotações descobertas incidentalmente nesta sessão que podem interessar ao Bloco B:
- `app-portal/components/redator/approve-overlay.tsx:251` ainda exibe label `{longest}/33 lin` com limiar de **33 caracteres**, embora a Fase 3 tenha atualizado o limite backend para **38** em 5 pontos (P1 `105491f`). Inconsistência de limiar entre UI e backend — potencial indicador de análise de chars residual no editor/portal que deveria viver só em redator.
- Não encontrei nesta sessão um grep amplo por `[RC LineBreak]` nem por `max_linhas` / `38` / `42` em app-editor — deixado para PROMPT 5B.

---

## 3. Bloco C — [a investigar em PROMPT 5C]

Escopo: sanity check da Fase 3 — quais dos 6 patches foram aplicados parcialmente, quais escaparam de smoke testing, se há contradição entre `RELATORIO_EXECUCAO.md` e o código real.

Não investigado nesta sessão.

Anotação incidental relevante:
- O merge commit `90add64` assume explicitamente o bypass dos 6 itens do checklist "Pending before merge" (ver `docs/rc_v3_migration/NOTAS_EXECUCAO.md` entrada "BYPASS EXPLÍCITO" de 2026-04-22). Registrado aqui para o Bloco C.

---

## 4. Ambiguidades e lacunas desta sessão

1. **Payload real do #355 não foi capturado.** Railway edge bloqueia requisições do sandbox com HTTP 403 "Host not in allowlist" em todos os hosts de produção (`ia-production-cf4a`, `app-production-870c`, `portal-production-4304`). Não há Railway CLI disponível. Não há token Sentry no MCP. Captura foi substituída por reconstituição estática a partir do código-fonte — ver `evidencias/BLOQUEIO_CAPTURA.md` e `evidencias/projeto_355_shape_reconstituido.md`. A reconstituição é determinística sobre o shape (o que basta para o diagnóstico), mas NÃO confirma empiricamente que o #355 específico recebeu o sentinel.
2. **Stack trace JS definitivo não foi capturado.** Slot reservado em `evidencias/portal_console_error.txt` com instruções para o operador. A hipótese declarada é forte (`TypeError: Cannot read properties of undefined (reading 'split')` na linha 250) e vem de análise estática de 3 fontes cruzadas, mas permanece tecnicamente como hipótese até o console confirmar.
3. **`app-editor` só foi auditado nos pontos diretos de consumo de `overlay_json`.** Encontrei que o filtro existente em `app-editor/backend/app/routes/importar.py:253-256` absorve o sentinel por acidente feliz (filtra itens sem texto). Não fiz grep exaustivo por outros possíveis consumidores dentro do editor — risco latente, não confirmado.

---

## 5. Anexos

Todos em `docs/rc_v3_migration/evidencias/`:

- `BLOQUEIO_CAPTURA.md` — tentativas de captura de payload + decisão de fallback
- `projeto_355_shape_reconstituido.md` — shape do payload reconstituído a partir do código
- `portal_overlay_componente.md` — mapa dos componentes frontend envolvidos
- `portal_overlay_shape_diff.md` — tabela comparativa FE espera vs BE retorna
- `portal_console_error.txt` — slot para stack trace do operador + hipótese declarada
- `diff_fase3_relevante.md` — diffs e blame dos commits da Fase 3 que causaram a regressão
