"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { StatusBadge } from "@/components/status-badge"
import { Plus, Music, ArrowRight, Download, Trash2 } from "lucide-react"
import { redatorApi, type Project, type R2AvailableItem } from "@/lib/api/redator"
import { useBrand } from "@/lib/brand-context"
import { toast } from "sonner"

function nextStepLink(p: Project): string {
  if (p.status === "input_complete" || p.status === "generating") return `/redator/projeto/${p.id}/overlay`
  if (!p.overlay_approved) return `/redator/projeto/${p.id}/overlay`
  if (!p.post_approved) return `/redator/projeto/${p.id}/post`
  if (!p.youtube_approved) return `/redator/projeto/${p.id}/youtube`
  return `/redator/projeto/${p.id}/exportar`
}

export function RedatorProjectList() {
  const { selectedBrand } = useBrand()
  const [projects, setProjects] = useState<Project[]>([])
  const [r2Items, setR2Items] = useState<R2AvailableItem[]>([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [deleting, setDeleting] = useState(false)

  const toggleSelect = (folder: string) => {
    setSelected(prev => {
      const next = new Set(prev)
      next.has(folder) ? next.delete(folder) : next.add(folder)
      return next
    })
  }

  const handleDelete = async () => {
    if (selected.size === 0) return
    setDeleting(true)
    try {
      await redatorApi.deleteR2Items(Array.from(selected))
      setR2Items(prev => prev.filter(i => !selected.has(i.folder)))
      setSelected(new Set())
      toast.success(`${selected.size} item(s) removido(s)`)
    } catch {
      toast.error("Erro ao remover itens")
    } finally {
      setDeleting(false)
    }
  }

  useEffect(() => {
    setLoading(true)
    Promise.all([
      redatorApi.listProjects(selectedBrand?.slug),
      redatorApi.listR2Available(selectedBrand?.slug, selectedBrand?.r2_prefix).catch(() => [] as R2AvailableItem[]),
    ]).then(([projs, r2]) => {
      setProjects(projs)
      setR2Items(r2)
    }).finally(() => setLoading(false))
  }, [selectedBrand?.slug])

  if (loading) {
    return <div className="flex items-center justify-center py-12 text-sm text-muted-foreground">Carregando projetos...</div>
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-foreground">Projetos</h1>
          <p className="text-sm text-muted-foreground">{projects.length} projetos</p>
        </div>
        <div className="flex items-center gap-2">
          {selected.size > 0 && (
            <Button size="sm" variant="destructive" onClick={handleDelete} disabled={deleting} className="gap-1.5">
              <Trash2 className="h-3.5 w-3.5" />
              {deleting ? "Removendo..." : `Limpar seleção (${selected.size})`}
            </Button>
          )}
          <Link href="/redator/novo">
            <Button size="sm">
              <Plus className="mr-2 h-3.5 w-3.5" />
              Novo Projeto
            </Button>
          </Link>
        </div>
      </div>

      {r2Items.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center gap-3">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Prontos para o Redator
            </p>
            <button
              onClick={() => setSelected(
                selected.size === r2Items.length
                  ? new Set()
                  : new Set(r2Items.map(i => i.folder))
              )}
              className="text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              {selected.size === r2Items.length ? "Desmarcar tudo" : "Selecionar tudo"}
            </button>
          </div>
          {r2Items.map((item) => (
            <div key={item.folder} className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={selected.has(item.folder)}
                onChange={() => toggleSelect(item.folder)}
                className="h-4 w-4 accent-destructive flex-shrink-0 cursor-pointer"
                onClick={e => e.stopPropagation()}
              />
              <Link
                href={`/redator/novo?r2_folder=${encodeURIComponent(item.folder)}`}
                className="flex-1"
              >
                <Card className={`cursor-pointer border-primary/20 transition-colors hover:bg-primary/10 ${selected.has(item.folder) ? "bg-destructive/5 border-destructive/20" : "bg-primary/5"}`}>
                  <CardContent className="flex items-center gap-4 p-4">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/15">
                      <Download className="h-5 w-5 text-primary" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-foreground">
                        {item.artist} — {item.work}
                      </p>
                      <p className="text-xs text-primary/70">Vamos criar texto e legendas overlay?</p>
                    </div>
                    <ArrowRight className="h-4 w-4 text-primary" />
                  </CardContent>
                </Card>
              </Link>
            </div>
          ))}
        </div>
      )}

      {projects.length === 0 && r2Items.length === 0 ? (
        <Card className="text-center">
          <CardContent className="py-12">
            <p className="text-sm text-muted-foreground mb-4">Nenhum projeto ainda.</p>
            <Link href="/redator/novo">
              <Button>Crie seu primeiro projeto</Button>
            </Link>
          </CardContent>
        </Card>
      ) : projects.length > 0 ? (
        <div className="space-y-2">
          {projects.map((project) => (
            <Link key={project.id} href={nextStepLink(project)}>
              <Card className="cursor-pointer transition-colors hover:bg-muted/20">
                <CardContent className="flex items-center gap-4 p-4">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                    <Music className="h-5 w-5 text-primary" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-foreground">{project.artist} — {project.work}</p>
                    <p className="text-xs text-muted-foreground">
                      {project.composer} {project.category ? `· ${project.category}` : ""}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 text-right text-xs text-muted-foreground">
                    {project.overlay_approved && <span className="text-emerald-600">Legendas OK</span>}
                    {project.post_approved && <span className="text-emerald-600">Post OK</span>}
                    {project.youtube_approved && <span className="text-emerald-600">YouTube OK</span>}
                  </div>
                  {selectedBrand && (
                    <span
                      className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wide flex-shrink-0"
                      style={{ backgroundColor: selectedBrand.cor_secundaria + "22", color: selectedBrand.cor_secundaria, border: `1px solid ${selectedBrand.cor_secundaria}44` }}
                    >
                      {selectedBrand.sigla}
                    </span>
                  )}
                  <StatusBadge status={project.status as any} />
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      ) : null}
    </div>
  )
}
