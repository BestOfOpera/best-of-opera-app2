"use client"

import { useState } from "react"
import { MoreVertical, CalendarX, CalendarPlus } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { redatorApi } from "@/lib/api/redator"
import { toast } from "sonner"

interface ScheduleDropdownProps {
  projectId: number
  onScheduleChange: (newDate: string | null) => void
}

export function ScheduleDropdown({ projectId, onScheduleChange }: ScheduleDropdownProps) {
  const [showDateInput, setShowDateInput] = useState(false)

  async function handleReschedule(dateStr: string) {
    try {
      await redatorApi.scheduleProject(projectId, dateStr)
      toast.success("Projeto reagendado")
      onScheduleChange(dateStr)
    } catch {
      toast.error("Erro ao reagendar projeto")
    }
    setShowDateInput(false)
  }

  async function handleUnschedule() {
    try {
      await redatorApi.scheduleProject(projectId, null)
      toast.success("Projeto removido do calendario")
      onScheduleChange(null)
    } catch {
      toast.error("Erro ao remover projeto do calendario")
    }
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" className="h-5 w-5 shrink-0" onClick={(e) => e.stopPropagation()}>
          <MoreVertical className="h-3 w-3" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" onClick={(e) => e.stopPropagation()}>
        {showDateInput ? (
          <div className="p-2">
            <input
              type="date"
              autoFocus
              className="rounded border border-border bg-background px-2 py-1 text-sm"
              onChange={(e) => {
                if (e.target.value) handleReschedule(e.target.value)
              }}
              onBlur={() => setShowDateInput(false)}
            />
          </div>
        ) : (
          <DropdownMenuItem onClick={() => setShowDateInput(true)}>
            <CalendarPlus className="mr-2 h-3.5 w-3.5" />
            Reagendar
          </DropdownMenuItem>
        )}
        <DropdownMenuItem onClick={handleUnschedule} className="text-destructive">
          <CalendarX className="mr-2 h-3.5 w-3.5" />
          Remover do calendario
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
