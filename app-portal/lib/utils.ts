import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Normaliza youtube_url para evitar URL duplicada no href.
 * Se já é URL completa, retorna como está.
 * Se é apenas video_id, constrói a URL.
 */
export function getYoutubeUrl(youtubeUrl?: string | null, videoId?: string | null): string | null {
  const val = youtubeUrl?.trim()
  if (!val) {
    return videoId ? `https://www.youtube.com/watch?v=${videoId}` : null
  }
  if (val.startsWith("http://") || val.startsWith("https://")) {
    return val
  }
  // Valor sem protocolo — provavelmente é só o video_id
  return `https://www.youtube.com/watch?v=${val}`
}

export function extractErrorMessage(err: unknown): string {
  if (!err) return "Erro desconhecido"
  if (typeof err === "string") return err
  const anyErr = err as any
  const detail = anyErr.detail || anyErr.mensagem || anyErr.message
  if (typeof detail === "object" && detail !== null) {
    return JSON.stringify(detail)
  }
  return detail || "Falha na requisição"
}
