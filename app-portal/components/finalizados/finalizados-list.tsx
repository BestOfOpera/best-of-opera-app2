"use client"

import { useEffect, useState, useRef, useCallback } from "react"
import { useBrand } from "@/lib/brand-context"
import { editorApi, Edicao } from "@/lib/api/editor"
import { redatorApi, Project } from "@/lib/api/redator"
import { FilterBar } from "@/components/ui/filter-bar"
import { FinalizadoCard } from "./finalizado-card"
import { Loader2, PackageCheck } from "lucide-react"

const SORT_OPTIONS = [
  { value: "created_at:desc", label: "Mais recente" },
  { value: "created_at:asc", label: "Mais antigo" },
  { value: "artista:asc", label: "Artista A-Z" },
  { value: "artista:desc", label: "Artista Z-A" },
]

const LIMIT = 20

export function FinalizadosList() {
  const { selectedBrand } = useBrand()
  const [edicoes, setEdicoes] = useState<Edicao[]>([])
  const [total, setTotal] = useState(0)
  const [totalPages, setTotalPages] = useState(1)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState("")
  const [sort, setSort] = useState("created_at:desc")
  const [loading, setLoading] = useState(false)
  const redatorCache = useRef<Map<number, Project | null>>(new Map())

  const [redatorData, setRedatorData] = useState<Map<number, Project | null>>(new Map())

  const fetchEdicoes = useCallback(async () => {
    if (!selectedBrand) {
      setEdicoes([])
      setTotal(0)
      setTotalPages(1)
      return
    }
    setLoading(true)
    try {
      const [sortBy, sortOrder] = sort.split(":")
      const res = await editorApi.listarEdicoes(
        { status: "concluido", search, sort_by: sortBy, sort_order: sortOrder, page: String(page), limit: String(LIMIT) },
        selectedBrand.id,
      )
      setEdicoes(res.edicoes)
      setTotal(res.total)
      setTotalPages(res.total_pages)

      // Batch-fetch redator data for edicoes with redator_project_id
      const toFetch = res.edicoes
        .filter((e) => e.redator_project_id && !redatorCache.current.has(e.redator_project_id))
        .map((e) => e.redator_project_id!)

      if (toFetch.length > 0) {
        const results = await Promise.allSettled(
          toFetch.map((id) => redatorApi.getProject(id)),
        )
        const newMap = new Map(redatorCache.current)
        results.forEach((r, i) => {
          if (r.status === "fulfilled") {
            newMap.set(toFetch[i], r.value)
          } else {
            newMap.set(toFetch[i], null)
          }
        })
        redatorCache.current = newMap
        setRedatorData(new Map(newMap))
      } else {
        setRedatorData(new Map(redatorCache.current))
      }
    } catch {
      setEdicoes([])
    } finally {
      setLoading(false)
    }
  }, [selectedBrand, search, sort, page])

  useEffect(() => {
    setPage(1)
  }, [search, sort, selectedBrand])

  useEffect(() => {
    fetchEdicoes()
  }, [fetchEdicoes])

  if (!selectedBrand) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-muted-foreground">
        <PackageCheck className="h-12 w-12 mb-4 opacity-40" />
        <p className="text-lg font-medium">Selecione uma marca</p>
        <p className="text-sm">Use o seletor no topo da página para escolher a marca.</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Finalizados</h1>
        <p className="text-sm text-muted-foreground mt-1">Projetos com render concluído — download, cópia de textos e publicação.</p>
      </div>

      <FilterBar
        searchPlaceholder="Buscar artista, obra, compositor..."
        searchValue={search}
        onSearchChange={setSearch}
        showStatus={false}
        sortOptions={SORT_OPTIONS}
        sortValue={sort}
        onSortChange={setSort}
        page={page}
        totalPages={totalPages}
        total={total}
        onPageChange={setPage}
        showPagination={totalPages > 1}
      />

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      ) : edicoes.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-muted-foreground">
          <PackageCheck className="h-10 w-10 mb-3 opacity-40" />
          <p className="text-sm">Nenhum projeto finalizado encontrado.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {edicoes.map((edicao) => (
            <FinalizadoCard
              key={edicao.id}
              edicao={edicao}
              redatorProject={edicao.redator_project_id ? redatorData.get(edicao.redator_project_id) ?? null : null}
              onRefresh={fetchEdicoes}
            />
          ))}
        </div>
      )}
    </div>
  )
}
