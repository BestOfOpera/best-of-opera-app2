"use client"

import { useRouter } from "next/navigation"
import { cn } from "@/lib/utils"
import { Badge } from "@/components/ui/badge"
import { ScheduleDropdown } from "./schedule-dropdown"
import type { Project } from "@/lib/api/redator"
import { isRecentProject, RECENT_CLASSES } from "@/lib/project-utils"

const STATUS_COLORS: Record<string, string> = {
  input_complete: "bg-gray-100 text-gray-700",
  generating: "bg-blue-100 text-blue-700",
  awaiting_approval: "bg-yellow-100 text-yellow-700",
  translating: "bg-purple-100 text-purple-700",
  export_ready: "bg-green-100 text-green-700",
}

const STATUS_LABELS: Record<string, string> = {
  input_complete: "Novo",
  generating: "Gerando",
  awaiting_approval: "Aprovacao",
  translating: "Traduzindo",
  export_ready: "Pronto",
}

const EDITOR_COLORS: Record<string, string> = {
  pendente: "bg-gray-100 text-gray-600",
  em_andamento: "bg-blue-100 text-blue-600",
  concluido: "bg-green-100 text-green-600",
  erro: "bg-red-100 text-red-600",
}

interface ProjectCardProps {
  project: Project
  editorStatus?: string
  onScheduleChange: (newDate: string | null) => void
}

export function ProjectCard({ project, editorStatus, onScheduleChange }: ProjectCardProps) {
  const router = useRouter()

  const isLate =
    project.scheduled_date &&
    project.scheduled_date < new Date().toISOString().slice(0, 10) &&
    project.status !== "export_ready"

  function handleClick() {
    router.push(`/redator/novo?project_id=${project.id}`)
  }

  return (
    <div
      onClick={handleClick}
      className={cn(
        "group flex cursor-pointer items-center gap-1.5 rounded-md border border-border bg-card px-2 py-1.5 transition-colors hover:bg-muted/60",
        isLate && "border-destructive/40",
        isRecentProject(project.created_at) && RECENT_CLASSES
      )}
    >
      <div className="min-w-0 flex-1">
        <p className="truncate text-xs font-medium text-foreground">
          {project.artist}
        </p>
        <p className="truncate text-[10px] text-muted-foreground">
          {project.work}
        </p>
        <div className="mt-0.5 flex flex-wrap gap-0.5">
          <Badge variant="outline" className={cn("h-4 px-1 text-[9px]", STATUS_COLORS[project.status])}>
            {STATUS_LABELS[project.status] || project.status}
          </Badge>
          {editorStatus && (
            <Badge variant="outline" className={cn("h-4 px-1 text-[9px]", EDITOR_COLORS[editorStatus] || "bg-gray-100 text-gray-600")}>
              Ed: {editorStatus}
            </Badge>
          )}
          {isLate && (
            <Badge variant="destructive" className="h-4 px-1 text-[9px]">
              ATRASADO
            </Badge>
          )}
        </div>
        {project.cut_start && project.cut_end && (
          <p className="text-[9px] text-muted-foreground mt-0.5">
            Corte: {project.cut_start} — {project.cut_end}
          </p>
        )}
      </div>
      <div className="opacity-0 group-hover:opacity-100 transition-opacity">
        <ScheduleDropdown projectId={project.id} onScheduleChange={onScheduleChange} />
      </div>
    </div>
  )
}
