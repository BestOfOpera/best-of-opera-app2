"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { editorApi, type Edicao, type Render } from "@/lib/api/editor"
import { usePolling } from "@/lib/hooks/use-polling"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import {
  ArrowLeft, Download, Play, RefreshCw, CheckCircle, XCircle,
  ExternalLink, Pencil, RotateCcw, Eye, MessageSquare,
} from "lucide-react"

const IDIOMAS = [
  { code: "en", flag: "🇬🇧", label: "Inglês" },
  { code: "pt", flag: "🇧🇷", label: "Português" },
  { code: "es", flag: "🇪🇸", label: "Espanhol" },
  { code: "de", flag: "🇩🇪", label: "Alemão" },
  { code: "fr", flag: "🇫🇷", label: "Francês" },
  { code: "it", flag: "🇮🇹", label: "Italiano" },
  { code: "pl", flag: "🇵🇱", label: "Polonês" },
]

function formatBytes(bytes: number | null | undefined) {
  if (!bytes) return "--"
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatSec(sec: number | null | undefined) {
  if (!sec && sec !== 0) return "--:--"
  const m = Math.floor(sec / 60)
  const s = Math.floor(sec % 60)
  return `${m}:${String(s).padStart(2, "0")}`
}

export function EditorConclusion({ edicaoId }: { edicaoId: number }) {
  const router = useRouter()
  const [edicao, setEdicao] = useState<Edicao | null>(null)
  const [renders, setRenders] = useState<Render[]>([])
  const [loading, setLoading] = useState(true)
  const [renderizando, setRenderizando] = useState(false)
  const [traduzindo, setTraduzindo] = useState(false)
  const [exportando, setExportando] = useState(false)
  const [exportResult, setExportResult] = useState<{ pasta: string; arquivos_exportados: number } | null>(null)
  const [error, setError] = useState("")
  const [editandoCorte, setEditandoCorte] = useState(false)
  const [corteInicio, setCorteInicio] = useState("")
  const [corteFim, setCorteFim] = useState("")
  const [reaplicando, setReaplicando] = useState(false)
  const [notasRevisao, setNotasRevisao] = useState("")
  const [mostrarRevisao, setMostrarRevisao] = useState(false)
  const [aprovando, setAprovando] = useState(false)

  const load = async () => {
    try {
      const e = await editorApi.obterEdicao(edicaoId)
      setEdicao(e)
      const r = await editorApi.listarRenders(edicaoId)
      setRenders(r)
    } catch (err: unknown) {
      setError("Erro ao carregar dados: " + (err instanceof Error ? err.message : "Erro"))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [edicaoId])

  usePolling(load, 5000, !!edicao && ["renderizando", "traducao", "preview"].includes(edicao.status))

  const handleTraduzir = async () => {
    setTraduzindo(true)
    setError("")
    try {
      await editorApi.traduzirLyrics(edicaoId)
      await load()
    } catch (err: unknown) {
      setError("Erro na tradução: " + (err instanceof Error ? err.message : "Erro"))
    } finally {
      setTraduzindo(false)
    }
  }

  const handleRenderizarPreview = async () => {
    setRenderizando(true)
    setError("")
    try {
      await editorApi.renderizarPreview(edicaoId)
      await load()
    } catch (err: unknown) {
      setError("Erro na renderização: " + (err instanceof Error ? err.message : "Erro"))
    } finally {
      setRenderizando(false)
    }
  }

  const handleAprovarPreview = async () => {
    setAprovando(true)
    setError("")
    try {
      await editorApi.aprovarPreview(edicaoId, { aprovado: true })
      await load()
    } catch (err: unknown) {
      setError("Erro ao aprovar: " + (err instanceof Error ? err.message : "Erro"))
    } finally {
      setAprovando(false)
    }
  }

  const handleSolicitarRevisao = async () => {
    setAprovando(true)
    setError("")
    try {
      await editorApi.aprovarPreview(edicaoId, { aprovado: false, notas: notasRevisao })
      setMostrarRevisao(false)
      setNotasRevisao("")
      await load()
    } catch (err: unknown) {
      setError("Erro ao solicitar revisão: " + (err instanceof Error ? err.message : "Erro"))
    } finally {
      setAprovando(false)
    }
  }

  const handleRenderizarTodos = async () => {
    setRenderizando(true)
    setError("")
    try {
      await editorApi.renderizar(edicaoId)
      await load()
    } catch (err: unknown) {
      setError("Erro na renderização: " + (err instanceof Error ? err.message : "Erro"))
    } finally {
      setRenderizando(false)
    }
  }

  const handleExportar = async () => {
    setExportando(true)
    setError("")
    setExportResult(null)
    try {
      const result = await editorApi.exportarRenders(edicaoId)
      setExportResult(result)
    } catch (err: unknown) {
      setError("Erro ao exportar: " + (err instanceof Error ? err.message : "Erro"))
    } finally {
      setExportando(false)
    }
  }

  const parseMMSS = (val: string) => {
    const parts = val.split(":")
    if (parts.length === 2) return parseFloat(parts[0]) * 60 + parseFloat(parts[1])
    return parseFloat(val) || 0
  }

  const handleReaplicarCorte = async (params?: Record<string, number>) => {
    setReaplicando(true)
    setError("")
    try {
      await editorApi.aplicarCorte(edicaoId, params)
      await load()
      setEditandoCorte(false)
    } catch (err: unknown) {
      setError("Erro ao reaplicar corte: " + (err instanceof Error ? err.message : "Erro"))
    } finally {
      setReaplicando(false)
    }
  }

  if (loading || !edicao) return <div className="text-center py-16 text-muted-foreground">Carregando...</div>

  const concluidos = renders.filter(r => r.status === "concluido")
  const erros = renders.filter(r => r.status === "erro")
  const todosOk = concluidos.length === 7 && erros.length === 0
  const isConcluido = edicao.status === "concluido"
  const isPreviewPronto = edicao.status === "preview_pronto"
  const isPreview = edicao.status === "preview"
  const isRevisao = edicao.status === "revisao"

  const previewRender = renders.find(r => r.idioma === edicao.idioma && r.status === "concluido")

  return (
    <div className="max-w-4xl mx-auto">
      <Button variant="ghost" size="sm" asChild className="mb-6 gap-2 text-muted-foreground">
        <Link href="/editor"><ArrowLeft className="h-4 w-4" /> Voltar à fila</Link>
      </Button>

      {/* Header */}
      {isConcluido && todosOk ? (
        <div className="bg-green-50 border border-green-200 rounded-xl p-6 mb-6 text-center">
          <CheckCircle className="h-12 w-12 mx-auto mb-3 text-green-500" />
          <h2 className="text-2xl font-bold text-green-800">{edicao.artista} — {edicao.musica}</h2>
          <p className="text-green-600 mt-1">Edição concluída com sucesso! {concluidos.length} vídeos renderizados.</p>
        </div>
      ) : (
        <div className="mb-6">
          <h2 className="text-2xl font-bold">{edicao.artista} — {edicao.musica}</h2>
          <p className="text-sm text-muted-foreground mt-1">
            Conclusão
            {edicao.youtube_url && (
              <a href={edicao.youtube_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 ml-3 text-primary hover:underline">
                <ExternalLink className="h-3 w-3" /> YouTube
              </a>
            )}
          </p>
        </div>
      )}

      {error && <div className="bg-destructive/10 text-destructive text-sm rounded-lg p-3 mb-4">{error}</div>}

      {/* Revision card */}
      {isRevisao && edicao.notas_revisao && (
        <div className="bg-yellow-50 border border-yellow-300 rounded-xl p-5 mb-6">
          <div className="flex items-start gap-3">
            <MessageSquare className="h-5 w-5 text-yellow-600 mt-0.5" />
            <div className="flex-1">
              <h3 className="font-semibold text-yellow-800 mb-1">Revisão Solicitada</h3>
              <p className="text-sm text-yellow-700 whitespace-pre-wrap">{edicao.notas_revisao}</p>
              <Button
                variant="outline"
                size="sm"
                className="mt-3 gap-2"
                onClick={() => router.push(`/editor/edicao/${edicaoId}/alinhamento`)}
              >
                <ArrowLeft className="h-3.5 w-3.5" />
                Voltar ao Alinhamento
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Preview player + approval */}
      {isPreviewPronto && previewRender && (
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-6 mb-6">
          <h3 className="font-semibold text-blue-800 mb-3 flex items-center gap-2">
            <Eye className="h-4 w-4" /> Preview — {edicao.idioma.toUpperCase()}
          </h3>
          <video
            src={editorApi.downloadRenderUrl(edicaoId, previewRender.id)}
            controls
            className="w-full max-w-md mx-auto rounded-lg shadow-md mb-4"
            style={{ maxHeight: "500px" }}
          />
          <div className="flex gap-3 justify-center flex-wrap">
            <Button onClick={handleAprovarPreview} disabled={aprovando} className="gap-2">
              {aprovando ? <RefreshCw className="h-3.5 w-3.5 animate-spin" /> : <CheckCircle className="h-3.5 w-3.5" />}
              Aprovar e Renderizar Todos
            </Button>
            <Button variant="outline" onClick={() => setMostrarRevisao(!mostrarRevisao)} className="gap-2 border-yellow-400 text-yellow-700 hover:bg-yellow-50">
              <MessageSquare className="h-3.5 w-3.5" />
              Solicitar Revisão
            </Button>
          </div>
          {mostrarRevisao && (
            <div className="mt-4 max-w-md mx-auto">
              <Textarea
                value={notasRevisao}
                onChange={e => setNotasRevisao(e.target.value)}
                placeholder="Descreva o que precisa ser ajustado..."
                rows={3}
              />
              <Button
                onClick={handleSolicitarRevisao}
                disabled={aprovando || !notasRevisao.trim()}
                className="mt-2 w-full"
                variant="outline"
              >
                {aprovando ? "Enviando..." : "Enviar Revisão"}
              </Button>
            </div>
          )}
        </div>
      )}

      {/* Summary cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <Card>
          <CardContent className="p-4">
            <div className="text-xs text-muted-foreground mb-1">Status</div>
            <div className="font-semibold text-sm capitalize">{edicao.status}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs text-muted-foreground">Duração do Corte</span>
              <button
                onClick={() => {
                  setEditandoCorte(!editandoCorte)
                  if (!editandoCorte && edicao) {
                    setCorteInicio(formatSec(edicao.janela_inicio_sec))
                    setCorteFim(formatSec(edicao.janela_fim_sec))
                  }
                }}
                className="text-primary hover:text-primary/70"
              >
                <Pencil className="h-3 w-3" />
              </button>
            </div>
            <div className="font-semibold text-sm">{formatSec(edicao.duracao_corte_sec)}</div>
            <div className="text-xs text-muted-foreground">{formatSec(edicao.janela_inicio_sec)} → {formatSec(edicao.janela_fim_sec)}</div>
            {editandoCorte && (
              <div className="mt-2 space-y-2 border-t pt-2">
                <div className="flex gap-2 items-center">
                  <Input value={corteInicio} onChange={e => setCorteInicio(e.target.value)} placeholder="MM:SS" className="w-20 h-7 text-xs font-mono" />
                  <span className="text-xs text-muted-foreground">→</span>
                  <Input value={corteFim} onChange={e => setCorteFim(e.target.value)} placeholder="MM:SS" className="w-20 h-7 text-xs font-mono" />
                </div>
                <Button
                  size="sm"
                  className="w-full text-xs"
                  onClick={() => handleReaplicarCorte({ janela_inicio: parseMMSS(corteInicio), janela_fim: parseMMSS(corteFim) })}
                  disabled={reaplicando}
                >
                  {reaplicando ? "Reaplicando..." : "Reaplicar Corte"}
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-xs text-muted-foreground mb-1">Rota</div>
            <div className="font-semibold text-sm">{edicao.rota_alinhamento || "—"}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-xs text-muted-foreground mb-1">Confiança</div>
            <div className="font-semibold text-sm">{edicao.confianca_alinhamento ? `${(edicao.confianca_alinhamento * 100).toFixed(0)}%` : "—"}</div>
          </CardContent>
        </Card>
      </div>

      {/* Actions */}
      <div className="flex gap-3 mb-6 flex-wrap">
        <Button variant="secondary" size="sm" className="gap-2" onClick={() => router.push(`/editor/edicao/${edicaoId}/alinhamento`)}>
          <ArrowLeft className="h-3.5 w-3.5" /> Voltar ao Alinhamento
        </Button>
        <Button variant="secondary" size="sm" className="gap-2" onClick={() => handleReaplicarCorte()} disabled={reaplicando}>
          <RotateCcw className="h-3.5 w-3.5" />
          {reaplicando ? "Recalculando..." : "Refazer Corte"}
        </Button>
        {!edicao.eh_instrumental && (
          <Button variant="outline" size="sm" className="gap-2" onClick={handleTraduzir} disabled={traduzindo || edicao.status === "traducao"}>
            {(traduzindo || edicao.status === "traducao") && <RefreshCw className="h-3.5 w-3.5 animate-spin" />}
            {traduzindo || edicao.status === "traducao" ? "Traduzindo..." : "Traduzir Lyrics x7 idiomas"}
          </Button>
        )}
        {!isConcluido && !isPreviewPronto && !isPreview && edicao.status !== "renderizando" && (
          <Button size="sm" className="gap-2" onClick={handleRenderizarPreview} disabled={renderizando || traduzindo || edicao.status === "traducao"}>
            {renderizando || isPreview ? <RefreshCw className="h-3.5 w-3.5 animate-spin" /> : <Eye className="h-3.5 w-3.5" />}
            {renderizando || isPreview ? "Renderizando preview..." : "Renderizar Preview"}
          </Button>
        )}
        {isPreview && (
          <div className="flex items-center gap-2 bg-blue-100 text-blue-700 px-4 py-2 rounded-lg text-sm font-medium">
            <RefreshCw className="h-3.5 w-3.5 animate-spin" />
            Renderizando preview...
          </div>
        )}
        {isConcluido && (
          <Button size="sm" className="gap-2" onClick={handleRenderizarTodos} disabled={renderizando || edicao.status === "renderizando"}>
            {renderizando || edicao.status === "renderizando" ? <RefreshCw className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3.5 w-3.5" />}
            {renderizando || edicao.status === "renderizando" ? "Renderizando..." : "Re-renderizar Todos"}
          </Button>
        )}
        {concluidos.length > 0 && (
          <Button size="sm" variant="outline" className="gap-2 border-green-400 text-green-700 hover:bg-green-50" onClick={handleExportar} disabled={exportando}>
            {exportando ? <RefreshCw className="h-3.5 w-3.5 animate-spin" /> : <Download className="h-3.5 w-3.5" />}
            {exportando ? "Exportando..." : "Salvar no iCloud"}
          </Button>
        )}
      </div>

      {exportResult && (
        <div className="bg-green-50 border border-green-200 text-green-700 text-sm rounded-lg p-4 mb-6">
          <p className="font-medium">{exportResult.arquivos_exportados} vídeos exportados para:</p>
          <p className="text-xs mt-1 font-mono break-all">{exportResult.pasta}</p>
        </div>
      )}

      {/* Renders list */}
      {renders.length > 0 && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Vídeos Renderizados ({concluidos.length}/{IDIOMAS.length})</CardTitle>
            {concluidos.length > 0 && (
              <span className="text-xs text-muted-foreground">Clique para baixar</span>
            )}
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {IDIOMAS.map(({ code, flag, label }) => {
                const render = renders.find(r => r.idioma === code)
                if (!render) return (
                  <div key={code} className="flex items-center gap-3 py-3 px-4 rounded-lg bg-muted/50 text-muted-foreground text-sm">
                    <span className="text-lg">{flag}</span>
                    <span className="flex-1">{label}</span>
                    <span className="text-xs">Pendente</span>
                  </div>
                )
                return (
                  <div key={code} className={`flex items-center gap-3 py-3 px-4 rounded-lg text-sm ${render.status === "concluido" ? "bg-green-50 hover:bg-green-100 transition" : "bg-red-50"}`}>
                    <span className="text-lg">{flag}</span>
                    <span className="flex-1 font-medium">{label}</span>
                    {render.status === "concluido" ? (
                      <>
                        <span className="text-xs text-muted-foreground">{formatBytes(render.tamanho_bytes)}</span>
                        <Button asChild size="sm" variant="outline" className="gap-1.5 border-green-400 text-green-700 hover:bg-green-100">
                          <a href={editorApi.downloadRenderUrl(edicaoId, render.id)} download>
                            <Download className="h-3.5 w-3.5" /> Baixar
                          </a>
                        </Button>
                      </>
                    ) : (
                      <>
                        <span className="text-xs text-destructive truncate max-w-[200px]">{render.erro_msg}</span>
                        <XCircle className="h-4 w-4 text-destructive" />
                      </>
                    )}
                  </div>
                )
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Footer */}
      <div className="mt-8 text-center pb-8">
        <Button asChild variant="secondary" className="gap-2">
          <Link href="/editor"><ArrowLeft className="h-3.5 w-3.5" /> Voltar à Fila de Edição</Link>
        </Button>
      </div>
    </div>
  )
}
