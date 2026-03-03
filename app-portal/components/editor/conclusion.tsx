"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { editorApi, type Edicao, type Render, type FilaStatus, type ProgressoDetalhe, type PacoteStatus } from "@/lib/api/editor"
import { ApiError } from "@/lib/api/base"
import { useAdaptivePolling } from "@/lib/hooks/use-polling"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog"
import {
  ArrowLeft, Download, Play, RefreshCw, CheckCircle, XCircle,
  ExternalLink, Pencil, RotateCcw, Eye, MessageSquare, Package,
  Lock, AlertTriangle, Wrench, Trash2,
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

function formatProgresso(p: ProgressoDetalhe | null | undefined): string | null {
  if (!p || typeof p !== "object") return null
  if (!p.etapa || p.total == null || p.concluidos == null) return null
  const label = p.etapa === "traducao" ? "Traduzindo" : "Renderizando"
  const atual = p.atual ? ` (${p.atual})` : ""
  return `${label}: ${p.concluidos}/${p.total} idiomas${atual}`
}

function formatBytes(bytes: number | null | undefined) {
  if (!bytes) return "--"
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatSec(sec: number | null | undefined) {
  if (!sec && sec !== 0) return "--:--"
  const m = Math.floor(sec / 60)
  const s = Math.floor(sec % 60)
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`
}

export function EditorConclusion({ edicaoId }: { edicaoId: number }) {
  const router = useRouter()
  const [edicao, setEdicao] = useState<Edicao | null>(null)
  const [renders, setRenders] = useState<Render[]>([])
  const [loading, setLoading] = useState(true)
  const [renderizando, setRenderizando] = useState(false)
  const [traduzindo, setTraduzindo] = useState(false)
  const [baixandoTodos, setBaixandoTodos] = useState(false)
  const [baixandoRenders, setBaixandoRenders] = useState<Set<number>>(new Set())
  const [pacoteStatus, setPacoteStatus] = useState<PacoteStatus | null>(null)
  const [error, setError] = useState("")
  const [editandoCorte, setEditandoCorte] = useState(false)
  const [corteInicio, setCorteInicio] = useState("")
  const [corteFim, setCorteFim] = useState("")
  const [reaplicando, setReaplicando] = useState(false)
  const [notasRevisao, setNotasRevisao] = useState("")
  const [mostrarRevisao, setMostrarRevisao] = useState(false)
  const [aprovando, setAprovando] = useState(false)
  const [desbloqueando, setDesbloqueando] = useState(false)
  const [filaStatus, setFilaStatus] = useState<FilaStatus | null>(null)
  const [semLyrics, setSemLyrics] = useState(false)
  const [semLegendas, setSemLegendas] = useState(false)
  const [mostrarConfirmLimpar, setMostrarConfirmLimpar] = useState(false)
  const [limpando, setLimpando] = useState(false)

  const load = async () => {
    try {
      const [e, r, fila] = await Promise.all([
        editorApi.obterEdicao(edicaoId),
        editorApi.listarRenders(edicaoId),
        editorApi.filaStatus().catch(() => null),
      ])
      setEdicao(e)
      setSemLyrics(!!e.sem_lyrics)
      setRenders(r)
      setFilaStatus(fila)
    } catch (err: unknown) {
      setError("Erro ao carregar dados: " + (err instanceof Error ? err.message : "Erro"))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [edicaoId])

  const isProcessing = !!edicao && ["renderizando", "traducao", "preview"].includes(edicao.status)
  const { isSlowPolling } = useAdaptivePolling(load, isProcessing)

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
      await editorApi.renderizarPreview(edicaoId, { sem_legendas: semLegendas })
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
      await editorApi.aprovarPreview(edicaoId, { aprovado: true }, { sem_legendas: semLegendas })
      await load()
    } catch (err: unknown) {
      if (err instanceof ApiError && err.status === 409) {
        setError("Esta edição já está sendo processada. Aguarde a conclusão ou atualize a página.")
      } else {
        setError("Erro ao aprovar: " + (err instanceof Error ? err.message : "Erro"))
      }
    } finally {
      setAprovando(false)
    }
  }

  const handleSolicitarRevisao = async () => {
    setAprovando(true)
    setError("")
    try {
      await editorApi.aprovarPreview(edicaoId, { aprovado: false, notas_revisao: notasRevisao }, { sem_legendas: semLegendas })
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
      await editorApi.renderizar(edicaoId, { sem_legendas: semLegendas })
      await load()
    } catch (err: unknown) {
      setError("Erro na renderização: " + (err instanceof Error ? err.message : "Erro"))
    } finally {
      setRenderizando(false)
    }
  }

  const triggerDownload = (url: string) => {
    const a = document.createElement("a")
    a.href = url
    a.style.display = "none"
    document.body.appendChild(a)
    a.click()
    setTimeout(() => document.body.removeChild(a), 200)
  }

  const handleBaixarRender = async (renderId: number) => {
    setBaixandoRenders(prev => new Set(prev).add(renderId))
    try {
      triggerDownload(editorApi.downloadRenderUrl(edicaoId, renderId))
      // Pequeno delay para o browser processar
      await new Promise(r => setTimeout(r, 1500))
    } finally {
      setBaixandoRenders(prev => {
        const next = new Set(prev)
        next.delete(renderId)
        return next
      })
    }
  }

  const handleBaixarTodos = async () => {
    if (!edicao) return
    setBaixandoTodos(true)
    setError("")
    try {
      // Verifica se já tem pacote pronto
      const current = await editorApi.statusPacote(edicaoId).catch(() => null)
      if (current?.status === "pronto") {
        triggerDownload(editorApi.pacoteDownloadUrl(edicaoId))
        return
      }

      // Inicia geração assíncrona
      await editorApi.iniciarPacote(edicaoId)
      setPacoteStatus({ status: "gerando", url: null, erro: null })

      // Polling até ficar pronto (a cada 3s, máx 10 min)
      const maxAttempts = 200
      for (let i = 0; i < maxAttempts; i++) {
        await new Promise(r => setTimeout(r, 3000))
        const st = await editorApi.statusPacote(edicaoId).catch(() => null)
        if (!st) continue
        setPacoteStatus(st)
        if (st.status === "pronto") {
          triggerDownload(editorApi.pacoteDownloadUrl(edicaoId))
          return
        }
        if (st.status === "erro") {
          setError(`Erro ao gerar pacote: ${st.erro || "erro desconhecido"}`)
          return
        }
      }
      setError("Pacote demorou demais. Tente novamente ou baixe individualmente.")
    } catch (err: unknown) {
      setError("Erro ao iniciar pacote: " + (err instanceof Error ? err.message : "Erro"))
    } finally {
      setBaixandoTodos(false)
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

  const handleDesbloquear = async () => {
    setDesbloqueando(true)
    setError("")
    try {
      await editorApi.desbloquear(edicaoId)
      await load()
    } catch (err: unknown) {
      if (err instanceof ApiError && err.status === 409) {
        setError("Edição não pode ser desbloqueada — processamento ativo.")
      } else {
        setError("Erro ao desbloquear: " + (err instanceof Error ? err.message : "Erro"))
      }
    } finally {
      setDesbloqueando(false)
    }
  }

  const handleLimparEdicao = async () => {
    setLimpando(true)
    setError("")
    try {
      await editorApi.limparEdicao(edicaoId)
      setMostrarConfirmLimpar(false)
      await load()
    } catch (err: unknown) {
      if (err instanceof ApiError && err.status === 409) {
        setError((err as ApiError).message || "Edição está sendo processada agora. Aguarde terminar ou use Desbloquear primeiro.")
      } else {
        setError("Erro ao limpar edição: " + (err instanceof Error ? err.message : "Erro"))
      }
      setMostrarConfirmLimpar(false)
    } finally {
      setLimpando(false)
    }
  }

  const handleRefazerPreview = async () => {
    setRenderizando(true)
    setError("")
    try {
      await editorApi.desbloquear(edicaoId).catch(() => {})
      await editorApi.renderizarPreview(edicaoId, { sem_legendas: semLegendas })
      await load()
    } catch (err: unknown) {
      setError("Erro ao refazer preview: " + (err instanceof Error ? err.message : "Erro"))
    } finally {
      setRenderizando(false)
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
  const sistemaBloqueado = !!(filaStatus?.ocupado && filaStatus.edicao_id !== edicaoId)

  const isErro = edicao.status === "erro"
  const isMontagem = edicao.status === "montagem"
  const isActiveStatus = ["traducao", "renderizando", "preview"].includes(edicao.status)

  // Heartbeat stale detection (> 5 minutes)
  const heartbeatStaleMinutes = (() => {
    if (!isActiveStatus || !edicao.task_heartbeat) return isActiveStatus ? 999 : null
    const hbTime = new Date(edicao.task_heartbeat).getTime()
    const diffMs = Date.now() - hbTime
    const diffMin = Math.floor(diffMs / 60000)
    return diffMin >= 5 ? diffMin : null
  })()
  const isHeartbeatStale = heartbeatStaleMinutes !== null && isActiveStatus

  // Error contextual recovery hints
  const erroMsg = edicao.erro_msg ?? ""
  const erroRelatedToTranslation = /tradu[cç][aã]o/i.test(erroMsg)
  const erroRelatedToRender = /render|ffmpeg/i.test(erroMsg)

  // Preview é renderizado em PT (exceto se a música já for PT), mesma lógica do backend
  const idiomaPreview = edicao.idioma !== "pt" ? "pt" : edicao.idioma
  const previewRender = renders.find(r => r.idioma === idiomaPreview && r.status === "concluido")

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

      {/* Botão primário "Baixar Todos" — destaque quando tudo concluído */}
      {todosOk && (
        <div className="flex flex-col items-center gap-2 mb-6">
          <Button
            size="lg"
            className="gap-2 text-base px-8 py-3"
            onClick={handleBaixarTodos}
            disabled={baixandoTodos}
          >
            {baixandoTodos ? <RefreshCw className="h-5 w-5 animate-spin" /> : <Download className="h-5 w-5" />}
            {baixandoTodos && pacoteStatus?.status === "gerando"
              ? "Gerando pacote ZIP..."
              : baixandoTodos
                ? "Iniciando..."
                : "Baixar Todos os Vídeos"}
          </Button>
          {baixandoTodos && (
            <p className="text-sm text-muted-foreground">
              {pacoteStatus?.status === "gerando"
                ? "Empacotando vídeos — isso pode levar alguns minutos..."
                : "Verificando status do pacote..."}
            </p>
          )}
        </div>
      )}

      {error && <div className="bg-destructive/10 text-destructive text-sm rounded-lg p-3 mb-4">{error}</div>}

      {/* System busy banner */}
      {filaStatus?.ocupado && filaStatus.edicao_id !== edicaoId && (
        <div className="bg-amber-50 border border-amber-300 rounded-xl p-4 mb-4 text-sm text-amber-800">
          <p className="font-semibold">
            Sistema processando edição #{filaStatus.edicao_id} — {filaStatus.etapa ?? "processando"}.
            Aguarde ou volte depois.
          </p>
          {formatProgresso(filaStatus.progresso) && (
            <p className="mt-1 text-amber-700">{formatProgresso(filaStatus.progresso)}</p>
          )}
        </div>
      )}

      {/* Slow polling notice */}
      {isSlowPolling && (
        <div className="bg-muted border rounded-lg px-4 py-2 mb-4 text-sm text-muted-foreground">
          Processo em andamento, verificando a cada 15s...
        </div>
      )}

      {/* Error contextual banner */}
      {isErro && erroMsg && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-4">
          <div className="flex items-start gap-3">
            <XCircle className="h-5 w-5 text-red-500 mt-0.5 flex-shrink-0" />
            <div className="flex-1">
              <p className="text-sm font-semibold text-red-800">Erro na edição</p>
              <p className="text-sm text-red-700 mt-1 whitespace-pre-wrap">{erroMsg}</p>
            </div>
          </div>
        </div>
      )}

      {/* Heartbeat stale banner */}
      {isHeartbeatStale && !isErro && (
        <div className="bg-amber-50 border border-amber-300 rounded-xl p-4 mb-4 flex items-start gap-3">
          <AlertTriangle className="h-5 w-5 text-amber-600 mt-0.5 flex-shrink-0" />
          <div className="flex-1">
            <p className="text-sm font-semibold text-amber-800">O processamento parece travado</p>
            <p className="text-sm text-amber-700 mt-1">
              Último sinal há {heartbeatStaleMinutes} minuto{heartbeatStaleMinutes !== 1 ? "s" : ""}.
            </p>
            <Button
              variant="outline"
              size="sm"
              className="mt-2 gap-2 border-amber-400 text-amber-700 hover:bg-amber-100"
              onClick={handleDesbloquear}
              disabled={desbloqueando}
            >
              {desbloqueando ? <RefreshCw className="h-3.5 w-3.5 animate-spin" /> : <Lock className="h-3.5 w-3.5" />}
              {desbloqueando ? "Desbloqueando..." : "Desbloquear Edição"}
            </Button>
          </div>
        </div>
      )}

      {/* Granular progress / current edicao being processed */}
      {isProcessing && filaStatus?.ocupado && filaStatus.edicao_id === edicaoId && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg px-4 py-2 mb-4 text-sm text-blue-700 flex items-center gap-2">
          <RefreshCw className="h-3.5 w-3.5 animate-spin flex-shrink-0" />
          {formatProgresso(edicao.progresso_detalhe)
            ?? formatProgresso(filaStatus.progresso as ProgressoDetalhe | null)
            ?? `Processando: ${filaStatus.etapa ?? edicao.status}…`}
        </div>
      )}

      {/* Revision card */}
      {isRevisao && (
        <div className="bg-yellow-50 border border-yellow-300 rounded-xl p-5 mb-6">
          <div className="flex items-start gap-3">
            <MessageSquare className="h-5 w-5 text-yellow-600 mt-0.5" />
            <div className="flex-1">
              <h3 className="font-semibold text-yellow-800 mb-1">Revisão Solicitada</h3>
              {edicao.notas_revisao && (
                <p className="text-sm text-yellow-700 whitespace-pre-wrap">{edicao.notas_revisao}</p>
              )}
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
      {isPreviewPronto && (
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-6 mb-6">
          <h3 className="font-semibold text-blue-800 mb-3 flex items-center gap-2">
            <Eye className="h-4 w-4" /> Preview — {idiomaPreview.toUpperCase()}
          </h3>
          {previewRender ? (
            <>
              <p className="text-sm text-blue-700 mb-4 text-center">
                Baixe o vídeo e assista localmente (QuickTime, VLC) antes de aprovar.
              </p>
              <div className="flex gap-3 justify-center flex-wrap mb-4">
                <Button asChild variant="outline" className="gap-2 border-blue-400 text-blue-700 hover:bg-blue-100">
                  <a href={editorApi.downloadRenderUrl(edicaoId, previewRender.id)} target="_blank" rel="noopener">
                    <Download className="h-3.5 w-3.5" /> Baixar Preview
                  </a>
                </Button>
              </div>
            </>
          ) : (
            <p className="text-sm text-blue-700 mb-4 text-center">
              Preview concluído. Aprove para renderizar todos os idiomas.
            </p>
          )}
          <div className="flex gap-3 justify-center flex-wrap">
            <Button onClick={handleAprovarPreview} disabled={aprovando || sistemaBloqueado} className="gap-2">
              {aprovando ? <RefreshCw className="h-3.5 w-3.5 animate-spin" /> : <CheckCircle className="h-3.5 w-3.5" />}
              {aprovando ? "Renderizando..." : "Aprovar e Renderizar Todos"}
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

      {/* Toggle sem lyrics (persiste no banco) */}
      <div className="mb-4 space-y-2">
        <label className="flex items-center gap-2 cursor-pointer select-none" title="Ative para músicas instrumentais ou com texto mínimo repetitivo">
          <input
            type="checkbox"
            checked={semLyrics}
            onChange={async (e) => {
              const val = e.target.checked
              setSemLyrics(val)
              try {
                await editorApi.atualizarEdicao(edicaoId, { sem_lyrics: val } as Partial<Edicao>)
              } catch {
                setSemLyrics(!val)
              }
            }}
            className="h-4 w-4 rounded border-gray-300 accent-amber-600"
          />
          <span className="text-sm font-medium">Sem legendas de transcrição</span>
          <span className="text-xs text-muted-foreground">(músicas instrumentais / texto mínimo)</span>
        </label>
        {semLyrics && (
          <div className="bg-amber-50 border border-amber-300 rounded-lg px-3 py-2 text-sm text-amber-800 flex items-start gap-2">
            <AlertTriangle className="h-4 w-4 mt-0.5 flex-shrink-0" />
            <span>Vídeo será gerado apenas com overlay editorial (topo). Legendas de letra e tradução serão omitidas.</span>
          </div>
        )}

        {/* Toggle sem legendas (remove todas, inclusive overlay) */}
        <label className="flex items-center gap-2 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={semLegendas}
            onChange={e => setSemLegendas(e.target.checked)}
            className="h-4 w-4 rounded border-gray-300 accent-gray-600"
          />
          <span className="text-sm font-medium">Renderizar sem nenhuma legenda</span>
        </label>
        {semLegendas && (
          <div className="bg-amber-50 border border-amber-300 rounded-lg px-3 py-2 text-sm text-amber-800 flex items-start gap-2">
            <AlertTriangle className="h-4 w-4 mt-0.5 flex-shrink-0" />
            <span>Vídeo será gerado sem nenhuma legenda (overlay, letra e tradução).</span>
          </div>
        )}
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
          <Button variant="outline" size="sm" className="gap-2" onClick={handleTraduzir} disabled={traduzindo || edicao.status === "traducao" || sistemaBloqueado}>
            {(traduzindo || edicao.status === "traducao") && <RefreshCw className="h-3.5 w-3.5 animate-spin" />}
            {traduzindo || edicao.status === "traducao" ? "Traduzindo..." : "Traduzir Lyrics x7 idiomas"}
          </Button>
        )}
        {!isConcluido && !isPreviewPronto && !isPreview && edicao.status !== "renderizando" && (
          <Button size="sm" className="gap-2" onClick={handleRenderizarPreview} disabled={renderizando || traduzindo || edicao.status === "traducao" || sistemaBloqueado}>
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
          <Button size="sm" className="gap-2" onClick={handleRenderizarTodos} disabled={renderizando || edicao.status === "renderizando" || sistemaBloqueado}>
            {renderizando || edicao.status === "renderizando" ? <RefreshCw className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3.5 w-3.5" />}
            {renderizando || edicao.status === "renderizando" ? "Renderizando..." : "Re-renderizar Todos"}
          </Button>
        )}
      </div>

      {/* Recovery section */}
      {(isErro || isHeartbeatStale || isMontagem || isPreviewPronto) && (
        <div className="border border-dashed border-muted-foreground/30 rounded-xl p-4 mb-6">
          <div className="flex items-center gap-2 mb-3 text-muted-foreground">
            <Wrench className="h-4 w-4" />
            <span className="text-sm font-medium">Resolver problemas</span>
          </div>
          <div className="flex gap-2 flex-wrap">
            {/* Desbloquear: always on error, or on stale heartbeat */}
            {(isErro || isHeartbeatStale) && (
              <Button
                variant="outline"
                size="sm"
                className="gap-2"
                onClick={handleDesbloquear}
                disabled={desbloqueando}
              >
                {desbloqueando ? <RefreshCw className="h-3.5 w-3.5 animate-spin" /> : <Lock className="h-3.5 w-3.5" />}
                {desbloqueando ? "Desbloqueando..." : "Desbloquear Edição"}
              </Button>
            )}
            {/* Refazer Tradução: montagem or error (with translation hint or always) */}
            {(isMontagem || (isErro && (erroRelatedToTranslation || !erroRelatedToRender))) && !edicao.eh_instrumental && (
              <Button
                variant="outline"
                size="sm"
                className="gap-2"
                onClick={handleTraduzir}
                disabled={traduzindo || sistemaBloqueado}
              >
                {traduzindo ? <RefreshCw className="h-3.5 w-3.5 animate-spin" /> : <RotateCcw className="h-3.5 w-3.5" />}
                Refazer Tradução
              </Button>
            )}
            {/* Refazer Preview: preview_pronto or error */}
            {(isPreviewPronto || isErro) && (
              <Button
                variant="outline"
                size="sm"
                className="gap-2"
                onClick={handleRefazerPreview}
                disabled={renderizando || sistemaBloqueado}
              >
                {renderizando ? <RefreshCw className="h-3.5 w-3.5 animate-spin" /> : <Eye className="h-3.5 w-3.5" />}
                Refazer Preview
              </Button>
            )}
            {/* Voltar para Alinhamento */}
            {(isErro || isMontagem) && (
              <Button
                variant="ghost"
                size="sm"
                className="gap-2 text-muted-foreground"
                onClick={() => router.push(`/editor/edicao/${edicaoId}/alinhamento`)}
              >
                <ArrowLeft className="h-3.5 w-3.5" />
                Voltar para Alinhamento
              </Button>
            )}
          </div>
        </div>
      )}

      {/* Renders list */}
      {(renders.length > 0 || edicao.status === "renderizando") && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Vídeos Renderizados ({concluidos.length}/{IDIOMAS.length})</CardTitle>
            {todosOk ? (
              <Button
                size="sm"
                variant="outline"
                className="gap-1.5 border-green-400 text-green-700 hover:bg-green-100"
                onClick={handleBaixarTodos}
                disabled={baixandoTodos}
              >
                {baixandoTodos ? <RefreshCw className="h-3.5 w-3.5 animate-spin" /> : <Package className="h-3.5 w-3.5" />}
                {baixandoTodos && pacoteStatus?.status === "gerando"
                  ? "Gerando ZIP..."
                  : baixandoTodos
                    ? "Iniciando..."
                    : "Baixar Todos"}
              </Button>
            ) : concluidos.length > 0 ? (
              <span className="text-xs text-muted-foreground">Baixe individualmente</span>
            ) : null}
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {IDIOMAS.map(({ code, flag, label }) => {
                const render = renders.find(r => r.idioma === code)
                const isAtual = edicao.status === "renderizando" && edicao.progresso_detalhe?.atual === code
                if (!render) return (
                  <div key={code} className={`flex items-center gap-3 py-3 px-4 rounded-lg text-sm ${isAtual ? "bg-blue-50" : "bg-muted/50 text-muted-foreground"}`}>
                    <span className="text-lg">{flag}</span>
                    <span className="flex-1">{label}</span>
                    {isAtual ? (
                      <span className="text-xs text-blue-600 flex items-center gap-1.5">
                        <RefreshCw className="h-3 w-3 animate-spin" /> Renderizando...
                      </span>
                    ) : (
                      <span className="text-xs">Pendente</span>
                    )}
                  </div>
                )
                return (
                  <div key={code} className={`flex items-center gap-3 py-3 px-4 rounded-lg text-sm ${render.status === "concluido" ? "bg-green-50 hover:bg-green-100 transition" : "bg-red-50"}`}>
                    <span className="text-lg">{flag}</span>
                    <span className="flex-1 font-medium">{label}</span>
                    {render.status === "concluido" ? (
                      <>
                        <CheckCircle className="h-4 w-4 text-green-500" />
                        <span className="text-xs text-muted-foreground">{formatBytes(render.tamanho_bytes)}</span>
                        <Button
                          size="sm"
                          variant="outline"
                          className="gap-1.5 border-green-400 text-green-700 hover:bg-green-100"
                          onClick={() => handleBaixarRender(render.id)}
                          disabled={baixandoRenders.has(render.id)}
                        >
                          {baixandoRenders.has(render.id)
                            ? <><RefreshCw className="h-3.5 w-3.5 animate-spin" /> Baixando...</>
                            : <><Download className="h-3.5 w-3.5" /> Baixar</>
                          }
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
      <div className="mt-8 flex items-center justify-between pb-8">
        <Button asChild variant="secondary" className="gap-2">
          <Link href="/editor"><ArrowLeft className="h-3.5 w-3.5" /> Voltar à Fila de Edição</Link>
        </Button>
        {!isConcluido && !isPreviewPronto && (
          <Button
            variant="outline"
            size="sm"
            className="gap-2 border-red-300 text-red-600 hover:bg-red-50 hover:text-red-700"
            onClick={() => setMostrarConfirmLimpar(true)}
            disabled={limpando}
          >
            <Trash2 className="h-3.5 w-3.5" />
            Limpar Edição
          </Button>
        )}
      </div>

      {/* Dialog confirmação Limpar Edição */}
      <Dialog open={mostrarConfirmLimpar} onOpenChange={setMostrarConfirmLimpar}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-red-700">
              <AlertTriangle className="h-5 w-5" />
              Limpar Edição
            </DialogTitle>
            <DialogDescription>
              Tem certeza? Todo o progresso desta edição será apagado e ela voltará ao início.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2 sm:gap-0">
            <Button variant="ghost" onClick={() => setMostrarConfirmLimpar(false)} disabled={limpando}>
              Cancelar
            </Button>
            <Button
              variant="destructive"
              onClick={handleLimparEdicao}
              disabled={limpando}
              className="gap-2"
            >
              {limpando ? <RefreshCw className="h-3.5 w-3.5 animate-spin" /> : <Trash2 className="h-3.5 w-3.5" />}
              {limpando ? "Limpando..." : "Sim, Limpar Tudo"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
