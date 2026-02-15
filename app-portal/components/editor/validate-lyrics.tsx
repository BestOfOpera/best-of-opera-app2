"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { editorApi, type Edicao } from "@/lib/api/editor"
import { usePolling } from "@/lib/hooks/use-polling"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Textarea } from "@/components/ui/textarea"
import { Badge } from "@/components/ui/badge"
import { ArrowLeft, Search, Check, RefreshCw, Loader2, ExternalLink, Upload } from "lucide-react"

export function EditorValidateLyrics({ edicaoId }: { edicaoId: number }) {
  const router = useRouter()
  const [edicao, setEdicao] = useState<Edicao | null>(null)
  const [letra, setLetra] = useState("")
  const [fonte, setFonte] = useState("")
  const [loading, setLoading] = useState(true)
  const [buscando, setBuscando] = useState(false)
  const [salvando, setSalvando] = useState(false)
  const [error, setError] = useState("")
  const [videoStatus, setVideoStatus] = useState<{ status: string; progresso?: number; video_completo?: boolean } | null>(null)
  const [uploading, setUploading] = useState(false)

  useEffect(() => {
    editorApi.obterEdicao(edicaoId).then(e => {
      setEdicao(e)
      if (e.eh_instrumental) {
        router.push(`/editor/edicao/${edicaoId}/conclusao`)
        return
      }
      setLoading(false)
      if (!e.arquivo_video_completo) {
        editorApi.garantirVideo(edicaoId).catch(() => {})
      }
    })
  }, [edicaoId, router])

  usePolling(
    async () => {
      const s = await editorApi.statusVideo(edicaoId).catch(() => null)
      if (s) setVideoStatus(s)
    },
    5000,
    !!edicao
  )

  const buscarLetra = async () => {
    setBuscando(true)
    setError("")
    try {
      const result = await editorApi.buscarLetra(edicaoId)
      setLetra(result.letra || "")
      setFonte(result.fonte || "desconhecida")
    } catch (err: unknown) {
      setError("Erro ao buscar letra: " + (err instanceof Error ? err.message : "Erro"))
    } finally {
      setBuscando(false)
    }
  }

  const aprovarLetra = async () => {
    if (!letra.trim()) return
    setSalvando(true)
    setError("")
    try {
      await editorApi.aprovarLetra(edicaoId, { letra })
      editorApi.iniciarTranscricao(edicaoId).catch(() => {})
      router.push(`/editor/edicao/${edicaoId}/alinhamento`)
    } catch (err: unknown) {
      setError("Erro ao salvar: " + (err instanceof Error ? err.message : "Erro"))
      setSalvando(false)
    }
  }

  if (loading || !edicao) return <div className="text-center py-16 text-muted-foreground">Carregando...</div>

  const videoReady = videoStatus?.video_completo
  const jaTemLetra = letra.trim().length > 0

  return (
    <div className="max-w-3xl mx-auto">
      <Button variant="ghost" size="sm" asChild className="mb-6 gap-2 text-muted-foreground">
        <Link href="/editor"><ArrowLeft className="h-4 w-4" /> Voltar à fila</Link>
      </Button>

      <div className="mb-6">
        <h2 className="text-2xl font-bold">{edicao.artista} — {edicao.musica}</h2>
        <p className="text-sm text-muted-foreground mt-1">
          {edicao.compositor} {edicao.opera ? `· ${edicao.opera}` : ""} · {edicao.idioma?.toUpperCase()}
          {edicao.youtube_url && (
            <a href={edicao.youtube_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 ml-3 text-primary hover:underline">
              <ExternalLink className="h-3 w-3" /> Abrir no YouTube
            </a>
          )}
        </p>
      </div>

      {/* Video status */}
      <div className={`flex items-center gap-2 text-xs px-3 py-2 rounded-lg mb-4 ${videoReady ? "bg-green-50 text-green-700" : edicao.erro_msg ? "bg-red-50 text-red-700" : "bg-blue-50 text-blue-700"}`}>
        {videoReady ? (
          <><Check className="h-3.5 w-3.5" /> Vídeo disponível</>
        ) : edicao.erro_msg ? (
          <><span className="font-bold">Erro no download:</span> {edicao.erro_msg}</>
        ) : uploading ? (
          <><Loader2 className="h-3.5 w-3.5 animate-spin" /> Enviando vídeo...</>
        ) : (
          <><Loader2 className="h-3.5 w-3.5 animate-spin" /> Baixando vídeo em background...</>
        )}
        {!videoReady && (
          <label className="ml-auto cursor-pointer flex items-center gap-1 bg-white border px-3 py-1 rounded text-muted-foreground hover:bg-muted/50 text-xs">
            <Upload className="h-3 w-3" />
            {uploading ? "Enviando..." : "Subir vídeo"}
            <input type="file" accept="video/*" className="hidden" disabled={uploading} onChange={async (ev) => {
              const file = ev.target.files?.[0]
              if (!file) return
              setUploading(true)
              setError("")
              try {
                await editorApi.uploadVideo(edicaoId, file)
                const e2 = await editorApi.obterEdicao(edicaoId)
                setEdicao(e2)
              } catch (err: unknown) {
                setError("Erro no upload: " + (err instanceof Error ? err.message : "Erro"))
              } finally {
                setUploading(false)
              }
            }} />
          </label>
        )}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Passo 2 — Validar Letra</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-2">
            <Button onClick={buscarLetra} disabled={buscando} className="gap-2">
              {buscando ? <RefreshCw className="h-3.5 w-3.5 animate-spin" /> : <Search className="h-3.5 w-3.5" />}
              {buscando ? "Buscando..." : jaTemLetra ? "Buscar Novamente" : "Buscar Letra"}
            </Button>
          </div>

          {fonte && (
            <div className="flex items-center gap-2 text-xs">
              <span className="text-muted-foreground">Fonte:</span>
              <Badge variant={fonte === "banco" ? "default" : fonte === "genius" ? "outline" : "secondary"}>
                {fonte === "banco" ? "Banco de dados" : fonte === "genius" ? "Genius" : fonte === "gemini" ? "Gemini (IA)" : fonte}
              </Badge>
              {fonte === "gemini" && <span className="text-yellow-600">— Verifique a letra antes de aprovar</span>}
            </div>
          )}

          {error && <div className="bg-destructive/10 text-destructive text-sm rounded-lg p-3">{error}</div>}

          <Textarea
            value={letra}
            onChange={e => { setLetra(e.target.value); if (!fonte) setFonte("manual") }}
            placeholder="Cole ou busque a letra original aqui..."
            className="font-mono min-h-[400px] resize-y"
          />

          <div className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground">{letra.split("\n").filter(l => l.trim()).length} versos</span>
            <Button onClick={aprovarLetra} disabled={salvando || !letra.trim()} className="gap-2">
              <Check className="h-4 w-4" />
              {salvando ? "Salvando..." : "Aprovar Letra e Continuar"}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
