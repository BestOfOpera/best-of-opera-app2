"use client"

import { useState, useEffect, useCallback } from "react"
import { useBrand } from "@/lib/brand-context"
import { redatorApi, Project } from "@/lib/api/redator"
import { editorApi, Edicao } from "@/lib/api/editor"
import { PenTool, Film } from "lucide-react"

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime()
  const min = Math.floor(diff / 60_000)
  if (min < 1) return "agora"
  if (min < 60) return `${min}min`
  const h = Math.floor(min / 60)
  if (h < 24) return `${h}h`
  const d = Math.floor(h / 24)
  return `${d}d`
}

function inferAction(item: Project | Edicao, source: "redator" | "editor"): string {
  if (source === "redator") {
    const p = item as Project
    if (p.automation_approved) return "Automação aprovada"
    if (p.youtube_approved) return "YouTube aprovado"
    if (p.post_approved) return "Post aprovado"
    if (p.overlay_approved) return "Overlay aprovado"
    if (p.status === "concluido") return "Concluído"
    return `Status: ${p.status || "novo"}`
  }
  const e = item as Edicao
  if (e.status === "concluido") return "Concluído"
  if (e.status === "erro") return "Erro"
  if (e.status === "processando") return `Processando (passo ${e.passo_atual})`
  return `Status: ${e.status || "pendente"}`
}

interface TimelineItem {
  id: string
  source: "redator" | "editor"
  title: string
  action: string
  time: string
  date: string
}

export function ActivityTimeline() {
  const { selectedBrand } = useBrand()
  const [items, setItems] = useState<TimelineItem[]>([])
  const [loading, setLoading] = useState(true)

  const fetchData = useCallback(async () => {
    if (!selectedBrand) return
    try {
      const [redatorRes, editorRes] = await Promise.all([
        redatorApi.listProjects({ brand_slug: selectedBrand.slug, sort_by: "updated_at", sort_order: "desc", limit: 5 }),
        editorApi.listarEdicoes({ sort_by: "updated_at", sort_order: "desc", limit: "5" }, selectedBrand.id),
      ])

      const combined: TimelineItem[] = []
      for (const p of redatorRes.projects || []) {
        combined.push({
          id: `r-${p.id}`,
          source: "redator",
          title: `${p.artist} — ${p.work}`,
          action: inferAction(p, "redator"),
          time: timeAgo(p.updated_at),
          date: p.updated_at,
        })
      }
      for (const e of editorRes.edicoes || []) {
        combined.push({
          id: `e-${e.id}`,
          source: "editor",
          title: `${e.artista} — ${e.musica}`,
          action: inferAction(e, "editor"),
          time: timeAgo(e.updated_at),
          date: e.updated_at,
        })
      }

      combined.sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime())
      setItems(combined.slice(0, 10))
    } catch {
      // Silencioso
    } finally {
      setLoading(false)
    }
  }, [selectedBrand])

  useEffect(() => { fetchData() }, [fetchData])

  if (loading) {
    return (
      <div className="mb-6">
        <div className="h-4 bg-muted rounded w-32 mb-3" />
        <div className="rounded-lg border bg-card divide-y">
          {[1, 2, 3].map(i => (
            <div key={i} className="p-3 animate-pulse flex gap-3">
              <div className="h-4 w-4 bg-muted rounded" />
              <div className="flex-1 space-y-1">
                <div className="h-3 bg-muted rounded w-3/4" />
                <div className="h-2 bg-muted rounded w-1/2" />
              </div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  if (items.length === 0) return null

  return (
    <div className="mb-6">
      <h3 className="text-sm font-medium text-muted-foreground mb-3">Atividade recente</h3>
      <div className="rounded-lg border bg-card divide-y">
        {items.map(item => (
          <div key={item.id} className="flex items-center gap-3 px-4 py-2.5 text-sm">
            {item.source === "redator" ? (
              <PenTool className="h-3.5 w-3.5 shrink-0 text-yellow-500" />
            ) : (
              <Film className="h-3.5 w-3.5 shrink-0 text-blue-500" />
            )}
            <div className="flex-1 min-w-0">
              <span className="font-medium truncate block">{item.title}</span>
              <span className="text-xs text-muted-foreground">{item.action}</span>
            </div>
            <span className="text-xs text-muted-foreground shrink-0">{item.time}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
