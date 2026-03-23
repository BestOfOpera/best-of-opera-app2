# SPEC-005a — Guard de Perfil (Brand Selector)

**Status:** CONCLUÍDO
**PRD de origem:** `docs/PRD-005-diagnostico-erros-plataforma.md` (problema #6)
**Data:** 23/03/2026

---

## Contexto

O dropdown de perfil troca de marca imediatamente ao clicar, sem confirmação e sem persistência. Isso causa dois problemas:
1. A lista de edições na fila reseta para o novo perfil sem aviso — o usuário perde o contexto visual da edição em andamento
2. Ao recarregar a página, o perfil volta para o primeiro da lista (estado não salvo)

A solução é: persistir a seleção em `localStorage` e adicionar um diálogo de confirmação quando a troca acontece enquanto o usuário está em uma página de edição ativa (`/editor/edicoes/[id]`).

**Arquivos a modificar:** 2 (ambos frontend, sem tocar backend ou banco)

---

## Tarefa 1 — `brand-context.tsx`: adicionar persistência em localStorage

**Arquivo:** `app-portal/lib/brand-context.tsx`

**Antes:**
```typescript
export function BrandProvider({ children }: { children: ReactNode }) {
  const [selectedBrand, setSelectedBrand] = useState<Perfil | null>(null)

  return (
    <BrandContext.Provider value={{ selectedBrand, setSelectedBrand }}>
      {children}
    </BrandContext.Provider>
  )
}
```

**Depois:**
```typescript
const STORAGE_KEY = "selectedBrandId"

export function BrandProvider({ children }: { children: ReactNode }) {
  const [selectedBrand, setSelectedBrandState] = useState<Perfil | null>(null)
  const [savedBrandId, setSavedBrandId] = useState<string | null>(null)

  // Lê o id salvo do localStorage na montagem (client-side only)
  useEffect(() => {
    const id = localStorage.getItem(STORAGE_KEY)
    setSavedBrandId(id)
  }, [])

  const setSelectedBrand = useCallback((brand: Perfil | null) => {
    setSelectedBrandState(brand)
    if (brand) {
      localStorage.setItem(STORAGE_KEY, String(brand.id))
    } else {
      localStorage.removeItem(STORAGE_KEY)
    }
  }, [])

  return (
    <BrandContext.Provider value={{ selectedBrand, setSelectedBrand, savedBrandId }}>
      {children}
    </BrandContext.Provider>
  )
}
```

Adicionar `savedBrandId` na interface `BrandContextType` e no `createContext`:
```typescript
interface BrandContextType {
  selectedBrand: Perfil | null
  setSelectedBrand: (brand: Perfil | null) => void
  savedBrandId: string | null
}

const BrandContext = createContext<BrandContextType>({
  selectedBrand: null,
  setSelectedBrand: () => {},
  savedBrandId: null,
})
```

Adicionar imports necessários: `useCallback`, `useEffect` (já podem estar importados — verificar).

**Critério de feito:** ao selecionar um perfil, `localStorage.getItem("selectedBrandId")` retorna o `id` correto. Após recarregar a página, `savedBrandId` contém o id salvo (usado na Tarefa 2 para pré-selecionar).

---

## Tarefa 2 — `brand-selector.tsx`: usar savedBrandId na seleção inicial + adicionar guard

**Arquivo:** `app-portal/components/brand-selector.tsx`

### 2a. Pré-selecionar perfil salvo no carregamento inicial

**Localizar** o bloco dentro de `fetchData()` (linha ~24):
```typescript
if (activeBrands.length > 0 && !selected) {
  setSelected(activeBrands[0])
}
```

**Substituir por:**
```typescript
if (activeBrands.length > 0 && !selected) {
  const saved = activeBrands.find(b => String(b.id) === savedBrandId)
  setSelected(saved ?? activeBrands[0])
}
```

Importar `savedBrandId` do contexto:
```typescript
const { selectedBrand: selected, setSelectedBrand: setSelected, savedBrandId } = useBrand()
```

### 2b. Adicionar guard de confirmação ao trocar de perfil

Adicionar `usePathname` do Next.js e estado de confirmação:

```typescript
import { usePathname } from "next/navigation"
// ...
const pathname = usePathname()
const [pendingBrand, setPendingBrand] = useState<Perfil | null>(null)
```

Criar função `handleSelect` que substitui o `onClick` direto:
```typescript
const handleSelect = (brand: Perfil) => {
  if (brand.id === selected?.id) return
  // Só pede confirmação se estiver em uma página de edição ativa
  const isEditingPage = /\/editor\/edicoes\/\d+/.test(pathname)
  if (isEditingPage) {
    setPendingBrand(brand)
  } else {
    setSelected(brand)
  }
}
```

Substituir o `onClick` no `DropdownMenuItem`:
```typescript
// Antes:
onClick={() => setSelected(brand)}

// Depois:
onClick={() => handleSelect(brand)}
```

Adicionar diálogo de confirmação ao final do JSX retornado (antes do `</>`  ou dentro do fragment):
```tsx
{pendingBrand && (
  <Dialog open={!!pendingBrand} onOpenChange={() => setPendingBrand(null)}>
    <DialogContent className="max-w-sm">
      <DialogHeader>
        <DialogTitle>Trocar de perfil?</DialogTitle>
        <DialogDescription>
          Você está editando um vídeo. Trocar para <strong>{pendingBrand.nome}</strong> vai
          atualizar a lista de edições. A edição atual continua salva e pode ser acessada
          voltando ao perfil correto.
        </DialogDescription>
      </DialogHeader>
      <DialogFooter>
        <Button variant="outline" onClick={() => setPendingBrand(null)}>Cancelar</Button>
        <Button onClick={() => { setSelected(pendingBrand); setPendingBrand(null) }}>
          Confirmar troca
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
)}
```

Importar os componentes de Dialog necessários (verificar se já estão importados no arquivo; se não, adicionar):
```typescript
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
```

**Critério de feito:**
- Ao acessar `/editor/edicoes/123` e tentar trocar de perfil, aparece diálogo de confirmação
- Em qualquer outra página, a troca é imediata (sem diálogo)
- Ao recarregar a página, o perfil salvo é pré-selecionado automaticamente

---

## Ordem de execução

1. Tarefa 1 — `brand-context.tsx` (base da persistência)
2. Tarefa 2a — pré-seleção no `brand-selector.tsx`
3. Tarefa 2b — guard de confirmação no `brand-selector.tsx`

---

## Verificação pós-execução

- [ ] Selecionar "Reels Classics" → recarregar página → perfil deve continuar "Reels Classics"
- [ ] Abrir uma edição (entrar em `/editor/edicoes/[id]`) → tentar trocar de perfil → diálogo de confirmação deve aparecer
- [ ] Confirmar a troca → lista de edições atualiza para o novo perfil
- [ ] Cancelar a troca → perfil não muda, continua na edição
- [ ] Na página principal (fora de uma edição) → trocar de perfil → sem diálogo, troca imediata
