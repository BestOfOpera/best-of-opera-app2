"use client"

import { useState, useMemo } from "react"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { redatorApi, type Project, type R2AvailableItem } from "@/lib/api/redator"
import { isRecentProject } from "@/lib/project-utils"
import { Download } from "lucide-react"
import { cn } from "@/lib/utils"
import { toast } from "sonner"

interface AddModalProps {
  open: boolean
  onClose: () => void
  targetDate: string
  brandSlug: string
  unscheduledProjects: Project[]
  r2Items?: R2AvailableItem[]
  onProjectScheduled: () => void
}

export function AddModal({
  open,
  onClose,
  targetDate,
  brandSlug,
  unscheduledProjects,
  r2Items,
  onProjectScheduled,
}: AddModalProps) {
  const [search, setSearch] = useState("")
  const [scheduling, setScheduling] = useState<number | null>(null)

  const filtered = useMemo(() => {
    const projects = unscheduledProjects
      .filter((p) => (p.brand_slug || "").toLowerCase() === (brandSlug || "").toLowerCase())
      .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    if (!search.trim()) return projects
    const term = search.toLowerCase()
    return projects.filter(
      (p) =>
        p.artist.toLowerCase().includes(term) ||
        p.work.toLowerCase().includes(term)
    )
  }, [unscheduledProjects, brandSlug, search])

  async function handleSelect(project: Project) {
    setScheduling(project.id)
    try {
      await redatorApi.scheduleProject(project.id, targetDate)
      toast.success(`"${project.artist}" agendado para ${formatDate(targetDate)}`)
      onProjectScheduled()
      onClose()
    } catch {
      toast.error("Erro ao agendar projeto")
    } finally {
      setScheduling(null)
    }
  }

  async function handleScheduleR2(item: R2AvailableItem) {
    setScheduling(-1)
    try {
      const project = await redatorApi.createProject({
        artist: item.artist,
        work: item.work,
        composer: "",
      }, brandSlug)
      await redatorApi.scheduleProject(project.id, targetDate)
      toast.success(`"${item.artist}" agendado para ${formatDate(targetDate)}`)
      onProjectScheduled()
      onClose()
    } catch {
      toast.error("Erro ao agendar vídeo do R2")
    } finally {
      setScheduling(null)
    }
  }

  const filteredR2 = useMemo(() => {
    if (!r2Items?.length) return []
    if (!search.trim()) return r2Items
    const term = search.toLowerCase()
    return r2Items.filter(
      (item) =>
        item.artist.toLowerCase().includes(term) ||
        item.work.toLowerCase().includes(term)
    )
  }, [r2Items, search])

  function formatDate(dateStr: string) {
    const [y, m, d] = dateStr.split("-")
    return `${d}/${m}/${y}`
  }

  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) onClose() }}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>
            Agendar projeto para {formatDate(targetDate)}
          </DialogTitle>
        </DialogHeader>
        <Input
          placeholder="Buscar por artista ou obra..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          autoFocus
        />
        <div className="mt-2 max-h-80 overflow-y-auto">
          {filtered.length === 0 ? (
            <p className="py-8 text-center text-sm text-muted-foreground">
              Nenhum projeto sem data encontrado para esta marca.
            </p>
          ) : (
            <div className="flex flex-col gap-1">
              {filtered.map((p) => (
                <button
                  key={p.id}
                  disabled={scheduling === p.id}
                  onClick={() => handleSelect(p)}
                  className={cn(
                    "flex items-center gap-2 rounded-md px-3 py-2 text-left transition-colors hover:bg-muted/60 disabled:opacity-50",
                    isRecentProject(p.created_at) && "ring-1 ring-green-400/50 bg-green-50/30 dark:bg-green-950/20"
                  )}
                >
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">{p.artist}</p>
                    <p className="truncate text-xs text-muted-foreground">{p.work}</p>
                  </div>
                  <Badge variant="outline" className="shrink-0 text-[10px]">
                    {p.status}
                  </Badge>
                </button>
              ))}
            </div>
          )}
          {/* R2 items disponíveis */}
          {filteredR2.length > 0 && (
            <div className="mt-3 border-t pt-3">
              <p className="text-xs font-semibold text-muted-foreground mb-2">
                Vídeos disponíveis (R2)
              </p>
              <div className="flex flex-col gap-1">
                {filteredR2.map((item, i) => (
                  <button
                    key={`r2-${i}`}
                    disabled={scheduling !== null}
                    onClick={() => handleScheduleR2(item)}
                    className={cn(
                      "flex items-center gap-2 rounded-md px-3 py-2 text-left transition-colors hover:bg-muted/60 disabled:opacity-50",
                      item.prepared_at && isRecentProject(item.prepared_at) && "ring-1 ring-green-400/50 bg-green-50/30 dark:bg-green-950/20"
                    )}
                  >
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium">{item.artist}</p>
                      <p className="truncate text-xs text-muted-foreground">{item.work}</p>
                    </div>
                    <Badge variant="outline" className="shrink-0 text-[10px] bg-blue-50 text-blue-600">
                      <Download className="mr-1 h-3 w-3" /> R2
                    </Badge>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
