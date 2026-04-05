"use client"

import { Plus } from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { ProjectCard } from "./project-card"
import type { Project } from "@/lib/api/redator"

const DAY_NAMES = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sab"]

export interface EnrichedProject extends Project {
  editorStatus?: string
}

interface CalendarCellProps {
  date: string
  projects: EnrichedProject[]
  isToday: boolean
  onAddClick: () => void
  onScheduleChange: () => void
}

export function CalendarCell({
  date,
  projects,
  isToday,
  onAddClick,
  onScheduleChange,
}: CalendarCellProps) {
  const d = new Date(date + "T12:00:00")
  const dayName = DAY_NAMES[d.getUTCDay()]
  const dayNum = d.getUTCDate()

  return (
    <div
      className={cn(
        "flex min-h-[120px] flex-col rounded-md border border-border bg-card",
        isToday && "ring-1 ring-primary/40"
      )}
    >
      <div className={cn(
        "flex items-center justify-between px-2 py-1 border-b border-border",
        isToday && "bg-primary/5"
      )}>
        <span className="text-[10px] font-medium uppercase text-muted-foreground">
          {dayName}
        </span>
        <span className={cn(
          "text-xs font-semibold",
          isToday ? "text-primary" : "text-foreground"
        )}>
          {dayNum}
        </span>
      </div>
      <div className="flex flex-1 flex-col gap-1 p-1.5">
        {projects.map((p) => (
          <ProjectCard
            key={p.id}
            project={p}
            editorStatus={p.editorStatus}
            onScheduleChange={() => onScheduleChange()}
          />
        ))}
      </div>
      <div className="border-t border-border px-1.5 py-1">
        <Button
          variant="ghost"
          size="sm"
          className="h-5 w-full text-[10px] text-muted-foreground hover:text-foreground"
          onClick={onAddClick}
        >
          <Plus className="mr-1 h-3 w-3" />
          Adicionar
        </Button>
      </div>
    </div>
  )
}
