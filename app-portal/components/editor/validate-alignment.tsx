"use client"

import { useState, useEffect, useRef } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { editorApi, type Edicao, type Segmento, type AlinhamentoData, type Janela } from "@/lib/api/editor"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { ArrowLeft, Check, PenLine, Plus, RefreshCw, Scissors, Trash2 } from "lucide-react"

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
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`
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
  const [confirmingDelete, setConfirmingDelete] = useState<number | null>(null)
  const [manualIndices, setManualIndices] = useState<Set<number>>(new Set())
  const confirmTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const [addingAfterIndex, setAddingAfterIndex] = useState<number | null>(null)
  const [addFormStart, setAddFormStart] = useState("")
  const [addFormEnd, setAddFormEnd] = useState("")
  const [addFormText, setAddFormText] = useState("")
  const addFormTextRef = useRef<HTMLInputElement>(null)
  const [criandoManual, setCriandoManual] = useState(false)

  const load = async () => {
    try {
      const e = await editorApi.obterEdicao(edicaoId)
      setEdicao(e)

      // Status "erro" — exibir mensagem e parar polling
      if (e.status === "erro") {
        setError(e.erro_msg ? "Erro na transcrição: " + e.erro_msg : "Erro desconhecido na edição")
        setPolling(false)
        return
      }

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

  // Transcription polling with 8 minute timeout
  const [pollingTimedOut, setPollingTimedOut] = useState(false)
  const pollingStartRef = useRef<number>(0)
  useEffect(() => {
    if (!polling) {
      setPollingTimedOut(false)
      return
    }
    pollingStartRef.current = Date.now()
    setPollingTimedOut(false)
    const timer = setInterval(() => {
      if (Date.now() - pollingStartRef.current > 8 * 60 * 1000) {
        clearInterval(timer)
        setPollingTimedOut(true)
        return
      }
      load()
    }, 5000)
    return () => clearInterval(timer)
  }, [polling])

  const handleRetranscrever = async () => {
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
  }

  const handleInserirManual = async () => {
    setCriandoManual(true)
    setError("")
    try {
      await editorApi.criarAlinhamentoManual(edicaoId)
      setPolling(false)
      await load()
    } catch (err: unknown) {
      setError("Erro ao criar alinhamento manual: " + (err instanceof Error ? err.message : "Erro"))
    } finally {
      setCriandoManual(false)
    }
  }

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

  // --- Excluir segmento (confirmação duplo clique) ---
  const handleDeleteSegmento = (index: number) => {
    if (segmentos.length <= 1) return
    if (confirmingDelete === index) {
      if (confirmTimerRef.current) clearTimeout(confirmTimerRef.current)
      const updated = segmentos.filter((_, i) => i !== index)
      setSegmentos(updated)
      const newManual = new Set<number>()
      manualIndices.forEach(mi => {
        if (mi < index) newManual.add(mi)
        else if (mi > index) newManual.add(mi - 1)
      })
      setManualIndices(newManual)
      setConfirmingDelete(null)
    } else {
      setConfirmingDelete(index)
      if (confirmTimerRef.current) clearTimeout(confirmTimerRef.current)
      confirmTimerRef.current = setTimeout(() => setConfirmingDelete(null), 3000)
    }
  }

  // --- Adicionar segmento: abrir form inline ---
  const handleOpenAddForm = (afterIndex: number) => {
    const defaultStart = edicao?.cut_start || "00:00.000"
    const prevEnd = segmentos[afterIndex]?.end || defaultStart
    const nextStart = segmentos[afterIndex + 1]?.start || prevEnd
    setAddFormStart(prevEnd)
    setAddFormEnd(nextStart)
    setAddFormText("")
    setAddingAfterIndex(afterIndex)
  }

  const handleConfirmAdd = () => {
    if (addingAfterIndex === null) return
    const newIndex = addingAfterIndex + 1
    const newSeg: Segmento = {
      start: addFormStart,
      end: addFormEnd,
      texto_final: addFormText,
      flag: "VERDE",
      confianca: 1.0,
    }
    const updated = [...segmentos]
    updated.splice(newIndex, 0, newSeg)
    setSegmentos(updated)
    const newManual = new Set<number>()
    manualIndices.forEach(mi => {
      newManual.add(mi < newIndex ? mi : mi + 1)
    })
    newManual.add(newIndex)
    setManualIndices(newManual)
    setAddingAfterIndex(null)
  }

  const handleCancelAdd = () => {
    setAddingAfterIndex(null)
  }

  // Auto-focus no campo de texto quando o form abre
  useEffect(() => {
    if (addingAfterIndex !== null && addFormTextRef.current) {
      addFormTextRef.current.focus()
    }
  }, [addingAfterIndex])

  // Cancelar confirmação de delete ao clicar fora
  useEffect(() => {
    if (confirmingDelete === null) return
    const handler = (e: MouseEvent) => {
      const target = e.target as HTMLElement
      if (!target.closest(`[data-delete-btn="${confirmingDelete}"]`)) {
        setConfirmingDelete(null)
        if (confirmTimerRef.current) clearTimeout(confirmTimerRef.current)
      }
    }
    document.addEventListener("click", handler, true)
    return () => document.removeEventListener("click", handler, true)
  }, [confirmingDelete])

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

  if (polling || error) {
    const manualButton = (
      <Button
        variant="outline"
        onClick={handleInserirManual}
        disabled={criandoManual}
        className="gap-2"
      >
        <PenLine className="h-4 w-4" />
        {criandoManual ? "Criando..." : "Inserir letra manualmente"}
      </Button>
    )

    return (
      <div className="max-w-3xl mx-auto text-center py-16">
        {error ? (
          <>
            <div className="text-destructive text-4xl mb-4">!</div>
            <h3 className="text-lg font-semibold mb-2 text-destructive">Erro na transcrição</h3>
            <div className="bg-destructive/10 text-destructive text-sm rounded-lg p-4 mb-4 text-left max-w-lg mx-auto whitespace-pre-wrap">{error}</div>
            <div className="flex gap-3 justify-center mt-4 flex-wrap">
              <Button variant="link" onClick={() => router.push(`/editor/edicao/${edicaoId}/letra`)}>
                Voltar para letra
              </Button>
              <Button onClick={handleRetranscrever} disabled={retranscrevendo}>
                <RefreshCw className={`h-4 w-4 mr-2 ${retranscrevendo ? "animate-spin" : ""}`} />
                {retranscrevendo ? "Retranscrevendo..." : "Retranscrever"}
              </Button>
              {manualButton}
            </div>
          </>
        ) : (
          <>
            {pollingTimedOut ? (
              <>
                <div className="h-8 w-8 mx-auto mb-4 text-yellow-500 text-3xl">⏱</div>
                <h3 className="text-lg font-semibold mb-2 text-yellow-700">Timeout — transcrição demorando demais</h3>
                <p className="text-sm text-muted-foreground">O backend pode ter travado. Tente recarregar ou iniciar novamente.</p>
                <div className="flex gap-3 justify-center mt-4 flex-wrap">
                  <Button variant="outline" onClick={() => window.location.reload()}>Recarregar</Button>
                  <Button onClick={handleRetranscrever} disabled={retranscrevendo}>
                    {retranscrevendo ? "Retranscrevendo..." : "Retranscrever"}
                  </Button>
                  {manualButton}
                </div>
              </>
            ) : (
              <>
                <RefreshCw className="h-8 w-8 mx-auto mb-4 text-primary animate-spin" />
                <h3 className="text-lg font-semibold mb-2">Transcrição em andamento...</h3>
                <p className="text-sm text-muted-foreground">O Gemini está analisando o áudio. Isso pode levar alguns minutos.</p>
                <p className="text-xs text-muted-foreground mt-4">Atualizando automaticamente...</p>
                <div className="mt-6">
                  {manualButton}
                </div>
              </>
            )}
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

      {/* Banner modo manual */}
      {alinhamento.rota === "M" && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-4">
          <div className="flex items-start gap-3">
            <PenLine className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
            <div>
              <h4 className="text-sm font-semibold text-amber-800">Modo manual — insira a letra com timestamps</h4>
              <p className="text-sm text-amber-700 mt-1">
                Use o botão <span className="font-medium">+</span> abaixo para adicionar cada verso com seu timestamp.
                {(edicao.cut_start || edicao.cut_end) && (
                  <>
                    {" "}Corte escolhido:{" "}
                    <span className="font-bold">{edicao.cut_start || "?"} — {edicao.cut_end || "?"}</span>
                    {" "}(só é necessário sincronizar esse trecho).
                  </>
                )}
              </p>
            </div>
          </div>
        </div>
      )}

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
        <div className="space-y-0">
          {segmentos.map((seg, i) => {
            const isDentro = !janela || (parseTimestamp(seg.start) >= (janela.inicio || 0) && parseTimestamp(seg.start) <= (janela.fim || Infinity))
            const isManual = manualIndices.has(i)
            const isConfirming = confirmingDelete === i
            return (
              <div key={i} data-seg-index={i}>
                <div
                  className={`border-l-4 rounded-lg p-3 ${isManual ? "border-l-blue-500 bg-blue-50" : FLAG_STYLES[seg.flag] || "border-l-gray-300 bg-gray-50"} ${!isDentro ? "opacity-40" : ""} transition-all`}
                >
                  <div className="flex items-start gap-3">
                    <span className="text-xs mt-1">{isManual ? "🔵" : FLAG_DOTS[seg.flag]}</span>
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
                        data-field="texto_final"
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
                    <span className="text-xs text-muted-foreground whitespace-nowrap">{((seg.confianca || 0) * 100).toFixed(0)}%</span>
                    <button
                      type="button"
                      data-delete-btn={i}
                      onClick={() => handleDeleteSegmento(i)}
                      disabled={segmentos.length <= 1}
                      className={`shrink-0 p-1 rounded transition-colors ${
                        segmentos.length <= 1
                          ? "text-gray-200 cursor-not-allowed"
                          : isConfirming
                            ? "text-red-600 bg-red-50"
                            : "text-gray-400 hover:text-red-500 hover:bg-red-50"
                      }`}
                      title={segmentos.length <= 1 ? "Mínimo 1 segmento" : isConfirming ? "Clique para confirmar" : "Excluir segmento"}
                    >
                      {isConfirming ? (
                        <span className="text-[10px] font-semibold whitespace-nowrap">Confirmar?</span>
                      ) : (
                        <Trash2 className="h-4 w-4" />
                      )}
                    </button>
                  </div>
                </div>
                {addingAfterIndex === i ? (
                  <div className="border-l-4 border-l-blue-400 bg-blue-50 rounded-lg p-3 my-1">
                    <div className="flex items-start gap-3">
                      <span className="text-xs mt-1">➕</span>
                      <div className="flex flex-col gap-0.5 shrink-0">
                        <div className="flex items-center gap-1">
                          <Input
                            value={addFormStart}
                            onChange={e => setAddFormStart(e.target.value)}
                            className="w-[85px] h-6 text-xs font-mono"
                            title="Início"
                            placeholder="00:00.000"
                          />
                          <span className="text-xs text-muted-foreground">→</span>
                          <Input
                            value={addFormEnd}
                            onChange={e => setAddFormEnd(e.target.value)}
                            className="w-[85px] h-6 text-xs font-mono"
                            title="Fim"
                            placeholder="00:00.000"
                          />
                        </div>
                      </div>
                      <div className="flex-1">
                        <Input
                          ref={addFormTextRef}
                          value={addFormText}
                          onChange={e => setAddFormText(e.target.value)}
                          onKeyDown={e => {
                            if (e.key === "Enter") handleConfirmAdd()
                            if (e.key === "Escape") handleCancelAdd()
                          }}
                          placeholder="Texto do segmento..."
                          className="h-7 text-sm"
                        />
                      </div>
                    </div>
                    <div className="flex gap-2 mt-2 justify-end">
                      <Button type="button" size="sm" variant="ghost" onClick={handleCancelAdd}>
                        Cancelar
                      </Button>
                      <Button type="button" size="sm" onClick={handleConfirmAdd} className="gap-1">
                        <Check className="h-3.5 w-3.5" />
                        Adicionar
                      </Button>
                    </div>
                  </div>
                ) : (
                  <div className="flex justify-center py-0.5">
                    <button
                      type="button"
                      onClick={() => handleOpenAddForm(i)}
                      className="text-gray-300 hover:text-primary transition-colors p-0.5 rounded hover:bg-gray-100"
                      title="Adicionar segmento após este"
                    >
                      <Plus className="h-3.5 w-3.5" />
                    </button>
                  </div>
                )}
              </div>
            )
          })}
        </div>
        {segmentos.length === 0 && addingAfterIndex === null ? (
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => handleOpenAddForm(-1)}
            className="mt-2 w-full gap-2 border-dashed text-muted-foreground hover:text-primary"
          >
            <Plus className="h-4 w-4" />
            Adicionar primeiro segmento
          </Button>
        ) : segmentos.length === 0 && addingAfterIndex === -1 ? (
          <div className="border-l-4 border-l-blue-400 bg-blue-50 rounded-lg p-3 my-1">
            <div className="flex items-start gap-3">
              <span className="text-xs mt-1">➕</span>
              <div className="flex flex-col gap-0.5 shrink-0">
                <div className="flex items-center gap-1">
                  <Input
                    value={addFormStart}
                    onChange={e => setAddFormStart(e.target.value)}
                    className="w-[85px] h-6 text-xs font-mono"
                    title="Início"
                    placeholder="00:00.000"
                  />
                  <span className="text-xs text-muted-foreground">→</span>
                  <Input
                    value={addFormEnd}
                    onChange={e => setAddFormEnd(e.target.value)}
                    className="w-[85px] h-6 text-xs font-mono"
                    title="Fim"
                    placeholder="00:00.000"
                  />
                </div>
              </div>
              <div className="flex-1">
                <Input
                  ref={addFormTextRef}
                  value={addFormText}
                  onChange={e => setAddFormText(e.target.value)}
                  onKeyDown={e => {
                    if (e.key === "Enter") handleConfirmAdd()
                    if (e.key === "Escape") handleCancelAdd()
                  }}
                  placeholder="Texto do segmento..."
                  className="h-7 text-sm"
                />
              </div>
            </div>
            <div className="flex gap-2 mt-2 justify-end">
              <Button type="button" size="sm" variant="ghost" onClick={handleCancelAdd}>
                Cancelar
              </Button>
              <Button type="button" size="sm" onClick={handleConfirmAdd} className="gap-1">
                <Check className="h-3.5 w-3.5" />
                Adicionar
              </Button>
            </div>
          </div>
        ) : addingAfterIndex === segmentos.length - 1 ? null : segmentos.length > 0 ? (
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => handleOpenAddForm(segmentos.length - 1)}
            className="mt-2 w-full gap-2 border-dashed text-muted-foreground hover:text-primary"
          >
            <Plus className="h-4 w-4" />
            Adicionar segmento
          </Button>
        ) : null}
      </div>

      {/* Actions */}
      <div className="flex gap-3 mt-6 sticky bottom-4">
        <Button
          variant="secondary"
          onClick={handleRetranscrever}
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
