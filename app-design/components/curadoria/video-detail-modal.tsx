"use client"

import type { Video } from "@/lib/api/curadoria"
import { curadoriaApi } from "@/lib/api/curadoria"
import { ScoreRing, scoreColorBg } from "./score-ring"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Download, ExternalLink, Loader2 } from "lucide-react"
import { useState } from "react"

function formatViews(n: number) {
  if (n >= 1e6) return (n / 1e6).toFixed(1) + "M"
  if (n >= 1e3) return Math.round(n / 1e3) + "K"
  return String(n)
}

function formatDuration(s: number) {
  if (!s) return "--"
  const m = Math.floor(s / 60)
  const sec = Math.floor(s % 60)
  return `${m}:${String(sec).padStart(2, "0")}`
}

const TAG_COLORS: Record<string, string> = {
  elite_hit: "bg-green-100 text-green-700",
  power_name: "bg-purple-100 text-purple-700",
  specialty: "bg-blue-100 text-blue-700",
  voice: "bg-cyan-100 text-cyan-700",
  institutional: "bg-amber-100 text-amber-700",
  quality: "bg-teal-100 text-teal-700",
  views: "bg-orange-100 text-orange-700",
}

export function VideoDetailModal({
  video,
  open,
  onClose,
  onDownloaded,
}: {
  video: Video | null
  open: boolean
  onClose: () => void
  onDownloaded?: () => void
}) {
  const [downloading, setDownloading] = useState(false)

  if (!video) return null

  const score = video.score?.total || 0
  const reasons = video.score?.reasons || []

  const handleDownload = async () => {
    setDownloading(true)
    try {
      await curadoriaApi.downloadVideo(video.video_id, video.artist || "Unknown", video.song || video.title || "Video")
      onDownloaded?.()
    } catch (err) {
      alert("Download failed: " + (err instanceof Error ? err.message : "Erro"))
    } finally {
      setDownloading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) onClose() }}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-3">
            <span>{video.artist} — {video.song || video.title}</span>
            {video.posted && <Badge variant="secondary">Posted</Badge>}
          </DialogTitle>
          {video.url && (
            <a href={video.url} target="_blank" rel="noopener noreferrer" className="text-xs text-primary hover:underline inline-flex items-center gap-1">
              <ExternalLink className="h-3 w-3" /> Ver no YouTube
            </a>
          )}
        </DialogHeader>

        {/* Score ring + breakdown */}
        <div className="flex items-start gap-4">
          <ScoreRing score={score} size={54} />
          <div className="flex-1">
            <div className="text-sm font-semibold mb-2">Score Breakdown</div>
            {reasons.length > 0 ? (
              <div className="space-y-1">
                {reasons.map((r, i) => {
                  const { color } = scoreColorBg(r.points * 10)
                  return (
                    <div key={i} className="flex items-center gap-2 text-xs">
                      <span className={`px-1.5 py-0.5 rounded-full font-medium ${TAG_COLORS[r.tag] || "bg-gray-100 text-gray-600"}`}>
                        {r.tag}
                      </span>
                      <span className="flex-1 text-[#8B8680]">{r.label}</span>
                      <span className="font-bold" style={{ color }}>+{r.points}</span>
                    </div>
                  )
                })}
              </div>
            ) : (
              <div className="text-xs text-muted-foreground">Sem matches</div>
            )}
          </div>
        </div>

        {/* Stats grid */}
        <div className="grid grid-cols-3 gap-3 text-center">
          {[
            ["Views", formatViews(video.views)],
            ["Ano", video.year > 0 ? String(video.year) : "--"],
            ["Duração", formatDuration(video.duration)],
            ["HD", video.hd ? "Sim" : "Não"],
            ["Canal", video.channel || "--"],
            ["Cat.", video.category || "--"],
          ].map(([label, val]) => (
            <div key={label} className="bg-muted/50 rounded-lg p-2">
              <div className="text-[10px] text-muted-foreground uppercase">{label}</div>
              <div className="text-sm font-semibold truncate">{val}</div>
            </div>
          ))}
        </div>

        {/* YouTube URL */}
        {video.url && (
          <div>
            <div className="text-[10px] text-muted-foreground mb-1">YouTube URL</div>
            <div className="flex gap-2">
              <input
                value={video.url}
                readOnly
                onClick={e => (e.target as HTMLInputElement).select()}
                className="flex-1 bg-muted/50 rounded px-2 py-1 text-xs font-mono border"
              />
              <Button size="sm" variant="outline" asChild>
                <a href={video.url} target="_blank" rel="noopener noreferrer">Abrir</a>
              </Button>
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-3 justify-end">
          {!video.posted && (
            <Button onClick={handleDownload} disabled={downloading} className="gap-2">
              {downloading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Download className="h-3.5 w-3.5" />}
              {downloading ? "Downloading..." : "Download"}
            </Button>
          )}
          <Button variant="outline" onClick={onClose}>Fechar</Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
