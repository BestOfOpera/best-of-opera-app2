# Mapeamento do frontend — fluxo de exibição do overlay RC

**Fonte canônica (pós-Fase 3):** branch `main` @ `90add64`
**Sessão:** PROMPT 5A — Bloco A

## 1. Árvore de arquivos envolvidos

```
app-portal/
├── app/(app)/redator/projeto/[id]/overlay/
│   └── page.tsx            (9 linhas — wrapper Next 15, só delega ao componente)
├── components/redator/
│   └── approve-overlay.tsx (365 linhas — TODA a UI editável do overlay)
└── lib/api/
    └── redator.ts          (248 linhas — types + client HTTP)
```

`approve-overlay.tsx` é o único componente que renderiza a lista editável de
legendas do overlay para o operador. Não há outro componente de leitura-apenas
separado: a UI de exibição e a UI de edição são o mesmo componente.

## 2. Rota Next.js

`app-portal/app/(app)/redator/projeto/[id]/overlay/page.tsx`:

```tsx
"use client"

import { use } from "react"
import { RedatorApproveOverlay } from "@/components/redator/approve-overlay"

export default function OverlayPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  return <RedatorApproveOverlay projectId={Number(id)} />
}
```

Sem lógica. Só repassa `projectId` para o componente.

## 3. Carregamento do overlay

`approve-overlay.tsx:44-49`:

```tsx
useEffect(() => {
  redatorApi.getProject(projectId).then((p) => {
    setProject(p)
    setOverlay(p.overlay_json || [])   // ← sem filtro de _is_audit_meta
  }).finally(() => setLoading(false))
}, [projectId])
```

Cliente HTTP (`app-portal/lib/api/redator.ts:138`):

```ts
getProject: (id: number) => request<Project>(`${BASE()}/projects/${id}`),
```

Ou seja: o frontend carrega `overlay_json` cru do endpoint
`GET /api/projects/{id}` e passa direto para `setOverlay`. Em nenhum ponto do
caminho (useEffect, api client, nem no estado inicial) há filtro de entrada do
sentinel `_is_audit_meta`.

## 4. Tipo TypeScript declarado para `overlay_json`

`app-portal/lib/api/redator.ts:5-51` (relevante em 30):

```ts
export interface Project {
  // ...
  overlay_json:
    { timestamp: string; text: string; _is_cta?: boolean; end?: string; type?: string }[]
    | null
  // ...
}
```

**O tipo declara que TODO item tem `timestamp: string` e `text: string` (não
opcionais).** O sentinel v3.1 retornado pelo backend viola esse contrato: tem
apenas `_is_audit_meta`, `fio_unico_identificado`, `pontes_planejadas`,
`verificacoes`. TypeScript nominal não detecta isso em runtime (é `any` depois
do `JSON.parse`), mas o código trata os campos como não-opcionais e quebra.

## 5. Pontos onde `entry.text` / `entry.timestamp` são acessados sem guard

Iteração principal (`approve-overlay.tsx:216-321`):

```tsx
{overlay.map((entry, i) => {
  const isCta = entry._is_cta === true       // linha 217 — safe (undefined = false)
  return (
    // ...
    <Input value={entry.timestamp} ... />    // 238 — uncontrolled se undefined, mas não crasha
    <Textarea value={entry.text} ... />      // 243 — idem
    {(() => {
      if (isRC) {
        const longest = Math.max(
          ...(entry.text.split("\n").map((l: string) => l.length)),   // ← 250
          0
        )
        const over = longest > 33
        return <span>...{longest}/33 lin</span>
      }
      const over = entry.text.length > 70    // 258 — .length em undefined NÃO crasha,
                                             //       mas dá NaN > 70 = false.
      return <span>...{entry.text.length}/70</span>  // 261 — "undefined/70" no DOM
    })()}
```

### Ponto de crash definitivo: linha 250

```ts
const longest = Math.max(...(entry.text.split("\n").map((l: string) => l.length)), 0)
```

Para o projeto #355, que é Reels Classics (`brand_slug === "reels-classics"` → `isRC === true`
via `approve-overlay.tsx:51`), o branch `if (isRC)` é sempre executado. Quando
`entry` é o sentinel `_is_audit_meta`, `entry.text` é `undefined`.

`undefined.split(...)` lança `TypeError: Cannot read properties of undefined (reading 'split')`.

Em Next.js 15 client component, o erro dispara o Error Boundary que renderiza o
fallback `app-portal/app/(app)/error.tsx` (ou `app/error.tsx`) — que exibe a
mensagem **"Ocorreu um erro inesperado"** reportada pelo operador.

## 6. Outros pontos onde o sentinel passa sem filtro

- **`updateEntry` (linha 116-118):** preserva o sentinel inadvertidamente ao
  editar qualquer legenda (spread mantém todos os campos).
- **`handleApprove` (linha 146-165):** envia `overlay` de volta via
  `redatorApi.approveOverlay(projectId, overlay)` — o sentinel é reenviado ao
  backend e persistido de novo no banco.
- **`addEntryAt` (linha 122-135):** `parseTimestamp(novo[index].timestamp || "00:00")`
  — safe porque tem fallback `"00:00"`, mas se `index === overlay.length - 1` e
  o último item é o sentinel, o tempo de referência fica zerado.

Esses três pontos não causam crash visível, mas são efeitos colaterais que
merecem remediação junto com o fix principal.

## 7. Confirmação de ausência de filtro no caminho feliz

```
Backend  /api/projects/{id} GET
         └─ routers/projects.py:226-231  (NÃO filtra _is_audit_meta)
              ↓
Frontend redatorApi.getProject
         └─ lib/api/redator.ts:138 (GET + JSON.parse)
              ↓
         setOverlay(p.overlay_json || [])
         └─ approve-overlay.tsx:47 (NÃO filtra)
              ↓
         overlay.map((entry, i) => ...)
         └─ approve-overlay.tsx:216 (itera TUDO, sentinel incluso)
              ↓
         entry.text.split("\n")
         └─ approve-overlay.tsx:250 ← CRASH quando entry é sentinel
```

Nenhum nó da cadeia filtra o sentinel. A Fase 3 atualizou 7+ consumers backend,
mas não tocou no frontend nem no endpoint GET.
