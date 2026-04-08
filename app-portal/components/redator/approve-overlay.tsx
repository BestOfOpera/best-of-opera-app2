"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Check, RefreshCw, Trash2, Plus, Loader2, ChevronUp, ChevronDown, Sparkles } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import { redatorApi, type Project } from "@/lib/api/redator"
import { toast } from "sonner"

function parseTimestamp(ts: string): number {
  const parts = ts.split(":")
  return (parseInt(parts[0] || "0") * 60) + parseInt(parts[1] || "0")
}

function formatTimestamp(secs: number): string {
  const m = Math.floor(Math.max(0, secs) / 60)
  const s = Math.floor(Math.max(0, secs) % 60)
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`
}

export function RedatorApproveOverlay({ projectId }: { projectId: number }) {
  const router = useRouter()
  const [project, setProject] = useState<Project | null>(null)
  const [overlay, setOverlay] = useState<{ timestamp: string; text: string }[]>([])
  const [loading, setLoading] = useState(true)
  const [regenerating, setRegenerating] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState("")
  const [showPrompt, setShowPrompt] = useState(false)
  const [customPrompt, setCustomPrompt] = useState("")
  // Individual regeneration
  const [regeneratingIndex, setRegeneratingIndex] = useState<number>(-1)
  const [regenerateInstruction, setRegenerateInstruction] = useState("")
  const [regeneratingEntry, setRegeneratingEntry] = useState(false)
  // Global instruction
  const [globalInstruction, setGlobalInstruction] = useState("")
  const [regeneratingAll, setRegeneratingAll] = useState(false)

  useEffect(() => {
    redatorApi.getProject(projectId).then((p) => {
      setProject(p)
      setOverlay(p.overlay_json || [])
    }).finally(() => setLoading(false))
  }, [projectId])

  const isRC = project?.brand_slug === "reels-classics"

  const handleRegenerate = async () => {
    setRegenerating(true)
    setError("")
    try {
      if (isRC) {
        await redatorApi.generateOverlayRC(projectId)
        const p = await redatorApi.getProject(projectId)
        setProject(p)
        setOverlay(p.overlay_json || [])
      } else {
        const p = await redatorApi.regenerateOverlay(projectId, customPrompt || undefined)
        setProject(p)
        setOverlay(p.overlay_json || [])
      }
      setCustomPrompt("")
      setShowPrompt(false)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setRegenerating(false)
    }
  }

  const handleRegenerateEntry = async (index: number) => {
    setRegeneratingEntry(true)
    try {
      const result = await redatorApi.regenerateOverlayEntry(projectId, index, {
        instruction: regenerateInstruction,
        brand_slug: project?.brand_slug || "",
      })
      setOverlay(result.overlay_json)
      setRegeneratingIndex(-1)
      setRegenerateInstruction("")
      toast.success("Legenda regenerada")
    } catch (e: any) {
      toast.error(e.message || "Erro ao regenerar legenda")
    } finally {
      setRegeneratingEntry(false)
    }
  }

  const handleRegenerateAll = async () => {
    setRegeneratingAll(true)
    try {
      if (isRC) {
        await redatorApi.generateOverlayRC(projectId)
        const p = await redatorApi.getProject(projectId)
        setProject(p)
        setOverlay(p.overlay_json || [])
      } else {
        const p = await redatorApi.regenerateOverlay(projectId, globalInstruction)
        setProject(p)
        setOverlay(p.overlay_json || [])
      }
      setGlobalInstruction("")
      toast.success("Overlay reformulado")
    } catch (e: any) {
      toast.error(e.message || "Erro ao reformular overlay")
    } finally {
      setRegeneratingAll(false)
    }
  }

  const updateEntry = (index: number, field: "timestamp" | "text", value: string) => {
    setOverlay(prev => prev.map((o, i) => i === index ? { ...o, [field]: value } : o))
  }

  const removeEntry = (index: number) => setOverlay(prev => prev.filter((_, i) => i !== index))

  const addEntryAt = (index: number) => {
    const novo = [...overlay]
    let newTimestamp = "00:00"
    if (index > 0 && index < novo.length) {
      const prevTime = parseTimestamp(novo[index - 1].timestamp || "00:00")
      const nextTime = parseTimestamp(novo[index].timestamp || "00:00")
      newTimestamp = formatTimestamp((prevTime + nextTime) / 2)
    } else if (index > 0) {
      const prevTime = parseTimestamp(novo[index - 1].timestamp || "00:00")
      newTimestamp = formatTimestamp(prevTime + 5)
    }
    novo.splice(index, 0, { text: "", timestamp: newTimestamp })
    setOverlay(novo)
  }

  const addEntry = () => addEntryAt(overlay.length)

  const moveEntry = (from: number, to: number) => {
    const novo = [...overlay]
    const [moved] = novo.splice(from, 1)
    novo.splice(to, 0, moved)
    setOverlay(novo)
  }

  const handleApprove = async () => {
    setSaving(true)
    setError("")
    try {
      await redatorApi.approveOverlay(projectId, overlay)
    } catch (err: any) {
      setError(err.message)
      setSaving(false)
      return
    }
    if (isRC) {
      try {
        await redatorApi.generatePostRC(projectId)
      } catch (e: any) {
        // Overlay aprovado mas descrição falhou — redirecionar mesmo assim
      }
    }
    router.push(`/redator/projeto/${projectId}/post`)
    setSaving(false)
  }

  if (loading || !project) {
    return <div className="flex items-center justify-center py-12 text-sm text-muted-foreground">Carregando...</div>
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-foreground">Aprovar Overlay</h1>
          <p className="text-sm text-muted-foreground">{project.artist} — {project.work} · {overlay.length} legendas</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => setShowPrompt(!showPrompt)}>
            <RefreshCw className="mr-2 h-3.5 w-3.5" />
            Regenerar
          </Button>
        </div>
      </div>

      {overlay.length === 0 && !regenerating && (
        <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-700">
          Nenhuma legenda gerada. Clique em &quot;Regenerar&quot; para gerar o overlay.
        </div>
      )}

      {error && (
        <div className="rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">{error}</div>
      )}

      {showPrompt && (
        <Card>
          <CardContent className="p-4 space-y-3">
            <Textarea
              value={customPrompt}
              onChange={(e) => setCustomPrompt(e.target.value)}
              placeholder="Prompt personalizado (opcional)"
              className="min-h-[60px] text-sm"
            />
            <Button size="sm" onClick={handleRegenerate} disabled={regenerating}>
              {regenerating && <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />}
              {regenerating ? "Regenerando..." : "Regenerar"}
            </Button>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardContent className="p-0">
          <div className="divide-y divide-border">
            {overlay.map((entry, i) => {
              const isCta = (entry as any)._is_cta === true
              return (
                <div key={i}>
                  {/* Insert button between entries */}
                  {i > 0 && (
                    <div className="flex justify-center py-0.5 border-b border-dashed border-border/50">
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-5 w-full max-w-[200px] text-[10px] text-muted-foreground hover:text-foreground"
                        onClick={() => addEntryAt(i)}
                      >
                        + inserir legenda
                      </Button>
                    </div>
                  )}
                  <div className={cn("flex items-start gap-2 px-4 py-2.5", isCta && "bg-muted/30")}>
                    <span className="text-xs font-medium text-muted-foreground tabular-nums w-8 pt-2">
                      {isCta ? "CTA" : i + 1}
                    </span>
                    <Input
                      value={entry.timestamp}
                      onChange={(e) => updateEntry(i, "timestamp", e.target.value)}
                      className="w-20 font-mono text-xs"
                    />
                    <Textarea
                      value={entry.text}
                      onChange={(e) => updateEntry(i, "text", e.target.value)}
                      className="flex-1 text-sm min-h-0 py-1.5 resize-none"
                      rows={1}
                    />
                    {(() => {
                      if (isRC) {
                        const longest = Math.max(...(entry.text.split("\n").map((l: string) => l.length)), 0)
                        const over = longest > 33
                        return (
                          <span className={`text-[10px] tabular-nums w-14 text-right pt-2 ${over ? "text-destructive font-medium" : "text-muted-foreground"}`}>
                            {longest}/33 lin
                          </span>
                        )
                      }
                      const over = entry.text.length > 70
                      return (
                        <span className={`text-[10px] tabular-nums w-10 text-right pt-2 ${over ? "text-destructive font-medium" : "text-muted-foreground"}`}>
                          {entry.text.length}/70
                        </span>
                      )
                    })()}
                    <div className="flex flex-col gap-0.5 shrink-0">
                      {/* Move up */}
                      {i > 0 && !isCta && (
                        <Button variant="ghost" size="icon-xs" className="text-muted-foreground hover:text-foreground" onClick={() => moveEntry(i, i - 1)} title="Mover para cima">
                          <ChevronUp className="h-3 w-3" />
                        </Button>
                      )}
                      {/* Move down */}
                      {i < overlay.length - 1 && !isCta && (
                        <Button variant="ghost" size="icon-xs" className="text-muted-foreground hover:text-foreground" onClick={() => moveEntry(i, i + 1)} title="Mover para baixo">
                          <ChevronDown className="h-3 w-3" />
                        </Button>
                      )}
                      {/* Regenerate individual */}
                      {!isCta && (
                        <Button
                          variant="ghost"
                          size="icon-xs"
                          className="text-muted-foreground hover:text-primary"
                          onClick={() => setRegeneratingIndex(regeneratingIndex === i ? -1 : i)}
                          title="Regenerar esta legenda com IA"
                        >
                          <Sparkles className="h-3 w-3" />
                        </Button>
                      )}
                      {/* Delete */}
                      {isCta ? (
                        <Badge variant="secondary" className="text-[9px] shrink-0">CTA</Badge>
                      ) : (
                        <Button variant="ghost" size="icon-xs" className="text-muted-foreground hover:text-destructive" onClick={() => removeEntry(i)}>
                          <Trash2 className="h-3 w-3" />
                        </Button>
                      )}
                    </div>
                  </div>
                  {/* Inline instruction for individual regeneration */}
                  {regeneratingIndex === i && (
                    <div className="flex gap-2 px-4 pb-2">
                      <Input
                        placeholder="Instrucao para a IA (opcional): ex. 'mais emocional', 'mencionar a estreia'..."
                        value={regenerateInstruction}
                        onChange={(e) => setRegenerateInstruction(e.target.value)}
                        className="flex-1 text-xs"
                        onKeyDown={(e) => { if (e.key === "Enter") handleRegenerateEntry(i) }}
                      />
                      <Button size="sm" onClick={() => handleRegenerateEntry(i)} disabled={regeneratingEntry} className="text-xs">
                        {regeneratingEntry && <Loader2 className="mr-1 h-3 w-3 animate-spin" />}
                        {regeneratingEntry ? "..." : "Regenerar"}
                      </Button>
                      <Button variant="ghost" size="sm" className="text-xs" onClick={() => { setRegeneratingIndex(-1); setRegenerateInstruction("") }}>
                        Cancelar
                      </Button>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
          <div className="px-4 py-2 border-t">
            <Button variant="ghost" size="sm" onClick={addEntry}>
              <Plus className="mr-1 h-3.5 w-3.5" />
              Adicionar Legenda
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Global instruction for reformulating entire overlay */}
      <Card>
        <CardContent className="p-4 space-y-2">
          <div className="flex items-start gap-2">
            <Textarea
              placeholder="Observacoes para a IA reformular o overlay: ex. 'tom mais dramatico', 'focar na historia do compositor', 'menos artificial'..."
              value={globalInstruction}
              onChange={(e) => setGlobalInstruction(e.target.value)}
              className="flex-1 text-sm min-h-0 resize-none"
              rows={2}
            />
            <Button
              size="sm"
              disabled={!globalInstruction.trim() || regeneratingAll}
              onClick={handleRegenerateAll}
            >
              {regeneratingAll && <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" />}
              {regeneratingAll ? "Reformulando..." : "Reformular"}
            </Button>
          </div>
          <p className="text-[10px] text-muted-foreground">
            A IA reformulara todas as legendas mantendo a estrutura.
          </p>
        </CardContent>
      </Card>

      <Button className="w-full" onClick={handleApprove} disabled={saving || overlay.length === 0}>
        {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
        <Check className="mr-2 h-4 w-4" />
        {saving ? (isRC ? "Gerando descricao..." : "Salvando...") : (isRC ? "Aprovar e Gerar Descricao" : "Aprovar e Continuar para o Post")}
      </Button>
    </div>
  )
}
