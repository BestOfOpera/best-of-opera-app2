"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { curadoriaApi, type Download } from "@/lib/api/curadoria"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ArrowLeft, Download as DownloadIcon, ExternalLink, FileSpreadsheet } from "lucide-react"

export function CuradoriaDownloads() {
  const [downloads, setDownloads] = useState<Download[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    curadoriaApi.downloads()
      .then(data => setDownloads(data.downloads || []))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="text-center py-16 text-muted-foreground">Carregando...</div>

  return (
    <div className="max-w-3xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" asChild className="gap-2 text-muted-foreground">
            <Link href="/curadoria"><ArrowLeft className="h-4 w-4" /> Voltar</Link>
          </Button>
          <h2 className="text-2xl font-bold">Downloads ({downloads.length})</h2>
        </div>
        {downloads.length > 0 && (
          <Button variant="outline" size="sm" asChild className="gap-2">
            <a href={curadoriaApi.downloadsExportUrl()} download>
              <FileSpreadsheet className="h-4 w-4" /> Export CSV
            </a>
          </Button>
        )}
      </div>

      {downloads.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground">
          <DownloadIcon className="h-12 w-12 mx-auto mb-4 opacity-50" />
          <p>Nenhum download ainda</p>
        </div>
      ) : (
        <Card>
          <CardContent className="p-0">
            <div className="divide-y">
              {downloads.map((d, i) => {
                const date = d.downloaded_at ? new Date(d.downloaded_at).toLocaleDateString("pt-BR") : "--"
                return (
                  <div key={i} className="flex items-center gap-3 px-4 py-3 hover:bg-muted/50 transition">
                    <DownloadIcon className="h-4 w-4 text-muted-foreground shrink-0" />
                    <span className="flex-1 text-sm font-medium truncate">{d.filename || d.video_id}</span>
                    <span className="text-xs text-muted-foreground">{date}</span>
                    {d.youtube_url && (
                      <a href={d.youtube_url} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline text-xs inline-flex items-center gap-1">
                        <ExternalLink className="h-3 w-3" /> YT
                      </a>
                    )}
                  </div>
                )
              })}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
