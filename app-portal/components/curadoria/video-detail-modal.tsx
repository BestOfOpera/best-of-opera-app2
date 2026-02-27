"use client"

import type { Video } from "@/lib/api/curadoria"
import { curadoriaApi } from "@/lib/api/curadoria"
import { ScoreRing, scoreColorBg } from "./score-ring"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Download, ExternalLink, Loader2, CheckCircle2, ArrowRight, Cloud, CloudOff } from "lucide-react"
import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"

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
  const router = useRouter()
  const [downloading, setDownloading] = useState(false)
  const [preparing, setPreparing] = useState(false)
  const [downloadDone, setDownloadDone] = useState(false)
  const [r2Status, setR2Status] = useState<"ok" | "failed" | "unknown">("unknown")
  const [r2Key, setR2Key] = useState("")
  const [r2Cached, setR2Cached] = useState(false)
  const [editArtist, setEditArtist] = useState("")
  const [editSong, setEditSong] = useState("")

  // Reset fields when video changes or modal opens
  useEffect(() => {
    if (video && open) {
      setEditArtist(video.artist || "")
      setEditSong(video.song || video.title || "")
      setDownloadDone(false)
      setR2Status("unknown")
      setR2Key("")
      setR2Cached(false)
    }
  }, [video?.video_id, open])

  if (!video) return null

  const score = video.score?.total || 0
  const reasons = video.score?.reasons || []

  /** Apenas salva no R2 (sem download pro browser) — fluxo principal */
  const handlePrepare = async () => {
    const artist = editArtist.trim() || "Unknown"
    const song = editSong.trim() || "Video"
    setPreparing(true)
    try {
      const result = await curadoriaApi.prepareVideo(video.video_id, artist, song)
      setR2Status("ok")
      setR2Key(result.r2_key)
      setR2Cached(result.cached)
      setDownloadDone(true)
      onDownloaded?.()
    } catch (err) {
      alert("Falha ao preparar vídeo: " + (err instanceof Error ? err.message : "Erro"))
    } finally {
      setPreparing(false)
    }
  }

  /** Download pro browser + upload R2 (fluxo legado) */
  const handleDownload = async () => {
    const artist = editArtist.trim() || "Unknown"
    const song = editSong.trim() || "Video"
    setDownloading(true)
    try {
      const result = await curadoriaApi.downloadVideo(video.video_id, artist, song)
      setR2Status(result.r2Status as "ok" | "failed" | "unknown")
      setR2Key(result.r2Key)
      setDownloadDone(true)
      onDownloaded?.()
    } catch (err) {
      alert("Download falhou: " + (err instanceof Error ? err.message : "Erro"))
    } finally {
      setDownloading(false)
    }
  }

  const handleGoToRedator = () => {
    onClose()
    router.push("/redator")
  }

  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) { setDownloadDone(false); onClose() } }}>
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

        {/* Download/Prepare success state */}
        {downloadDone ? (
          <div className="space-y-4">
            <div className={`flex items-center gap-3 p-4 rounded-lg border ${
              r2Status === "ok"
                ? "bg-green-50 border-green-200"
                : "bg-amber-50 border-amber-200"
            }`}>
              {r2Status === "ok"
                ? <Cloud className="h-6 w-6 text-green-600 flex-shrink-0" />
                : <CloudOff className="h-6 w-6 text-amber-600 flex-shrink-0" />
              }
              <div>
                <div className={`font-semibold ${r2Status === "ok" ? "text-green-800" : "text-amber-800"}`}>
                  {r2Status === "ok"
                    ? (r2Cached ? "Video ja estava no R2" : "Video salvo e pronto para edicao")
                    : "Download concluido (upload R2 falhou)"
                  }
                </div>
                <div className={`text-sm ${r2Status === "ok" ? "text-green-700" : "text-amber-700"}`}>
                  {r2Status === "ok"
                    ? <><span className="font-mono text-xs">{r2Key}</span></>
                    : "O video foi baixado mas nao foi salvo na nuvem. Tente novamente."
                  }
                </div>
              </div>
            </div>

            <div className="flex gap-3 justify-end">
              <Button variant="outline" onClick={() => { setDownloadDone(false); onClose() }}>
                Fechar
              </Button>
              <Button onClick={handleGoToRedator} className="gap-2">
                Seguir para o Redator <ArrowRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        ) : (
          <>
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

            {/* Editable artist/song for R2 naming */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-[10px] text-muted-foreground uppercase">Artista</label>
                <input
                  value={editArtist}
                  onChange={e => setEditArtist(e.target.value)}
                  className="w-full bg-muted/50 rounded px-2 py-1.5 text-sm border focus:outline-none focus:ring-1 focus:ring-primary"
                  placeholder="Nome do artista"
                />
              </div>
              <div>
                <label className="text-[10px] text-muted-foreground uppercase">Musica / Aria</label>
                <input
                  value={editSong}
                  onChange={e => setEditSong(e.target.value)}
                  className="w-full bg-muted/50 rounded px-2 py-1.5 text-sm border focus:outline-none focus:ring-1 focus:ring-primary"
                  placeholder="Nome da musica"
                />
              </div>
            </div>

            {/* Actions */}
            <div className="flex gap-3 justify-end">
              <Button variant="outline" onClick={onClose}>Fechar</Button>
              <Button
                variant="outline"
                onClick={handleDownload}
                disabled={downloading || preparing || !editArtist.trim() || !editSong.trim()}
                className="gap-2"
              >
                {downloading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Download className="h-3.5 w-3.5" />}
                {downloading ? "Baixando..." : "Download local"}
              </Button>
              <Button
                onClick={handlePrepare}
                disabled={downloading || preparing || !editArtist.trim() || !editSong.trim()}
                className="gap-2"
              >
                {preparing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Cloud className="h-3.5 w-3.5" />}
                {preparing ? "Preparando..." : "Preparar para Edicao"}
              </Button>
            </div>
          </>
        )}
      </DialogContent>
    </Dialog>
  )
}
