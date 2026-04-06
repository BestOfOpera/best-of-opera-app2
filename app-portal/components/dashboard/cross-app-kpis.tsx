"use client"

import { useState, useEffect, useCallback } from "react"
import { useBrand } from "@/lib/brand-context"
import { redatorApi } from "@/lib/api/redator"
import { editorApi } from "@/lib/api/editor"
import { PenTool, Film, CheckCircle2, LayoutDashboard } from "lucide-react"
import { useRouter } from "next/navigation"

interface KPIData {
  redator: number
  editor: number
  concluidos: number
  total: number
  loading: boolean
  error: boolean
}

export function CrossAppKPIs() {
  const { selectedBrand } = useBrand()
  const router = useRouter()
  const [data, setData] = useState<KPIData>({
    redator: 0, editor: 0, concluidos: 0, total: 0, loading: true, error: false,
  })

  const fetchData = useCallback(async () => {
    if (!selectedBrand) return
    try {
      const [redatorRes, editorTotal, editorConcluido] = await Promise.all([
        redatorApi.listProjects({ brand_slug: selectedBrand.slug, limit: 1 }),
        editorApi.listarEdicoes({ limit: "1" }, selectedBrand.id),
        editorApi.listarEdicoes({ status: "concluido", limit: "1" }, selectedBrand.id),
      ])
      const redator = redatorRes.total || 0
      const concluidos = editorConcluido.total || 0
      const editorAtivos = Math.max(0, (editorTotal.total || 0) - concluidos)
      setData({
        redator, editor: editorAtivos, concluidos,
        total: redator + editorAtivos + concluidos,
        loading: false, error: false,
      })
    } catch {
      setData(prev => ({ ...prev, loading: false, error: true }))
    }
  }, [selectedBrand])

  useEffect(() => { fetchData() }, [fetchData])

  const cards = [
    { label: "Redação", value: data.redator, sub: "em andamento", icon: PenTool, href: "/redator", color: "text-yellow-500" },
    { label: "Editor", value: data.editor, sub: "ativos", icon: Film, href: "/editor", color: "text-blue-500" },
    { label: "Concluídos", value: data.concluidos, sub: "prontos", icon: CheckCircle2, href: "/finalizados", color: "text-green-500" },
    { label: "Total", value: data.total, sub: "projetos", icon: LayoutDashboard, href: "#", color: "text-muted-foreground" },
  ]

  if (data.loading) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {[1, 2, 3, 4].map(i => (
          <div key={i} className="rounded-lg border bg-card p-4 animate-pulse">
            <div className="h-4 bg-muted rounded w-20 mb-2" />
            <div className="h-8 bg-muted rounded w-12 mb-1" />
            <div className="h-3 bg-muted rounded w-16" />
          </div>
        ))}
      </div>
    )
  }

  return (
    <div className="mb-6">
      <h3 className="text-sm font-medium text-muted-foreground mb-3">Pipeline completo</h3>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {cards.map(card => (
          <div
            key={card.label}
            className="rounded-lg border bg-card p-4 cursor-pointer hover:border-primary/50 transition-colors"
            onClick={() => card.href !== "#" && router.push(card.href)}
          >
            <div className="flex items-center gap-2 mb-2">
              <card.icon className={`h-4 w-4 ${card.color}`} />
              <span className="text-sm font-medium">{card.label}</span>
            </div>
            <div className="text-2xl font-bold">{data.error ? "—" : card.value}</div>
            <div className="text-xs text-muted-foreground">{card.sub}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
