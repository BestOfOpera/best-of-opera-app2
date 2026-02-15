import { cn } from "@/lib/utils"

type StatusType = "input_complete" | "generating" | "awaiting_approval" | "translating" | "export_ready" | "success" | "error" | "in_progress" | "pending" | "downloaded" | "posted"

const statusConfig: Record<StatusType, { label: string; dot: string; text: string }> = {
  input_complete: { label: "Input Completo", dot: "bg-blue-400", text: "text-blue-700" },
  generating: { label: "Gerando", dot: "bg-purple-400", text: "text-purple-700" },
  awaiting_approval: { label: "Aguardando Aprovacao", dot: "bg-amber-400", text: "text-amber-700" },
  translating: { label: "Traduzindo", dot: "bg-cyan-400", text: "text-cyan-700" },
  export_ready: { label: "Pronto p/ Exportar", dot: "bg-emerald-400", text: "text-emerald-700" },
  success: { label: "Concluido", dot: "bg-emerald-400", text: "text-emerald-700" },
  error: { label: "Erro", dot: "bg-red-400", text: "text-red-700" },
  in_progress: { label: "Em Andamento", dot: "bg-amber-400", text: "text-amber-700" },
  pending: { label: "Pendente", dot: "bg-gray-300", text: "text-gray-500" },
  downloaded: { label: "Baixado", dot: "bg-blue-400", text: "text-blue-700" },
  posted: { label: "Publicado", dot: "bg-emerald-400", text: "text-emerald-700" },
}

interface StatusBadgeProps { status: StatusType; className?: string }

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const config = statusConfig[status]
  return (
    <span className={cn("inline-flex items-center gap-1.5 text-xs font-medium", config.text, className)}>
      <span className={cn("h-1.5 w-1.5 rounded-full", config.dot)} />
      {config.label}
    </span>
  )
}
