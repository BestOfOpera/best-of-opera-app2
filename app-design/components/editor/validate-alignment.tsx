"use client"

import { useState, useEffect, useRef } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { editorApi, type Edicao, type Segmento, type AlinhamentoData, type Janela } from "@/lib/api/editor"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { ArrowLeft, Check, RefreshCw, Scissors } from "lucide-react"

const FLAG_STYLES: Record<string, string> = {
  VERDE: "border-l-green-500 bg-green-50",
  AMARELO: "border-l-yellow-500 bg-yellow-50",
  VERMELHO: "border-l-red-500 bg-red-50",
  ROXO: "border-l-purple-500 bg-purple-50",
}

const FLAG_DOTS: Record<string, string> = {
  VERDE: "🟢",
  AMARELO: "🟡",
  VERMELHO: "🔴",
  ROXO: "🟣",
}

function parseTimestamp(ts: string | undefined | null): number {
  if (!ts) return 0
  const parts = ts.replace(",", ".").split(":")
  if (parts.length === 3) return parseFloat(parts[0]) * 3600 + parseFloat(parts[1]) * 60 + parseFloat(parts[2])
  if (parts.length === 2) return parseFloat(parts[0]) * 60 + parseFloat(parts[1])
  return parseFloat(parts[0])
}

function formatSec(sec: number | null | undefined): string {
  if (!sec && sec !== 0) return "--:--"
  const m = Math.floor(sec / 60)
  const s = Math.floor(sec % 60)
  return `${m}:${String(s).padStart(2, "0")}`
}

export function EditorValidateAlignment({ edicaoId }: { edicaoId: number }) {
  const router = useRouter()
  const [edicao, setEdicao] = useState<Edicao | null>(null)
  const [alinhamento, setAlinhamento] = useState<AlinhamentoData | null>(null)
  const [janela, setJanela] = useState<Janela | null>(null)
  const [segmentos, setSegmentos] = useState<Segmento[]>([])
  const [loading, setLoading] = useState(true)
  const [salvando, setSalvando] = useState(false)
  const [cortando, setCortando] = useState(false)
  const [error, setError] = useState("")
  const [polling, setPolling] = useState(false)
  const [retranscrevendo, setRetranscrevendo] = useState(false)
  const [audioFailed, setAudioFailed] = useState(false)
  const audioRef = useRef<HTMLAudioElement>(null)

  const load = async () => {
    try {
      const e = await editorApi.obterEdicao(edicaoId)
      setEdicao(e)

      if (e.status === "transcricao") {
        if (e.erro_msg) {
          setError("Erro na transcrição: " + e.erro_msg)
          setPolling(false)
        } else {
          setPolling(true)
        }
        return
      }
      setPolling(false)

      const result = await editorApi.obterAlinhamento(edicaoId)
      setAlinhamento(result.alinhamento)
      setJanela(result.janela)
      setSegmentos(result.alinhamento?.segmentos || [])
    } catch (err: unknown) {
      if (polling) return
      setError("Erro ao carregar alinhamento: " + (err instanceof Error ? err.message : "Erro"))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [edicaoId])

  useEffect(() => {
    if (!polling) return
    const timer = setInterval(load, 5000)
    return () => clearInterval(timer)
  }, [polling])

  const updateSegmento = (index: number, field: string, value: string) => {
    const updated = [...segmentos]
    updated[index] = { ...updated[index], [field]: value } as Segmento

    if (field === "start" || field === "end") {
      const sec = parseTimestamp(value)
      if (!isNaN(sec) && sec > 0) {
        if (field === "start" && index > 0) {
          const prevEnd = parseTimestamp(updated[index - 1].end)
          if (prevEnd > sec) {
            updated[index - 1] = { ...updated[index - 1], end: value }
          }
        }
        if (field === "end" && index < updated.length - 1) {
          const nextStart = parseTimestamp(updated[index + 1].start)
          if (sec > nextStart) {
            updated[index + 1] = { ...updated[index + 1], start: value }
          }
        }
      }
    }

    setSegmentos(updated)
  }

  const handleValidar = async () => {
    setSalvando(true)
    setError("")
    try {
      await editorApi.validarAlinhamento(edicaoId, { segmentos })
      setCortando(true)
      try { await editorApi.aplicarCorte(edicaoId) } catch {}
      setCortando(false)
      router.push(`/editor/edicao/${edicaoId}/conclusao`)
    } catch (err: unknown) {
      setError("Erro: " + (err instanceof Error ? err.message : "Erro"))
    } finally {
      setSalvando(false)
    }
  }

  if (loading || !edicao) return <div className="text-center py-16 text-muted-foreground">Carregando...</div>

  if (polling || (edicao?.status === "transcricao" && error)) {
    return (
      <div className="max-w-3xl mx-auto text-center py-16">
        {error ? (
          <>
            <div className="text-destructive text-4xl mb-4">!</div>
            <h3 className="text-lg font-semibold mb-2 text-destructive">Erro na transcrição</h3>
            <div className="bg-destructive/10 text-destructive text-sm rounded-lg p-4 mb-4 text-left max-w-lg mx-auto whitespace-pre-wrap">{error}</div>
            <div className="flex gap-3 justify-center mt-4">
              <Button variant="link" onClick={() => router.push(`/editor/edicao/${edicaoId}/letra`)}>
                Voltar para letra
              </Button>
              <Button onClick={() => { setError(""); setPolling(true); load() }}>
                Tentar novamente
              </Button>
            </div>
          </>
        ) : (
          <>
            <RefreshCw className="h-8 w-8 mx-auto mb-4 text-primary animate-spin" />
            <h3 className="text-lg font-semibold mb-2">Transcrição em andamento...</h3>
            <p className="text-sm text-muted-foreground">O Gemini está analisando o áudio. Isso pode levar alguns minutos.</p>
            <p className="text-xs text-muted-foreground mt-4">Atualizando automaticamente...</p>
          </>
        )}
      </div>
    )
  }

  if (!alinhamento) {
    return (
      <div className="max-w-3xl mx-auto text-center py-16">
        <p className="text-muted-foreground">Alinhamento não disponível. Inicie a transcrição primeiro.</p>
        <Button variant="link" onClick={() => router.push(`/editor/edicao/${edicaoId}/letra`)} className="mt-4">
          Voltar para letra
        </Button>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto">
      <Button variant="ghost" size="sm" asChild className="mb-6 gap-2 text-muted-foreground">
        <Link href="/editor"><ArrowLeft className="h-4 w-4" /> Voltar à fila</Link>
      </Button>

      <div className="mb-6">
        <h2 className="text-2xl font-bold">{edicao.artista} — {edicao.musica}</h2>
        <p className="text-sm text-muted-foreground mt-1">Passo 4 — Validar Alinhamento</p>
      </div>

      {/* Audio player */}
      <div className="bg-card rounded-xl shadow-sm border p-4 mb-4 sticky top-0 z-10">
        <p className="text-xs text-muted-foreground mb-2">
          Ouça enquanto valida o alinhamento{edicao.arquivo_audio_completo ? " (clique nos timestamps para pular)" : ""}:
        </p>
        {edicao.arquivo_audio_completo && !audioFailed ? (
          <audio
            ref={audioRef}
            controls
            src={editorApi.audioUrl(edicaoId)}
            className="w-full"
            onError={() => setAudioFailed(true)}
          />
        ) : edicao.youtube_video_id ? (
          <iframe
            width="100%"
            height="80"
            src={`https://www.youtube.com/embed/${edicao.youtube_video_id}?rel=0`}
            allow="autoplay; encrypted-media"
            allowFullScreen
            className="rounded-lg"
            style={{ maxWidth: "100%" }}
          />
        ) : (
          <p className="text-xs text-muted-foreground">Nenhuma fonte de áudio disponível.</p>
        )}
      </div>

      {/* Info bar */}
      <div className="flex items-center gap-4 mb-6 flex-wrap">
        <div className="bg-card rounded-lg border px-4 py-2 text-sm">
          Rota <span className="font-bold text-primary">{alinhamento.rota}</span>
        </div>
        <div className="bg-card rounded-lg border px-4 py-2 text-sm">
          Confiança <span className="font-bold">{((alinhamento.confianca_media || 0) * 100).toFixed(0)}%</span>
        </div>
        {janela && (
          <div className="bg-card rounded-lg border px-4 py-2 text-sm flex items-center gap-2">
            <Scissors className="h-3.5 w-3.5 text-primary" />
            Corte: {formatSec(janela.inicio)} → {formatSec(janela.fim)} ({formatSec(janela.duracao)})
          </div>
        )}
        <div className="flex gap-2 text-xs">
          <span>🟢 {segmentos.filter(s => s.flag === "VERDE").length}</span>
          <span>🟡 {segmentos.filter(s => s.flag === "AMARELO").length}</span>
          <span>🔴 {segmentos.filter(s => s.flag === "VERMELHO").length}</span>
          <span>🟣 {segmentos.filter(s => s.flag === "ROXO").length}</span>
        </div>
      </div>

      {error && <div className="bg-destructive/10 text-destructive text-sm rounded-lg p-3 mb-4">{error}</div>}

      {/* Segments */}
      <div className="mb-4">
        <h4 className="text-sm font-semibold text-muted-foreground mb-2 uppercase tracking-wider">
          Segmentos ({segmentos.length})
        </h4>
        <div className="space-y-2">
          {segmentos.map((seg, i) => {
            const isDentro = !janela || (parseTimestamp(seg.start) >= (janela.inicio || 0) && parseTimestamp(seg.start) <= (janela.fim || Infinity))
            return (
              <div
                key={i}
                className={`border-l-4 rounded-lg p-3 ${FLAG_STYLES[seg.flag] || "border-l-gray-300 bg-gray-50"} ${!isDentro ? "opacity-40" : ""}`}
              >
                <div className="flex items-start gap-3">
                  <span className="text-xs mt-1">{FLAG_DOTS[seg.flag]}</span>
                  <div className="flex flex-col gap-0.5 shrink-0">
                    <div className="flex items-center gap-1">
                      <Input
                        value={seg.start || ""}
                        onChange={e => updateSegmento(i, "start", e.target.value)}
                        className="w-[85px] h-6 text-xs font-mono bg-transparent border-dashed"
                        title="Início (editável)"
                      />
                      <span className="text-xs text-muted-foreground">→</span>
                      <Input
                        value={seg.end || ""}
                        onChange={e => updateSegmento(i, "end", e.target.value)}
                        className="w-[85px] h-6 text-xs font-mono bg-transparent border-dashed"
                        title="Fim (editável)"
                      />
                    </div>
                    {edicao.arquivo_audio_completo && (
                      <button
                        type="button"
                        onClick={() => {
                          if (audioRef.current) {
                            audioRef.current.currentTime = parseTimestamp(seg.start)
                            audioRef.current.play()
                          }
                        }}
                        className="text-[10px] text-primary hover:underline text-left cursor-pointer"
                      >
                        Ouvir
                      </button>
                    )}
                  </div>
                  <div className="flex-1">
                    <Input
                      value={seg.texto_final || ""}
                      onChange={e => updateSegmento(i, "texto_final", e.target.value)}
                      className="h-7 bg-transparent border-transparent hover:border-border focus:border-primary text-sm"
                    />
                    {seg.texto_gemini && seg.texto_gemini !== seg.texto_final && (
                      <div className="text-xs text-muted-foreground mt-1">Gemini: {seg.texto_gemini}</div>
                    )}
                    {seg.candidato_letra && (
                      <div className="text-xs text-yellow-600 mt-1">Candidato: {seg.candidato_letra}</div>
                    )}
                  </div>
                  <span className="text-xs text-muted-foreground">{((seg.confianca || 0) * 100).toFixed(0)}%</span>
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-3 mt-6 sticky bottom-4">
        <Button
          variant="secondary"
          onClick={async () => {
            setRetranscrevendo(true)
            setError("")
            try {
              await editorApi.iniciarTranscricao(edicaoId)
              setPolling(true)
              setAlinhamento(null)
            } catch (err: unknown) {
              setError("Erro ao retranscrever: " + (err instanceof Error ? err.message : "Erro"))
            } finally {
              setRetranscrevendo(false)
            }
          }}
          disabled={retranscrevendo || salvando}
          className="gap-2"
        >
          <RefreshCw className={`h-4 w-4 ${retranscrevendo ? "animate-spin" : ""}`} />
          Retranscrever
        </Button>
        <Button
          onClick={handleValidar}
          disabled={salvando || cortando}
          className="flex-1 gap-2"
        >
          <Check className="h-4 w-4" />
          {cortando ? "Aplicando corte..." : salvando ? "Salvando..." : "Aprovar Alinhamento e Continuar"}
        </Button>
      </div>
    </div>
  )
}
