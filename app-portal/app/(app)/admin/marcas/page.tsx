"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { editorApi, type Perfil } from "@/lib/api/editor"
import { RequireAdmin } from "@/components/auth/require-admin"
import { toast } from "sonner"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Loader2, Plus, Settings, CopyPlus, Globe } from "lucide-react"

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
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16 gap-3 text-center">
            <Globe className="h-10 w-10 text-muted-foreground/40" />
            <p className="text-muted-foreground text-sm">Nenhuma marca configurada.</p>
            <Button asChild size="sm" variant="outline">
              <Link href="/admin/marcas/nova">Criar primeira marca</Link>
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {perfis.map((perfil) => (
            <Card key={perfil.id} className="flex flex-col">
              <CardContent className="flex flex-1 flex-col gap-3 p-5">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2.5">
                    <span
                      className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-xs font-bold text-white"
                      style={{ backgroundColor: perfil.cor_primaria || "#3b82f6" }}
                    >
                      {perfil.sigla}
                    </span>
                    <div>
                      <p className="font-semibold text-foreground leading-tight">{perfil.nome}</p>
                      <p className="text-xs text-muted-foreground">{perfil.slug}</p>
                    </div>
                  </div>
                  <Badge variant={perfil.ativo ? "default" : "secondary"} className="shrink-0 text-[10px]">
                    {perfil.ativo ? "Ativo" : "Inativo"}
                  </Badge>
                </div>

                <div className="flex flex-wrap gap-1">
                  {(perfil.idiomas_alvo || "").split(",").filter(Boolean).map((lang) => (
                    <span key={lang} className="rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground font-mono uppercase">{lang.trim()}</span>
                  ))}
                </div>

                {perfil.r2_prefix && (
                  <p className="truncate text-[11px] text-muted-foreground font-mono">R2: {perfil.r2_prefix}</p>
                )}

                <div className="mt-auto flex gap-2 pt-2">
                  <Button asChild size="sm" variant="outline" className="flex-1">
                    <Link href={`/admin/marcas/${perfil.id}`}>
                      <Settings className="mr-1.5 h-3.5 w-3.5" />
                      Configurar
                    </Link>
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    disabled={duplicandoId === perfil.id}
                    onClick={() => handleDuplicar(perfil.id)}
                    title="Clonar marca"
                  >
                    {duplicandoId === perfil.id
                      ? <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      : <CopyPlus className="h-3.5 w-3.5" />
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
