"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { editorApi, type Edicao } from "@/lib/api/editor"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { ArrowLeft, Play, ExternalLink, Music, User, Globe, Loader2 } from "lucide-react"
import { getYoutubeUrl } from "@/lib/utils"

const STATUS_LABELS: Record<string, { label: string; variant: "default" | "secondary" | "destructive" | "outline" }> = {
  aguardando: { label: "Aguardando", variant: "secondary" },
  baixando: { label: "Baixando...", variant: "outline" },
  letra: { label: "Letra", variant: "outline" },
  transcricao: { label: "Transcrição", variant: "outline" },
  alinhamento: { label: "Alinhamento", variant: "outline" },
  corte: { label: "Corte", variant: "outline" },
  traducao: { label: "Tradução", variant: "outline" },
  montagem: { label: "Montagem", variant: "outline" },
  renderizando: { label: "Renderizando...", variant: "outline" },
  concluido: { label: "Concluído", variant: "default" },
  erro: { label: "Erro", variant: "destructive" },
}

const IDIOMA_LABELS: Record<string, string> = {
  it: "Italiano",
  en: "Inglês",
  de: "Alemão",
  fr: "Francês",
  es: "Espanhol",
  pt: "Português",
  ru: "Russo",
  cs: "Tcheco",
  la: "Latim",
  pl: "Polonês",
  hu: "Húngaro",
}

export function EditorOverview({ edicaoId }: { edicaoId: number }) {
  const router = useRouter()
  const [edicao, setEdicao] = useState<Edicao | null>(null)
  const [loading, setLoading] = useState(true)
  const [iniciando, setIniciando] = useState(false)

  useEffect(() => {
    editorApi.obterEdicao(edicaoId)
      .then(setEdicao)
      .finally(() => setLoading(false))
  }, [edicaoId])

  const handleIniciarPipeline = async () => {
    setIniciando(true)
    router.push(`/editor/edicao/${edicaoId}/letra`)
  }

  if (loading) {
    return (
      <div className="text-center py-16 text-muted-foreground">
        <Loader2 className="h-6 w-6 mx-auto mb-2 animate-spin" />
        Carregando...
      </div>
    )
  }

  if (!edicao) {
    return (
      <div className="text-center py-16 text-muted-foreground">
        Edição não encontrada.
      </div>
    )
  }

  const st = STATUS_LABELS[edicao.status] || STATUS_LABELS.aguardando
  const idiomaLabel = IDIOMA_LABELS[edicao.idioma] || edicao.idioma?.toUpperCase()

  return (
    <div className="max-w-2xl mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <Button variant="ghost" size="icon" asChild>
          <Link href="/editor">
            <ArrowLeft className="h-5 w-5" />
          </Link>
        </Button>
        <h1 className="text-2xl font-bold">Visão Geral da Edição</h1>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>{edicao.artista} — {edicao.musica}</span>
            <Badge variant={st.variant}>{st.label}</Badge>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="flex items-start gap-3">
              <User className="h-4 w-4 mt-0.5 text-muted-foreground shrink-0" />
              <div>
                <p className="text-xs text-muted-foreground">Artista</p>
                <p className="font-medium">{edicao.artista}</p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <Music className="h-4 w-4 mt-0.5 text-muted-foreground shrink-0" />
              <div>
                <p className="text-xs text-muted-foreground">Música</p>
                <p className="font-medium">{edicao.musica}</p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <Globe className="h-4 w-4 mt-0.5 text-muted-foreground shrink-0" />
              <div>
                <p className="text-xs text-muted-foreground">Idioma da Música</p>
                <p className="font-medium">{idiomaLabel}</p>
              </div>
            </div>

            {edicao.compositor && (
              <div className="flex items-start gap-3">
                <Music className="h-4 w-4 mt-0.5 text-muted-foreground shrink-0" />
                <div>
                  <p className="text-xs text-muted-foreground">Compositor</p>
                  <p className="font-medium">{edicao.compositor}</p>
                </div>
              </div>
            )}

            {edicao.opera && (
              <div className="flex items-start gap-3">
                <Music className="h-4 w-4 mt-0.5 text-muted-foreground shrink-0" />
                <div>
                  <p className="text-xs text-muted-foreground">Ópera</p>
                  <p className="font-medium">{edicao.opera}</p>
                </div>
              </div>
            )}
          </div>

          {getYoutubeUrl(edicao.youtube_url, edicao.youtube_video_id) && (
            <div className="pt-2 border-t">
              <p className="text-xs text-muted-foreground mb-1">YouTube</p>
              <a
                href={getYoutubeUrl(edicao.youtube_url, edicao.youtube_video_id)!}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 text-sm text-primary hover:underline"
              >
                <ExternalLink className="h-3.5 w-3.5" />
                {getYoutubeUrl(edicao.youtube_url, edicao.youtube_video_id)}
              </a>
            </div>
          )}

          <div className="pt-4 border-t">
            <Button
              onClick={handleIniciarPipeline}
              disabled={iniciando}
              className="w-full gap-2"
              size="lg"
            >
              {iniciando ? (
                <><Loader2 className="h-4 w-4 animate-spin" /> Iniciando...</>
              ) : (
                <><Play className="h-4 w-4" /> Iniciar Pipeline</>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
