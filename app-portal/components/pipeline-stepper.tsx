import { cn } from "@/lib/utils"
import { Check } from "lucide-react"

const pipelineSteps = ["Download", "Letras", "Transcricao", "Alinhamento", "Corte", "Traducao", "Preview", "Render", "Exportar"]

interface PipelineStepperProps { currentStep: number; className?: string }

export function PipelineStepper({ currentStep, className }: PipelineStepperProps) {
  return (
    <div className={cn("flex items-center", className)}>
      {pipelineSteps.map((step, i) => {
        const stepNum = i + 1
        const isComplete = stepNum < currentStep
        const isCurrent = stepNum === currentStep
        return (
          <div key={step} className="flex items-center">
            <div className="flex flex-col items-center">
              <div className={cn("flex h-6 w-6 items-center justify-center rounded-full text-[10px] font-semibold transition-colors", isComplete && "bg-emerald-100 text-emerald-700", isCurrent && "bg-primary text-primary-foreground", !isComplete && !isCurrent && "bg-muted text-muted-foreground")}>
                {isComplete ? <Check className="h-3 w-3" /> : stepNum}
              </div>
              <span className={cn("mt-1 text-[9px] font-medium whitespace-nowrap", isCurrent ? "text-primary" : "text-muted-foreground")}>{step}</span>
            </div>
            {i < pipelineSteps.length - 1 && <div className={cn("mx-0.5 h-px w-5", isComplete ? "bg-emerald-300" : "bg-border")} />}
          </div>
        )
      })}
    </div>
  )
}
