"use client"

import { useState, useEffect, useCallback } from "react"
import { useBrand } from "@/lib/brand-context"
import { editorApi } from "@/lib/api/editor"
import { CheckCircle2, Target } from "lucide-react"

const WEEKLY_GOAL = 10

export function WeeklyProgress() {
  const { selectedBrand } = useBrand()
  const [count, setCount] = useState(0)
  const [loading, setLoading] = useState(true)

  const fetchData = useCallback(async () => {
    if (!selectedBrand) return
    try {
      // Buscar edições concluídas desta semana
      const res = await editorApi.listarEdicoes(
        { status: "concluido", sort_by: "updated_at", sort_order: "desc", limit: "100" },
        selectedBrand.id,
      )
      // Filtrar pela semana atual (seg-dom)
      const now = new Date()
      const weekStart = new Date(now)
      weekStart.setDate(now.getDate() - now.getDay() + (now.getDay() === 0 ? -6 : 1))
      weekStart.setHours(0, 0, 0, 0)

      const thisWeek = (res.edicoes || []).filter(e => {
        const d = new Date(e.updated_at)
        return d >= weekStart
      })
      setCount(thisWeek.length)
    } catch {
      // Silencioso
    } finally {
      setLoading(false)
    }
  }, [selectedBrand])

  useEffect(() => { fetchData() }, [fetchData])

  const pct = Math.min(100, Math.round((count / WEEKLY_GOAL) * 100))

  if (loading) {
    return (
      <div className="mb-6 animate-pulse">
        <div className="h-4 bg-muted rounded w-40 mb-3" />
        <div className="rounded-lg border bg-card p-4">
          <div className="h-3 bg-muted rounded-full w-full" />
        </div>
      </div>
    )
  }

  return (
    <div className="mb-6">
      <h3 className="text-sm font-medium text-muted-foreground mb-3">Progresso semanal</h3>
      <div className="rounded-lg border bg-card p-4">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <Target className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm font-medium">
              {count} / {WEEKLY_GOAL} concluídos
            </span>
          </div>
          <span className="text-sm font-bold text-primary">{pct}%</span>
        </div>
        <div className="h-2 w-full bg-muted rounded-full overflow-hidden">
          <div
            className="h-full bg-primary rounded-full transition-all duration-500"
            style={{ width: `${pct}%` }}
          />
        </div>
        {count >= WEEKLY_GOAL && (
          <div className="flex items-center gap-1.5 mt-2 text-xs text-green-500">
            <CheckCircle2 className="h-3.5 w-3.5" />
            <span>Meta atingida!</span>
          </div>
        )}
      </div>
    </div>
  )
}
