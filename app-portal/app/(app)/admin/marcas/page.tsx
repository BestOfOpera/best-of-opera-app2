"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { editorApi, type Perfil } from "@/lib/api/editor"
import { RequireAdmin } from "@/components/auth/require-admin"
import { toast } from "sonner"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Loader2, Plus, Settings, CopyPlus, Globe, HardDrive } from "lucide-react"
import { cn } from "@/lib/utils"

export default function MarcasPage() {
  return (
    <RequireAdmin>
      <MarcasContent />
    </RequireAdmin>
  )
}

function MarcasContent() {
  const [perfis, setPerfis] = useState<Perfil[]>([])
  const [loading, setLoading] = useState(true)
  const [duplicandoId, setDuplicandoId] = useState<number | null>(null)

  const load = async () => {
    try {
      const data = await editorApi.listarPerfis()
      setPerfis(data)
    } catch (err: any) {
      toast.error("Erro ao carregar marcas: " + err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const handleDuplicar = async (id: number) => {
    setDuplicandoId(id)
    try {
      const novo = await editorApi.duplicarPerfil(id)
      toast.success(`Marca duplicada: ${novo.nome}`)
      load()
    } catch (err: any) {
      toast.error("Erro ao duplicar: " + err.message)
    } finally {
      setDuplicandoId(null)
    }
  }

  if (loading) {
    return (
      <div className="flex h-48 items-center justify-center">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Marcas / Perfis</h1>
          <p className="text-sm text-muted-foreground mt-1">{perfis.length} marca{perfis.length !== 1 ? "s" : ""} configurada{perfis.length !== 1 ? "s" : ""}</p>
        </div>
        <Button asChild>
          <Link href="/admin/marcas/nova">
            <Plus className="mr-2 h-4 w-4" />
            Nova Marca
          </Link>
        </Button>
      </div>

      {perfis.length === 0 ? (
        <Card className="border-dashed border-2 bg-muted/30">
          <CardContent className="flex flex-col items-center justify-center py-16 gap-3 text-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-muted">
              <Globe className="h-8 w-8 text-muted-foreground/60" />
            </div>
            <h3 className="text-lg font-semibold mt-2">Nenhuma marca encontrada</h3>
            <p className="text-muted-foreground text-sm max-w-sm mb-2">Você ainda não tem nenhuma marca configurada. Crie a sua primeira marca para começar a gerar vídeos.</p>
            <Button asChild size="sm">
              <Link href="/admin/marcas/nova">
                <Plus className="mr-2 h-4 w-4" />
                Criar primeira marca
              </Link>
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {perfis.map((perfil) => (
            <Card key={perfil.id} className="group relative flex flex-col overflow-hidden transition-all hover:shadow-md">
              {/* Faixa lateral colorida */}
              <div 
                className="absolute left-0 top-0 bottom-0 w-1.5 transition-opacity group-hover:opacity-100 opacity-90"
                style={{ backgroundColor: perfil.cor_primaria || "#3b82f6" }}
              />
              <CardContent className="flex flex-1 flex-col gap-3 p-5 pl-6">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-3">
                    <span
                      className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg text-sm font-bold text-white shadow-sm ring-1 ring-black/5"
                      style={{ backgroundColor: perfil.cor_primaria || "#3b82f6" }}
                    >
                      {perfil.sigla}
                    </span>
                    <div>
                      <p className="font-semibold text-foreground leading-tight text-base">{perfil.nome}</p>
                      <p className="text-xs text-muted-foreground mt-0.5">{perfil.slug}</p>
                    </div>
                  </div>
                  <Badge 
                    variant={perfil.ativo ? "default" : "secondary"} 
                    className={cn(
                      "shrink-0 text-[10px] uppercase font-bold tracking-wider",
                      perfil.ativo ? "bg-emerald-500/15 text-emerald-700 hover:bg-emerald-500/25 border-0" : "bg-muted text-muted-foreground"
                    )}
                  >
                    {perfil.ativo ? "Ativo" : "Inativo"}
                  </Badge>
                </div>

                <div className="flex flex-wrap gap-1.5 mt-2">
                  {(perfil.idiomas_alvo || "").split(",").filter(Boolean).map((lang) => (
                    <span key={lang} className="rounded-md bg-secondary/50 px-2 py-0.5 text-[10px] text-secondary-foreground font-mono uppercase border border-border/50">{lang.trim()}</span>
                  ))}
                </div>

                {perfil.r2_prefix && (
                  <div className="flex items-center gap-1.5 mt-1">
                    <HardDrive className="h-3 w-3 text-muted-foreground" />
                    <p className="truncate text-xs text-muted-foreground font-mono">{perfil.r2_prefix}</p>
                  </div>
                )}

                <div className="mt-auto flex gap-2 pt-4 border-t border-border/50">
                  <Button asChild size="sm" variant="secondary" className="flex-1 transition-colors hover:bg-primary hover:text-primary-foreground">
                    <Link href={`/admin/marcas/${perfil.id}`}>
                      <Settings className="mr-1.5 h-3.5 w-3.5" />
                      Configurar
                    </Link>
                  </Button>
                  <Button
                    size="icon"
                    variant="ghost"
                    className="h-8 w-8 text-muted-foreground hover:text-foreground hover:bg-muted"
                    disabled={duplicandoId === perfil.id}
                    onClick={() => handleDuplicar(perfil.id)}
                    title="Clonar marca"
                  >
                    {duplicandoId === perfil.id
                      ? <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      : <CopyPlus className="h-4 w-4" />
                    }
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
