import { type Project } from "@/lib/api/redator"

export const RECENT_THRESHOLD_MS = 3 * 60 * 60 * 1000 // 3 horas

export const RECENT_CLASSES =
  "ring-2 ring-green-400/50 bg-green-50/30 dark:bg-green-950/20"

export function isRecentProject(created_at: string): boolean {
  return Date.now() - new Date(created_at).getTime() < RECENT_THRESHOLD_MS
}

export function nextStepLink(p: Project): string {
  // Projeto incompleto (criado pelo calendário sem dados completos)
  if (p.status === "input_complete" && !p.category) {
    return "/redator"
  }
  const isRC = p.brand_slug === "reels-classics"
  if (p.status === "input_complete" || p.status === "generating") {
    return isRC ? `/redator/projeto/${p.id}/hooks` : `/redator/projeto/${p.id}/overlay`
  }
  if (!p.overlay_approved) return `/redator/projeto/${p.id}/overlay`
  if (!p.post_approved) return `/redator/projeto/${p.id}/post`
  if (!isRC && !p.youtube_approved) return `/redator/projeto/${p.id}/youtube`
  if (isRC && !p.automation_approved) return `/redator/projeto/${p.id}/automation`
  return `/redator/projeto/${p.id}/exportar`
}
