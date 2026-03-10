"use client"

import { useState, useEffect } from "react"
import { cn } from "@/lib/utils"
import { ChevronDown, Check, Loader2, Globe } from "lucide-react"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import { editorApi, type Perfil } from "@/lib/api/editor"

export function BrandSelector() {
  const [brands, setBrands] = useState<Perfil[]>([])
  const [selected, setSelected] = useState<Perfil | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    editorApi.listarPerfis().then(data => {
      const activeBrands = data.filter(b => b.ativo)
      setBrands(activeBrands)
      if (activeBrands.length > 0) {
        setSelected(activeBrands[0])
      }
    }).catch(err => {
      console.error("Erro ao puxar Marcas/Perfis", err)
    }).finally(() => {
      setLoading(false)
    })
  }, [])

  if (loading) {
    return (
      <div className="flex h-8 w-32 items-center justify-center rounded-md border border-border bg-card">
        <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (brands.length === 0 || !selected) {
    return (
      <div className="flex h-8 w-32 items-center justify-center gap-1 rounded-md border border-border bg-card px-2">
        <Globe className="h-3 w-3 text-muted-foreground" />
        <span className="text-xs text-muted-foreground">0 Marcas</span>
      </div>
    )
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button className="flex items-center gap-2 rounded-md border border-border bg-card px-3 py-1.5 transition-colors hover:bg-muted/50">
          <span className="flex h-5 w-5 items-center justify-center rounded bg-primary/10 text-[9px] font-bold text-primary">{selected.sigla}</span>
          <span className="text-sm font-medium text-foreground">{selected.nome}</span>
          <ChevronDown className="ml-1 h-3 w-3 text-muted-foreground" />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-52">
        {brands.map((brand) => (
          <DropdownMenuItem key={brand.id} onClick={() => setSelected(brand)} className={cn("flex items-center gap-2.5 cursor-pointer", selected.id === brand.id && "bg-muted")}>
            <span className="flex h-5 w-5 items-center justify-center rounded bg-primary/10 text-[9px] font-bold text-primary">{brand.sigla}</span>
            <span className="flex-1 text-sm">{brand.nome}</span>
            {selected.id === brand.id && <Check className="h-3.5 w-3.5 text-primary" />}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
