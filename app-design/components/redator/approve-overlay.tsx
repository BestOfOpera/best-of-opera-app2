"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Check, RefreshCw, Trash2, Plus, Loader2 } from "lucide-react"
import { redatorApi, type Project } from "@/lib/api/redator"

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

  useEffect(() => {
    redatorApi.getProject(projectId).then((p) => {
      setProject(p)
      setOverlay(p.overlay_json || [])
    }).finally(() => setLoading(false))
  }, [projectId])

  const handleRegenerate = async () => {
    setRegenerating(true)
    setError("")
    try {
      const p = await redatorApi.regenerateOverlay(projectId, customPrompt || undefined)
      setProject(p)
      setOverlay(p.overlay_json || [])
      setCustomPrompt("")
      setShowPrompt(false)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setRegenerating(false)
    }
  }

  const updateEntry = (index: number, field: "timestamp" | "text", value: string) => {
    setOverlay(prev => prev.map((o, i) => i === index ? { ...o, [field]: value } : o))
  }

  const removeEntry = (index: number) => setOverlay(prev => prev.filter((_, i) => i !== index))
  const addEntry = () => setOverlay(prev => [...prev, { timestamp: "00:00", text: "" }])

  const handleApprove = async () => {
    setSaving(true)
    setError("")
    try {
      await redatorApi.approveOverlay(projectId, overlay)
      router.push(`/redator/projeto/${projectId}/post`)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
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
            {overlay.map((entry, i) => (
              <div key={i} className="flex items-center gap-3 px-4 py-2.5">
                <span className="text-xs font-medium text-muted-foreground tabular-nums w-8">{i + 1}</span>
                <Input
                  value={entry.timestamp}
                  onChange={(e) => updateEntry(i, "timestamp", e.target.value)}
                  className="w-20 font-mono text-xs"
                />
                <Input
                  value={entry.text}
                  onChange={(e) => updateEntry(i, "text", e.target.value)}
                  className="flex-1 text-sm"
                />
                <span className={`text-[10px] tabular-nums w-10 text-right ${entry.text.length > 70 ? "text-destructive font-medium" : "text-muted-foreground"}`}>
                  {entry.text.length}/70
                </span>
                <Button variant="ghost" size="icon-xs" className="text-muted-foreground hover:text-destructive" onClick={() => removeEntry(i)}>
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              </div>
            ))}
          </div>
          <div className="px-4 py-2 border-t">
            <Button variant="ghost" size="sm" onClick={addEntry}>
              <Plus className="mr-1 h-3.5 w-3.5" />
              Adicionar Legenda
            </Button>
          </div>
        </CardContent>
      </Card>

      <Button className="w-full" onClick={handleApprove} disabled={saving || overlay.length === 0}>
        {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
        <Check className="mr-2 h-4 w-4" />
        {saving ? "Salvando..." : "Aprovar e Continuar para o Post"}
      </Button>
    </div>
  )
}
