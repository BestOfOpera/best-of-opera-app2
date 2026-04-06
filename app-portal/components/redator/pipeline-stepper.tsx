"use client"

import { usePathname, useRouter } from "next/navigation"
import { Check } from "lucide-react"
import { cn } from "@/lib/utils"
import type { Project } from "@/lib/api/redator"

interface Step {
  id: string
  label: string
  href: string
  isComplete: boolean
}

interface PipelineStepperProps {
  projectId: number
  project: Project
}

function getStepsBO(project: Project, projectId: number): Step[] {
  return [
    {
      id: "overlay",
      label: "Overlay",
      href: `/redator/projeto/${projectId}/overlay`,
      isComplete: project.overlay_json != null,
    },
    {
      id: "post",
      label: "Post",
      href: `/redator/projeto/${projectId}/post`,
      isComplete: project.post_text != null,
    },
    {
      id: "youtube",
      label: "YouTube",
      href: `/redator/projeto/${projectId}/youtube`,
      isComplete: project.youtube_title != null,
    },
    {
      id: "exportar",
      label: "Exportar",
      href: `/redator/projeto/${projectId}/exportar`,
      isComplete: project.status === "export_ready",
    },
  ]
}

function getStepsRC(project: Project, projectId: number): Step[] {
  return [
    {
      id: "hooks",
      label: "Hooks",
      href: `/redator/projeto/${projectId}/hooks`,
      isComplete: project.selected_hook != null,
    },
    {
      id: "overlay",
      label: "Overlay",
      href: `/redator/projeto/${projectId}/overlay`,
      isComplete: project.overlay_json != null,
    },
    {
      id: "post",
      label: "Post",
      href: `/redator/projeto/${projectId}/post`,
      isComplete: project.post_text != null,
    },
    {
      id: "automation",
      label: "Automacao",
      href: `/redator/projeto/${projectId}/automation`,
      isComplete: project.automation_json != null,
    },
    {
      id: "youtube",
      label: "YouTube",
      href: `/redator/projeto/${projectId}/youtube`,
      isComplete: project.youtube_title != null,
    },
    {
      id: "exportar",
      label: "Exportar",
      href: `/redator/projeto/${projectId}/exportar`,
      isComplete: project.status === "export_ready",
    },
  ]
}

export function PipelineStepper({ projectId, project }: PipelineStepperProps) {
  const pathname = usePathname()
  const router = useRouter()

  const isRC = project.brand_slug === "reels-classics"
  const steps = isRC ? getStepsRC(project, projectId) : getStepsBO(project, projectId)

  const currentStepIndex = steps.findIndex((step) => pathname.endsWith(`/${step.id}`))

  return (
    <div className="mx-auto max-w-3xl mb-6">
      <div className="flex items-center justify-between mb-3">
        <div className="min-w-0">
          <h2 className="text-lg font-semibold truncate">{project.artist} — {project.work}</h2>
          <p className="text-xs text-muted-foreground">
            {isRC ? "Reels Classics" : "Best of Opera"}
          </p>
        </div>
      </div>

      <div className="flex items-center">
        {steps.map((step, index) => {
          const isCurrent = index === currentStepIndex
          const isComplete = step.isComplete
          const isClickable = isComplete || index <= currentStepIndex

          return (
            <div key={step.id} className="flex items-center flex-1 last:flex-initial">
              <button
                type="button"
                disabled={!isClickable}
                onClick={() => router.push(step.href)}
                className={cn(
                  "flex flex-col items-center gap-1 transition-colors",
                  isClickable ? "cursor-pointer" : "cursor-not-allowed opacity-40"
                )}
              >
                <div
                  className={cn(
                    "h-8 w-8 rounded-full flex items-center justify-center text-xs font-medium border-2 transition-colors",
                    isComplete && "bg-green-500 border-green-500 text-white",
                    isCurrent && !isComplete && "bg-primary border-primary text-primary-foreground",
                    !isCurrent && !isComplete && "bg-background border-muted-foreground/30 text-muted-foreground"
                  )}
                >
                  {isComplete ? <Check className="h-4 w-4" /> : <span>{index + 1}</span>}
                </div>
                <span
                  className={cn(
                    "text-[11px] font-medium whitespace-nowrap",
                    isCurrent && "text-primary",
                    isComplete && "text-green-600 dark:text-green-400",
                    !isCurrent && !isComplete && "text-muted-foreground"
                  )}
                >
                  {step.label}
                </span>
              </button>

              {index < steps.length - 1 && (
                <div
                  className={cn(
                    "flex-1 h-0.5 mx-2 self-start mt-4",
                    step.isComplete ? "bg-green-500" : "bg-muted-foreground/20"
                  )}
                />
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
