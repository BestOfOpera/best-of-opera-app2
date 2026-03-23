"use client"

import { useState, useEffect, useCallback } from "react"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"
import { ChevronDown, Check, Loader2, Globe, RefreshCw } from "lucide-react"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { editorApi, type Perfil } from "@/lib/api/editor"
import { useBrand } from "@/lib/brand-context"

export function BrandSelector() {
  const [brands, setBrands] = useState<Perfil[]>([])
  const { selectedBrand: selected, setSelectedBrand: setSelected, savedBrandId } = useBrand()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [retryAttempted, setRetryAttempted] = useState(false)
  const [pendingBrand, setPendingBrand] = useState<Perfil | null>(null)
  const pathname = usePathname()

  const fetchData = useCallback(() => {
    setLoading(true)
    setError(null)

    editorApi.listarPerfis().then(data => {
      const activeBrands = data.filter(b => b.ativo)
      setBrands(activeBrands)
      if (activeBrands.length > 0 && !selected) {
        const saved = activeBrands.find(b => String(b.id) === savedBrandId)
        setSelected(saved ?? activeBrands[0])
      }
      setError(null)
    }).catch(err => {
      console.error("Erro ao puxar Marcas/Perfis", err)
      setError("Falha ao carregar marcas")
    }).finally(() => {
      setLoading(false)
    })
  }, [selected, setSelected, savedBrandId])

  // Busca inicial e ao mudar seleção (mantendo lógica original)
  useEffect(() => {
    fetchData()
  }, [fetchData])

  // Retry automático silencioso após 5s na primeira falha
  useEffect(() => {
    let timer: NodeJS.Timeout
    if (error && !retryAttempted) {
      timer = setTimeout(() => {
        setRetryAttempted(true)
        fetchData()
      }, 5000)
    }
    return () => {
      if (timer) clearTimeout(timer)
    }
  }, [error, retryAttempted, fetchData])

  const handleManualRetry = () => {
    setRetryAttempted(true)
    fetchData()
  }

  const handleSelect = (brand: Perfil) => {
    if (brand.id === selected?.id) return
    const isEditingPage = /\/editor\/edicoes\/\d+/.test(pathname)
    if (isEditingPage) {
      setPendingBrand(brand)
    } else {
      setSelected(brand)
    }
  }

  if (loading && !error) {
    return (
      <div className="flex h-8 w-32 items-center justify-center rounded-md border border-border bg-card">
        <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (error) {
    return (
      <button
        onClick={handleManualRetry}
        className="flex h-8 w-32 items-center justify-center gap-2 rounded-md border border-destructive/20 bg-destructive/5 px-2 transition-all hover:bg-destructive/10"
      >
        <RefreshCw className="h-3 w-3 text-destructive" />
        <span className="text-xs font-medium text-destructive">Tentar novamente</span>
      </button>
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
    <>
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
              onClick={() => handleSelect(brand)}
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

      <Dialog open={!!pendingBrand} onOpenChange={() => setPendingBrand(null)}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Trocar de perfil?</DialogTitle>
            <DialogDescription>
              Você está editando um vídeo. Trocar para <strong>{pendingBrand?.nome}</strong> vai
              atualizar a lista de edições. A edição atual continua salva e pode ser acessada
              voltando ao perfil correto.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setPendingBrand(null)}>Cancelar</Button>
            <Button onClick={() => { setSelected(pendingBrand!); setPendingBrand(null) }}>
              Confirmar troca
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
