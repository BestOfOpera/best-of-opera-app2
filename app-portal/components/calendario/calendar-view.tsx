"use client"

import { useState, useEffect, useCallback, useMemo } from "react"
import { useSearchParams, useRouter } from "next/navigation"
import { ChevronLeft, ChevronRight, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { redatorApi, type Project } from "@/lib/api/redator"
import { editorApi, type Edicao, type Perfil } from "@/lib/api/editor"
import { CalendarCell, type EnrichedProject } from "./calendar-cell"
import { AddModal } from "./add-modal"
import { ScheduleDropdown } from "./schedule-dropdown"
import { toast } from "sonner"

function extractVideoId(url: string): string {
  const m = url.match(/(?:v=|youtu\.be\/|\/embed\/)([a-zA-Z0-9_-]{11})/)
  return m ? m[1] : url
}

function getMonday(d: Date): Date {
  const date = new Date(d)
  const day = date.getDay()
  const diff = day === 0 ? -6 : 1 - day
  date.setDate(date.getDate() + diff)
  date.setHours(0, 0, 0, 0)
  return date
}

function formatISO(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, "0")
  const day = String(d.getDate()).padStart(2, "0")
  return `${y}-${m}-${day}`
}

function formatShort(dateStr: string): string {
  const [, m, d] = dateStr.split("-")
  return `${d}/${m}`
}

function getWeekDates(monday: Date): string[] {
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(monday)
    d.setDate(d.getDate() + i)
    return formatISO(d)
  })
}

export function CalendarView() {
  const searchParams = useSearchParams()
  const router = useRouter()

  const initialMonday = useMemo(() => {
    const weekParam = searchParams.get("week")
    if (weekParam) {
      const parsed = new Date(weekParam + "T12:00:00")
      if (!isNaN(parsed.getTime())) return getMonday(parsed)
    }
    return getMonday(new Date())
  }, [])

  const [weekStart, setWeekStart] = useState<Date>(initialMonday)
  const [scheduled, setScheduled] = useState<Project[]>([])
  const [unscheduled, setUnscheduled] = useState<Project[]>([])
  const [edicoes, setEdicoes] = useState<Edicao[]>([])
  const [perfis, setPerfis] = useState<Perfil[]>([])
  const [loading, setLoading] = useState(true)
  const [addModal, setAddModal] = useState<{ date: string; brandSlug: string } | null>(null)

  const weekDates = useMemo(() => getWeekDates(weekStart), [weekStart])
  const todayStr = useMemo(() => formatISO(new Date()), [])

  const edicaoMap = useMemo(() => {
    const map = new Map<string, Edicao>()
    for (const e of edicoes) {
      if (e.youtube_url) map.set(extractVideoId(e.youtube_url), e)
    }
    return map
  }, [edicoes])

  const perfisAtivos = useMemo(
    () => perfis.filter((p) => p.ativo),
    [perfis]
  )

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const startDate = weekDates[0]
      const endDate = weekDates[6]

      const [calendarRes, perfisRes] = await Promise.all([
        redatorApi.getCalendar(startDate, endDate),
        editorApi.listarPerfis(),
      ])

      setScheduled(calendarRes.scheduled)
      setUnscheduled(calendarRes.unscheduled)
      setPerfis(perfisRes)

      const activePerfis = perfisRes.filter((p) => p.ativo)
      if (activePerfis.length > 0) {
        const edicaoResults = await Promise.all(
          activePerfis.map((p) => editorApi.listarEdicoes({ limit: "0" }, p.id))
        )
        setEdicoes(edicaoResults.flatMap((r) => r.edicoes))
      }
    } catch {
      toast.error("Erro ao carregar calendario")
    } finally {
      setLoading(false)
    }
  }, [weekDates])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  function navigateWeek(offset: number) {
    const next = new Date(weekStart)
    next.setDate(next.getDate() + offset * 7)
    setWeekStart(next)
    router.replace(`?week=${formatISO(next)}`, { scroll: false })
  }

  function goToToday() {
    const monday = getMonday(new Date())
    setWeekStart(monday)
    router.replace(`?week=${formatISO(monday)}`, { scroll: false })
  }

  function jumpToDate(dateStr: string) {
    if (!dateStr) return
    const d = new Date(dateStr + "T12:00:00")
    if (isNaN(d.getTime())) return
    const monday = getMonday(d)
    setWeekStart(monday)
    router.replace(`?week=${formatISO(monday)}`, { scroll: false })
  }

  function enrichProject(p: Project): EnrichedProject {
    const vid = p.youtube_url ? extractVideoId(p.youtube_url) : ""
    const edicao = vid ? edicaoMap.get(vid) : undefined
    return { ...p, editorStatus: edicao?.status }
  }

  function getProjectsForCell(date: string, brandSlug: string): EnrichedProject[] {
    return scheduled
      .filter((p) => p.scheduled_date === date && p.brand_slug === brandSlug)
      .map(enrichProject)
  }

  const stats = useMemo(() => {
    const total = scheduled.length
    const late = scheduled.filter(
      (p) =>
        p.scheduled_date &&
        p.scheduled_date < todayStr &&
        p.status !== "export_ready"
    ).length
    const ready = scheduled.filter((p) => p.status === "export_ready").length
    return { total, late, ready, pending: total - ready }
  }, [scheduled, todayStr])

  return (
    <div className="flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Button variant="outline" size="icon" className="h-8 w-8" onClick={() => navigateWeek(-1)}>
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <h2 className="text-sm font-semibold">
            Semana de {formatShort(weekDates[0])} — {formatShort(weekDates[6])}
          </h2>
          <Button variant="outline" size="icon" className="h-8 w-8" onClick={() => navigateWeek(1)}>
            <ChevronRight className="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="sm" className="text-xs" onClick={goToToday}>
            Hoje
          </Button>
          <input
            type="date"
            className="ml-2 rounded border border-border bg-background px-2 py-1 text-xs"
            onChange={(e) => jumpToDate(e.target.value)}
          />
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="text-xs">{stats.total} agendados</Badge>
          <Badge variant="outline" className="text-xs text-green-600">{stats.ready} prontos</Badge>
          {stats.late > 0 && (
            <Badge variant="destructive" className="text-xs">{stats.late} atrasados</Badge>
          )}
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <>
          {/* Grid por marca */}
          {perfisAtivos.length === 0 ? (
            <p className="py-10 text-center text-sm text-muted-foreground">
              Nenhuma marca ativa encontrada.
            </p>
          ) : (
            perfisAtivos.map((perfil) => (
              <div key={perfil.id} className="flex flex-col gap-1.5">
                <div className="flex items-center gap-2">
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    {perfil.nome}
                  </h3>
                  <Badge variant="outline" className="text-[9px] uppercase">{perfil.sigla}</Badge>
                </div>
                <div className="grid grid-cols-7 gap-1">
                  {weekDates.map((date) => (
                    <CalendarCell
                      key={date}
                      date={date}
                      projects={getProjectsForCell(date, perfil.slug)}
                      isToday={date === todayStr}
                      onAddClick={() => setAddModal({ date, brandSlug: perfil.slug })}
                      onScheduleChange={() => fetchData()}
                    />
                  ))}
                </div>
              </div>
            ))
          )}

          {/* Projetos sem data */}
          {unscheduled.length > 0 && (
            <div className="mt-4 flex flex-col gap-2">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Sem Data ({unscheduled.length})
              </h3>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
                {unscheduled.map((p) => {
                  const enriched = enrichProject(p)
                  return (
                    <div key={p.id} className="flex items-center gap-1 rounded-md border border-border bg-card p-2">
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-xs font-medium">{p.artist}</p>
                        <p className="truncate text-[10px] text-muted-foreground">{p.work}</p>
                        <Badge variant="outline" className="mt-0.5 text-[9px]">{p.brand_slug}</Badge>
                      </div>
                      <ScheduleDropdown
                        projectId={p.id}
                        onScheduleChange={() => fetchData()}
                      />
                    </div>
                  )
                })}
              </div>
            </div>
          )}
        </>
      )}

      {/* Add Modal */}
      {addModal && (
        <AddModal
          open={true}
          onClose={() => setAddModal(null)}
          targetDate={addModal.date}
          brandSlug={addModal.brandSlug}
          unscheduledProjects={unscheduled}
          onProjectScheduled={() => {
            setAddModal(null)
            fetchData()
          }}
        />
      )}
    </div>
  )
}
