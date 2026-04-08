"use client"

import { useEffect, useState, useCallback } from "react"
import Link from "next/link"
import { useSearchParams, useRouter } from "next/navigation"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { StatusBadge } from "@/components/status-badge"
import { FilterBar } from "@/components/ui/filter-bar"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import { Plus, Music, ArrowRight, Download, ChevronDown, Trash2, RotateCcw } from "lucide-react"
import { redatorApi, type Project, type R2AvailableItem } from "@/lib/api/redator"
import { useBrand } from "@/lib/brand-context"
import { cn } from "@/lib/utils"
import { toast } from "sonner"
import { nextStepLink, isRecentProject, RECENT_CLASSES } from "@/lib/project-utils"

type View = "em_andamento" | "export_ready" | "r2"

const VIEW_LABELS: Record<View, string> = {
  r2: "Prontos para o Redator",
  em_andamento: "Em andamento",
  export_ready: "Prontos p/ Exportar",
}

const STATUS_EM_ANDAMENTO = ["input_complete", "generating", "awaiting_approval", "translating"]

const STATUS_OPTIONS_REDATOR = [
  { value: "", label: "Todos" },
  { value: "input_complete", label: "Aguardando geração" },
  { value: "generating", label: "Gerando" },
  { value: "awaiting_approval", label: "Aguardando aprovação" },
  { value: "translating", label: "Traduzindo" },
]

const SORT_OPTIONS_REDATOR = [
  { value: "created_at:desc", label: "Mais recente" },
  { value: "created_at:asc", label: "Mais antigo" },
  { value: "artist:asc", label: "Artista A→Z" },
  { value: "artist:desc", label: "Artista Z→A" },
  { value: "updated_at:desc", label: "Última atualização" },
]

const SORT_OPTIONS_R2 = [
  { value: "artist:asc", label: "Artista A→Z" },
  { value: "artist:desc", label: "Artista Z→A" },
  { value: "work:asc", label: "Obra A→Z" },
  { value: "work:desc", label: "Obra Z→A" },
]

const PAGE_SIZE = 20


export function RedatorProjectList() {
  const { selectedBrand } = useBrand()
  const searchParams = useSearchParams()
  const router = useRouter()

  const [projects, setProjects] = useState<Project[]>([])
  const [r2Items, setR2Items] = useState<R2AvailableItem[]>([])
  const [loading, setLoading] = useState(true)
  const [total, setTotal] = useState(0)
  const [totalPages, setTotalPages] = useState(1)

  const [activeView, setActiveView] = useState<View>((searchParams.get("tab") as View) || "r2")
  const [selectMode, setSelectMode] = useState(false)
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())
  const [selectedFolders, setSelectedFolders] = useState<Set<string>>(new Set())
  const [deleting, setDeleting] = useState(false)

  const search = searchParams.get("search") || ""
  const filterStatus = searchParams.get("status") || ""
  const sort = searchParams.get("sort") || "created_at:desc"
  const page = parseInt(searchParams.get("page") || "1", 10)

  const updateParams = (updates: Record<string, string>) => {
    const params = new URLSearchParams(searchParams.toString())
    for (const [k, v] of Object.entries(updates)) {
      if (v) params.set(k, v)
      else params.delete(k)
    }
    if (!updates.page) params.set("page", "1")
    router.replace(`?${params.toString()}`, { scroll: false })
  }

  const handleViewChange = (v: View) => {
    setActiveView(v)
    const params = new URLSearchParams()
    params.set("tab", v)
    router.replace(`?${params.toString()}`, { scroll: false })
  }

  useEffect(() => {
    setSelectMode(false)
    setSelectedIds(new Set())
    setSelectedFolders(new Set())
  }, [activeView, selectedBrand?.slug])

  const loadData = useCallback(() => {
    if (!selectedBrand?.slug) return
    setLoading(true)

    const [sort_by, sort_order] = sort.split(":")

    // Build status filter for backend
    let statusParam = ""
    if (activeView === "em_andamento") {
      statusParam = filterStatus || STATUS_EM_ANDAMENTO.join(",")
    } else if (activeView === "export_ready") {
      statusParam = "export_ready"
    }

    const useLimit = activeView !== "r2" ? PAGE_SIZE : 0

    Promise.all([
      redatorApi.listProjects({
        brand_slug: selectedBrand.slug,
        search: search || undefined,
        status: statusParam || undefined,
        sort_by,
        sort_order,
        page: activeView !== "r2" ? page : undefined,
        limit: useLimit || undefined,
      }),
      redatorApi.listR2Available(selectedBrand.slug, selectedBrand.r2_prefix).catch(() => [] as R2AvailableItem[]),
    ]).then(([res, r2]) => {
      setProjects(res.projects ?? (res as any))
      setTotal(res.total ?? 0)
      setTotalPages(res.total_pages ?? 1)
      setR2Items(r2)
    }).finally(() => setLoading(false))
  }, [selectedBrand?.slug, activeView, search, filterStatus, sort, page])

  useEffect(() => {
    loadData()
  }, [loadData])

  const currentProjects = projects

  // R2: frontend filtering + sorting
  const filteredR2 = r2Items.filter(item => {
    if (!search) return true
    const s = search.toLowerCase()
    return (item.artist || "").toLowerCase().includes(s) || (item.work || "").toLowerCase().includes(s)
  })
  const sortedR2 = [...filteredR2].sort((a, b) => {
    const [field, dir] = sort.split(":")
    const aVal = field === "work" ? (a.work || "") : (a.artist || "")
    const bVal = field === "work" ? (b.work || "") : (b.artist || "")
    const cmp = aVal.localeCompare(bVal)
    return dir === "asc" ? cmp : -cmp
  })
  const currentR2 = activeView === "r2" ? sortedR2 : []

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
    const total = activeView === "r2" ? selectedFolders.size : selectedIds.size
    if (!confirm(`Excluir ${total} item(s) permanentemente? Esta ação não pode ser desfeita.`)) return
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
        setSelectedIds(new Set())
        toast.success(`${ids.length} projeto(s) removido(s)`)
      }
      setSelectMode(false)
      // Re-fetch to update total and pagination after delete
      loadData()
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "erro desconhecido"
      toast.error(`Erro ao remover itens: ${msg}`)
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
          <p className="text-sm text-muted-foreground">{total} projetos</p>
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
          {(activeView !== "em_andamento" || total > 0) && (
            <Button
              size="sm"
              variant="outline"
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
                <DropdownMenuItem key={v} onClick={() => handleViewChange(v)} className={activeView === v ? "font-medium" : ""}>
                  {VIEW_LABELS[v]}
                  {v === activeView && total > 0 && <span className="ml-auto text-xs text-muted-foreground">{total}</span>}
                  {v === "r2" && v !== activeView && r2Items.length > 0 && <span className="ml-auto text-xs text-muted-foreground">{r2Items.length}</span>}
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

      {/* FilterBar — all tabs */}
      <FilterBar
        searchPlaceholder="Buscar artista, obra, compositor..."
        searchValue={search}
        onSearchChange={(v) => updateParams({ search: v })}
        statusOptions={activeView === "em_andamento" ? STATUS_OPTIONS_REDATOR : undefined}
        statusValue={filterStatus}
        onStatusChange={(v) => updateParams({ status: v })}
        showStatus={activeView === "em_andamento"}
        sortOptions={activeView === "r2" ? SORT_OPTIONS_R2 : SORT_OPTIONS_REDATOR}
        sortValue={sort}
        onSortChange={(v) => updateParams({ sort: v })}
        page={page}
        totalPages={activeView !== "r2" ? totalPages : 1}
        total={activeView === "r2" ? filteredR2.length : total}
        onPageChange={(p) => updateParams({ page: String(p) })}
        showPagination={activeView !== "r2" && totalPages > 1}
      />

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
                  <Card className={cn(
                    "cursor-pointer transition-colors hover:bg-muted/20",
                    selectMode && selectedIds.has(p.id) && "border-primary/40 bg-primary/5",
                    isRecentProject(p.created_at) && RECENT_CLASSES
                  )}>
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
                      {(p.status === "translating" || p.status === "generating") && (
                        <button
                          title="Resetar projeto (destravar)"
                          className="ml-1 p-1 rounded hover:bg-destructive/10 text-muted-foreground hover:text-destructive transition-colors"
                          onClick={async (e) => {
                            e.preventDefault()
                            e.stopPropagation()
                            if (!confirm("Resetar este projeto? Traduções serão removidas.")) return
                            try {
                              await redatorApi.resetProject(p.id)
                              toast.success("Projeto resetado")
                              loadData()
                            } catch {
                              toast.error("Erro ao resetar projeto")
                            }
                          }}
                        >
                          <RotateCcw className="h-3.5 w-3.5" />
                        </button>
                      )}
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
        currentR2.length === 0 ? (
          <div className="text-center py-12 text-sm text-muted-foreground">
            {search ? "Nenhum vídeo encontrado com esses filtros." : "Nenhum vídeo aguardando no R2."}
          </div>
        ) : (
          <div className="space-y-2">
            {currentR2.map(item => (
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
                  <Card className={cn(
                    "cursor-pointer border-primary/20 transition-colors hover:bg-primary/10",
                    selectMode && selectedFolders.has(item.folder) ? "bg-destructive/5 border-destructive/20" : "bg-primary/5",
                    item.prepared_at && isRecentProject(item.prepared_at) && RECENT_CLASSES
                  )}>
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
      {total === 0 && r2Items.length === 0 && !search && !filterStatus && (
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
