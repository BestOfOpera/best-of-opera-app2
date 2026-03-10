"use client"

import { useMemo } from "react"
import { cn } from "@/lib/utils"
import { Check, X, Loader2, PlayCircle, HardDrive, Download, Music, Edit3 } from "lucide-react"

export type StepStatus = "pending" | "in-progress" | "completed" | "error" | "action-required"

export interface PhaseGroup {
  id: string
  title: string
  description?: string
  status: StepStatus
  icon: React.ElementType
  subStatus?: string
  errorMsg?: string
}

interface PipelineStepperProps {
  currentStepIndex: number
  totalSteps?: number
  errorMsg?: string
  isVerticalMobile?: boolean
  customPhases?: PhaseGroup[]
}

export function PipelineStepper({
  currentStepIndex,
  errorMsg,
  isVerticalMobile = true,
  customPhases
}: PipelineStepperProps) {

  // Map 9 steps into 5 Phase Groups for the UI if customPhases not provided
  const phases: PhaseGroup[] = useMemo(() => {
    if (customPhases) return customPhases

    // Default Best of Opera mapping:
    // 0: URL recebida -> 1: Importacao
    // 1-3: IA Metadados/Recortes/Validacao -> 2: Analise IA
    // 4-5: Fonte Isolada / Instrumental -> 3: Processamento Audio
    // 6-7: Traducao Letras / Rendering -> 4: Geracao Video
    // 8: Publicacao -> 5: Embalagem

    return [
      {
        id: "import",
        title: "Importação",
        description: "Baixando da fonte original",
        icon: Download,
        status: currentStepIndex > 0 ? "completed" : errorMsg ? "error" : "in-progress"
      },
      {
        id: "ai_analysis",
        title: "Análise IA",
        description: "Metadados e recortes",
        icon: HardDrive,
        status: currentStepIndex > 3 ? "completed" : currentStepIndex >= 1 ? (errorMsg ? "error" : "in-progress") : "pending"
      },
      {
        id: "audio",
        title: "Processamento Áudio",
        description: "Isolamento de vozes e BG",
        icon: Music,
        status: currentStepIndex > 5 ? "completed" : currentStepIndex >= 4 ? (errorMsg ? "error" : "in-progress") : "pending"
      },
      {
        id: "generate",
        title: "Geração",
        description: "Traduções e Renders ML",
        icon: Edit3,
        status: currentStepIndex > 7 ? "completed" : currentStepIndex >= 6 ? (errorMsg ? "error" : "in-progress") : "pending"
      },
      {
        id: "pack",
        title: "Exportação",
        description: "Zip e R2 upload",
        icon: PlayCircle,
        status: currentStepIndex >= 8 ? "completed" : currentStepIndex === 8 ? (errorMsg ? "error" : "in-progress") : "pending"
      }
    ]
  }, [currentStepIndex, errorMsg, customPhases])

  const renderIcon = (phase: PhaseGroup) => {
    switch (phase.status) {
      case "completed":
        return <Check className="h-4 w-4 text-green-600" />
      case "error":
        return <X className="h-4 w-4 text-red-600" />
      case "in-progress":
        return <Loader2 className="h-4 w-4 animate-spin text-blue-600" />
      case "action-required":
        return <AlertCircle className="h-4 w-4 text-amber-500" />
      default:
        const Icon = phase.icon
        return <Icon className="h-4 w-4 text-muted-foreground" />
    }
  }

  const getContainerStyles = (status: StepStatus) => {
    switch (status) {
      case "completed": return "bg-green-100 border-green-200"
      case "error": return "bg-red-100 border-red-200 ring-2 ring-red-500/20"
      case "in-progress": return "bg-blue-50 border-blue-200 ring-2 ring-blue-500/30 shadow-sm"
      case "action-required": return "bg-amber-50 border-amber-200 ring-2 ring-amber-500/20"
      default: return "bg-muted border-border"
    }
  }

  // Adjusted the line styles properly returning full component
  const getLineStyles = (status: StepStatus) => {
    if (status === "completed") return "bg-green-500"
    if (status === "in-progress" || status === "error") return "bg-border" // Has not finished this node
    return "bg-muted"
  }

  return (
    <div className={cn("w-full py-2", isVerticalMobile ? "flex flex-col sm:flex-row" : "flex flex-row items-center justify-between")}>
      {phases.map((phase, i) => {
        const isLast = i === phases.length - 1

        return (
          <div key={phase.id} className={cn("relative flex", isVerticalMobile ? "flex-col sm:flex-row sm:flex-1 items-start sm:items-center" : "flex-1 items-center")}>

            {/* The Item */}
            <div className={cn("relative z-10 flex items-center gap-3", isVerticalMobile ? "mb-6 sm:mb-0" : "")}>
              <div
                className={cn(
                  "flex h-9 w-9 shrink-0 items-center justify-center rounded-full border-2 transition-all duration-300",
                  getContainerStyles(phase.status),
                  phase.status === "in-progress" && "scale-110"
                )}
              >
                {renderIcon(phase)}
              </div>

              <div className={cn("flex flex-col", isVerticalMobile ? "sm:absolute sm:top-11 sm:-ml-10 sm:w-32 sm:text-center" : "")}>
                <span className={cn(
                  "text-sm font-semibold",
                  phase.status === "error" ? "text-red-700" : phase.status === "in-progress" ? "text-blue-700" : phase.status === "pending" ? "text-muted-foreground" : "text-foreground"
                )}>
                  {phase.title}
                </span>
                {(phase.description || phase.errorMsg) && (
                  <span className={cn("text-[10px] mt-0.5 max-w-[120px]", phase.status === "error" ? "text-red-500 line-clamp-2" : "text-muted-foreground hidden sm:block")}>
                    {phase.errorMsg || phase.description}
                  </span>
                )}
              </div>
            </div>

            {/* The Line (Connection) */}
            {!isLast && (
              <div
                className={cn(
                  "transition-all duration-500",
                  isVerticalMobile
                    ? "absolute left-[17px] top-9 h-[calc(100%+8px)] w-0.5 sm:static sm:h-0.5 sm:w-full sm:flex-1 sm:mx-4"
                    : "h-0.5 flex-1 mx-4",
                  getLineStyles(phase.status)
                )}
              />
            )}
          </div>
        )
      })}
    </div>
  )
}

function AlertCircle(props: any) {
  return (
    <svg
      {...props}
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="8" x2="12" y2="12" />
      <line x1="12" y1="16" x2="12.01" y2="16" />
    </svg>
  )
}
