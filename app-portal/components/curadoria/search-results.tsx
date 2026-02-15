"use client"

import { useState } from "react"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { ScoreRing } from "@/components/score-ring"
import { StatusBadge } from "@/components/status-badge"
import { Search, Download, Eye, EyeOff, Filter } from "lucide-react"

const mockResults = [
  { id: 1, videoId: "abc123", title: "Nessun Dorma - Three Tenors 1994", artist: "Luciano Pavarotti", song: "Nessun Dorma", channel: "Decca Records", views: 45200000, year: 2008, duration: 214, score: 92, hd: true, posted: false, thumbnail: "" },
  { id: 2, videoId: "def456", title: "Maria Callas - Casta Diva (Norma)", artist: "Maria Callas", song: "Casta Diva", channel: "Warner Classics", views: 12800000, year: 2012, duration: 342, score: 88, hd: true, posted: true, thumbnail: "" },
  { id: 3, videoId: "ghi789", title: "Anna Netrebko - O mio babbino caro", artist: "Anna Netrebko", song: "O mio babbino caro", channel: "Deutsche Grammophon", views: 6200000, year: 2018, duration: 178, score: 85, hd: true, posted: false, thumbnail: "" },
  { id: 4, videoId: "jkl012", title: "Jonas Kaufmann - E lucevan le stelle", artist: "Jonas Kaufmann", song: "E lucevan le stelle", channel: "Sony Classical", views: 4100000, year: 2016, duration: 198, score: 79, hd: true, posted: false, thumbnail: "" },
  { id: 5, videoId: "mno345", title: "Placido Domingo - La donna e mobile", artist: "Placido Domingo", song: "La donna e mobile", channel: "EMI Classics", views: 8500000, year: 2015, duration: 156, score: 75, hd: false, posted: false, thumbnail: "" },
  { id: 6, videoId: "pqr678", title: "Renee Fleming - O mio babbino caro", artist: "Renee Fleming", song: "O mio babbino caro", channel: "PBS", views: 3200000, year: 2010, duration: 185, score: 71, hd: true, posted: true, thumbnail: "" },
]

function formatViews(n: number) { return n >= 1e6 ? (n / 1e6).toFixed(1) + "M" : n >= 1e3 ? Math.round(n / 1e3) + "K" : String(n) }
function formatDuration(s: number) { const m = Math.floor(s / 60); const sec = s % 60; return `${m}:${String(sec).padStart(2, "0")}` }

export function CuradoriaSearchResults() {
  const [hidePosted, setHidePosted] = useState(true)
  const filtered = hidePosted ? mockResults.filter((r) => !r.posted) : mockResults

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-foreground">Resultados</h1>
          <p className="text-sm text-muted-foreground">{filtered.length} videos encontrados</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input placeholder="Filtrar resultados..." className="w-64 pl-9" />
          </div>
          <Button variant="outline" size="sm" onClick={() => setHidePosted(!hidePosted)}>
            {hidePosted ? <Eye className="mr-2 h-3.5 w-3.5" /> : <EyeOff className="mr-2 h-3.5 w-3.5" />}
            {hidePosted ? "Mostrar Publicados" : "Ocultar Publicados"}
          </Button>
          <Button variant="outline" size="sm">
            <Filter className="mr-2 h-3.5 w-3.5" />
            Filtros
          </Button>
        </div>
      </div>

      <div className="space-y-2">
        {filtered.map((video) => (
          <Card key={video.id} className="transition-colors hover:bg-muted/20">
            <CardContent className="flex items-center gap-4 p-4">
              <ScoreRing score={video.score} size={48} />
              <div className="flex h-14 w-24 items-center justify-center rounded bg-muted text-xs text-muted-foreground">
                Thumbnail
              </div>
              <div className="flex-1 min-w-0">
                <p className="truncate text-sm font-medium text-foreground">{video.artist} — {video.song}</p>
                <p className="truncate text-xs text-muted-foreground">{video.channel}</p>
                <div className="mt-1.5 flex items-center gap-3 text-[11px] text-muted-foreground">
                  <span>{formatViews(video.views)} views</span>
                  <span>{formatDuration(video.duration)}</span>
                  <span>{video.year}</span>
                  {video.hd && <span className="rounded bg-blue-50 px-1.5 py-0.5 text-[9px] font-semibold text-blue-600">HD</span>}
                  {video.posted && <StatusBadge status="posted" />}
                </div>
              </div>
              <Button variant="outline" size="sm">
                <Download className="mr-2 h-3.5 w-3.5" />
                Baixar
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
