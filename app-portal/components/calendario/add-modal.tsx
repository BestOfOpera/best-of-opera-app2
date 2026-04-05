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
import { redatorApi, type Project } from "@/lib/api/redator"
import { isRecentProject } from "@/lib/project-utils"
import { cn } from "@/lib/utils"
import { toast } from "sonner"

interface AddModalProps {
  open: boolean
  onClose: () => void
  targetDate: string
  brandSlug: string
  unscheduledProjects: Project[]
  onProjectScheduled: () => void
}

export function AddModal({
  open,
  onClose,
  targetDate,
  brandSlug,
  unscheduledProjects,
  onProjectScheduled,
}: AddModalProps) {
  const [search, setSearch] = useState("")
  const [scheduling, setScheduling] = useState<number | null>(null)

  const filtered = useMemo(() => {
    console.log("[AddModal] brandSlug recebido:", brandSlug)
    console.log("[AddModal] total unscheduled:", unscheduledProjects.length)
    console.log("[AddModal] brand_slugs:", [...new Set(unscheduledProjects.map(p => p.brand_slug))])
    const projects = unscheduledProjects
      .filter((p) => (p.brand_slug || "").toLowerCase() === (brandSlug || "").toLowerCase())
      .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    console.log("[AddModal] após filtro:", projects.length)
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
        </div>
      </DialogContent>
    </Dialog>
  )
}
