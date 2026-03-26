"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { StatusBadge } from "@/components/status-badge"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import { Plus, Music, ArrowRight, Download, ChevronDown, Trash2 } from "lucide-react"
import { redatorApi, type Project, type R2AvailableItem } from "@/lib/api/redator"
import { useBrand } from "@/lib/brand-context"
import { toast } from "sonner"

type View = "em_andamento" | "export_ready" | "r2"

const VIEW_LABELS: Record<View, string> = {
  em_andamento: "Em andamento",
  export_ready: "Prontos p/ Exportar",
  r2: "Prontos para o Redator",
}

const STATUS_EM_ANDAMENTO = ["input_complete", "generating", "awaiting_approval", "translating"]

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

  const [activeView, setActiveView] = useState<View>("em_andamento")
  const [selectMode, setSelectMode] = useState(false)
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())
  const [selectedFolders, setSelectedFolders] = useState<Set<string>>(new Set())
  const [deleting, setDeleting] = useState(false)

  useEffect(() => {
    setSelectMode(false)
    setSelectedIds(new Set())
    setSelectedFolders(new Set())
  }, [activeView, selectedBrand?.slug])

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

  const emAndamento = projects.filter(p => STATUS_EM_ANDAMENTO.includes(p.status))
  const prontos = projects.filter(p => p.status === "export_ready")

  const currentProjects = activeView === "em_andamento" ? emAndamento : activeView === "export_ready" ? prontos : []
  const currentR2 = activeView === "r2" ? r2Items : []

  const allProjectIds = currentProjects.map(p => p.id)
  const allFolders = currentR2.map(i => i.folder)
  const totalItems = activeView === "r2" ? allFolders.length : allProjectIds.length
  const totalSelected = activeView === "r2" ? selectedFolders.size : selectedIds.size

  const toggleProject = (id: number) => {
    setSelectedIds(prev => { const n = new Set(prev); n.has(id) ? n.delete(id) : n.add(id); return n })
  }
  const toggleFolder = (folder: string) => {
    setSelectedFolders(prev => { const n = new Set(prev); n.has(folder) ? n.delete(folder) : n.add(folder); return n })
  }
  const toggleSelectAll = () => {
    if (activeView === "r2") {
      setSelectedFolders(selectedFolders.size === allFolders.length ? new Set() : new Set(allFolders))
    } else {
      setSelectedIds(selectedIds.size === allProjectIds.length ? new Set() : new Set(allProjectIds))
    }
  }

  const handleDelete = async () => {
    setDeleting(true)
    try {
      if (activeView === "r2") {
        await redatorApi.deleteR2Items(Array.from(selectedFolders))
        setR2Items(prev => prev.filter(i => !selectedFolders.has(i.folder)))
        setSelectedFolders(new Set())
        toast.success(`${selectedFolders.size} item(s) removido(s)`)
      } else {
        const ids = Array.from(selectedIds)
        await redatorApi.deleteProjects(ids)
        setProjects(prev => prev.filter(p => !selectedIds.has(p.id)))
        setSelectedIds(new Set())
        toast.success(`${ids.length} projeto(s) removido(s)`)
      }
      setSelectMode(false)
    } catch {
      toast.error("Erro ao remover itens")
    } finally {
      setDeleting(false)
    }
  }

  if (loading) {
    return <div className="flex items-center justify-center py-12 text-sm text-muted-foreground">Carregando projetos...</div>
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-foreground">Projetos</h1>
          <p className="text-sm text-muted-foreground">{projects.length} projetos</p>
        </div>
        <div className="flex items-center gap-2">
          {/* Botão excluir — só no modo seleção com itens selecionados */}
          {selectMode && totalSelected > 0 && (
            <Button size="sm" variant="destructive" onClick={handleDelete} disabled={deleting} className="gap-1.5">
              <Trash2 className="h-3.5 w-3.5" />
              {deleting ? "Removendo..." : `Excluir (${totalSelected})`}
            </Button>
          )}
          {/* Selecionar / Cancelar */}
          {(activeView !== "em_andamento" || emAndamento.length > 0) && (
            <Button
              size="sm"
              variant="ghost"
              onClick={() => { setSelectMode(s => !s); setSelectedIds(new Set()); setSelectedFolders(new Set()) }}
            >
              {selectMode ? "Cancelar" : "Selecionar"}
            </Button>
          )}
          {/* Dropdown de view */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button size="sm" variant="outline" className="gap-1.5">
                {VIEW_LABELS[activeView]} <ChevronDown className="h-3.5 w-3.5" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              {(Object.keys(VIEW_LABELS) as View[]).map(v => (
                <DropdownMenuItem key={v} onClick={() => setActiveView(v)} className={activeView === v ? "font-medium" : ""}>
                  {VIEW_LABELS[v]}
                  {v === "em_andamento" && emAndamento.length > 0 && <span className="ml-auto text-xs text-muted-foreground">{emAndamento.length}</span>}
                  {v === "export_ready" && prontos.length > 0 && <span className="ml-auto text-xs text-muted-foreground">{prontos.length}</span>}
                  {v === "r2" && r2Items.length > 0 && <span className="ml-auto text-xs text-muted-foreground">{r2Items.length}</span>}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
          {/* Novo Projeto */}
          <Link href="/redator/novo">
            <Button size="sm">
              <Plus className="mr-2 h-3.5 w-3.5" />
              Novo Projeto
            </Button>
          </Link>
        </div>
      </div>

      {/* Barra de seleção total */}
      {selectMode && totalItems > 0 && (
        <div className="flex items-center gap-3 text-sm">
          <input
            type="checkbox"
            checked={totalSelected === totalItems}
            onChange={toggleSelectAll}
            className="h-4 w-4 accent-primary cursor-pointer"
          />
          <span className="text-muted-foreground">
            {totalSelected === totalItems ? "Desmarcar tudo" : "Selecionar tudo"}
          </span>
        </div>
      )}

      {/* View: Em andamento / Prontos p/ Exportar */}
      {activeView !== "r2" && (
        currentProjects.length === 0 ? (
          <div className="text-center py-12 text-sm text-muted-foreground">
            Nenhum projeto {activeView === "em_andamento" ? "em andamento" : "pronto para exportar"}.
          </div>
        ) : (
          <div className="space-y-2">
            {currentProjects.map(p => (
              <div key={p.id} className="flex items-center gap-2">
                {selectMode && (
                  <input
                    type="checkbox"
                    checked={selectedIds.has(p.id)}
                    onChange={() => toggleProject(p.id)}
                    className="h-4 w-4 accent-primary flex-shrink-0 cursor-pointer"
                  />
                )}
                <Link href={nextStepLink(p)} className="flex-1">
                  <Card className={`cursor-pointer transition-colors hover:bg-muted/20 ${selectMode && selectedIds.has(p.id) ? "border-primary/40 bg-primary/5" : ""}`}>
                    <CardContent className="flex items-center gap-4 p-4">
                      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                        <Music className="h-5 w-5 text-primary" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-foreground">{p.artist} — {p.work}</p>
                        <p className="text-xs text-muted-foreground">
                          {p.composer}{p.category ? ` · ${p.category}` : ""}
                        </p>
                      </div>
                      <div className="flex items-center gap-2 text-right text-xs text-muted-foreground">
                        {p.overlay_approved && <span className="text-emerald-600">Legendas OK</span>}
                        {p.post_approved && <span className="text-emerald-600">Post OK</span>}
                        {p.youtube_approved && <span className="text-emerald-600">YouTube OK</span>}
                      </div>
                      {selectedBrand && (
                        <span
                          className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wide flex-shrink-0"
                          style={{ backgroundColor: selectedBrand.cor_secundaria + "22", color: selectedBrand.cor_secundaria, border: `1px solid ${selectedBrand.cor_secundaria}44` }}
                        >
                          {selectedBrand.sigla}
                        </span>
                      )}
                      <StatusBadge status={p.status as any} />
                    </CardContent>
                  </Card>
                </Link>
              </div>
            ))}
          </div>
        )
      )}

      {/* View: Prontos para o Redator (R2) */}
      {activeView === "r2" && (
        r2Items.length === 0 ? (
          <div className="text-center py-12 text-sm text-muted-foreground">Nenhum vídeo aguardando no R2.</div>
        ) : (
          <div className="space-y-2">
            {r2Items.map(item => (
              <div key={item.folder} className="flex items-center gap-2">
                {selectMode && (
                  <input
                    type="checkbox"
                    checked={selectedFolders.has(item.folder)}
                    onChange={() => toggleFolder(item.folder)}
                    className="h-4 w-4 accent-destructive flex-shrink-0 cursor-pointer"
                  />
                )}
                <Link href={`/redator/novo?r2_folder=${encodeURIComponent(item.folder)}`} className="flex-1">
                  <Card className={`cursor-pointer border-primary/20 transition-colors hover:bg-primary/10 ${selectMode && selectedFolders.has(item.folder) ? "bg-destructive/5 border-destructive/20" : "bg-primary/5"}`}>
                    <CardContent className="flex items-center gap-4 p-4">
                      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/15">
                        <Download className="h-5 w-5 text-primary" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-foreground">{item.artist} — {item.work}</p>
                        <p className="text-xs text-primary/70">Vamos criar texto e legendas overlay?</p>
                      </div>
                      <ArrowRight className="h-4 w-4 text-primary" />
                    </CardContent>
                  </Card>
                </Link>
              </div>
            ))}
          </div>
        )
      )}

      {/* Empty state geral */}
      {projects.length === 0 && r2Items.length === 0 && (
        <Card className="text-center">
          <CardContent className="py-12">
            <p className="text-sm text-muted-foreground mb-4">Nenhum projeto ainda.</p>
            <Link href="/redator/novo">
              <Button>Crie seu primeiro projeto</Button>
            </Link>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
