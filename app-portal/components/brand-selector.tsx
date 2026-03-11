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
        <button className="flex items-center gap-2.5 rounded-full border border-border/60 bg-card py-1.5 pl-1.5 pr-3 transition-all hover:bg-muted/80 hover:shadow-sm">
          <div 
            className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[10px] font-bold text-white shadow-inner"
            style={{ backgroundColor: selected.cor_primaria || "#3b82f6" }}
          >
            {selected.sigla}
          </div>
          <span className="text-sm font-medium text-foreground">{selected.nome}</span>
          <ChevronDown className="ml-1 h-3.5 w-3.5 text-muted-foreground" />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56 p-1.5 rounded-xl">
        {brands.map((brand) => (
          <DropdownMenuItem 
            key={brand.id} 
            onClick={() => setSelected(brand)} 
            className={cn("flex items-center gap-3 cursor-pointer rounded-lg px-2.5 py-2 transition-colors", selected.id === brand.id && "bg-muted font-medium")}
          >
            <div 
              className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[10px] font-bold text-white shadow-inner"
              style={{ backgroundColor: brand.cor_primaria || "#3b82f6" }}
            >
              {brand.sigla}
            </div>
            <span className="flex-1 text-sm">{brand.nome}</span>
            {selected.id === brand.id && <Check className="h-4 w-4 text-foreground opacity-60" />}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
