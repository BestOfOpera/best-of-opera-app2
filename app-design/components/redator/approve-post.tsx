"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Check, RefreshCw, Copy, Loader2 } from "lucide-react"
import { redatorApi, type Project } from "@/lib/api/redator"

export function RedatorApprovePost({ projectId }: { projectId: number }) {
  const router = useRouter()
  const [project, setProject] = useState<Project | null>(null)
  const [postText, setPostText] = useState("")
  const [loading, setLoading] = useState(true)
  const [regenerating, setRegenerating] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState("")
  const [showPrompt, setShowPrompt] = useState(false)
  const [customPrompt, setCustomPrompt] = useState("")
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    redatorApi.getProject(projectId).then((p) => {
      setProject(p)
      setPostText(p.post_text || "")
    }).finally(() => setLoading(false))
  }, [projectId])

  const handleRegenerate = async () => {
    setRegenerating(true)
    setError("")
    try {
      const p = await redatorApi.regeneratePost(projectId, customPrompt || undefined)
      setProject(p)
      setPostText(p.post_text || "")
      setCustomPrompt("")
      setShowPrompt(false)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setRegenerating(false)
    }
  }

  const handleApprove = async () => {
    setSaving(true)
    setError("")
    try {
      await redatorApi.approvePost(projectId, postText)
      router.push(`/redator/projeto/${projectId}/youtube`)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  const handleCopy = () => {
    navigator.clipboard.writeText(postText)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  if (loading || !project) {
    return <div className="flex items-center justify-center py-12 text-sm text-muted-foreground">Carregando...</div>
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-foreground">Aprovar Post</h1>
          <p className="text-sm text-muted-foreground">{project.artist} — {project.work}</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={handleCopy}>
            <Copy className="mr-2 h-3.5 w-3.5" />
            {copied ? "Copiado!" : "Copiar"}
          </Button>
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
            <Textarea value={customPrompt} onChange={(e) => setCustomPrompt(e.target.value)} placeholder="Prompt personalizado (opcional)" className="min-h-[60px] text-sm" />
            <Button size="sm" onClick={handleRegenerate} disabled={regenerating}>
              {regenerating && <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />}
              {regenerating ? "Regenerando..." : "Regenerar"}
            </Button>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardContent className="p-4">
          <Textarea
            value={postText}
            onChange={(e) => setPostText(e.target.value)}
            className="min-h-[500px] text-sm leading-relaxed"
          />
          <div className="mt-2 flex items-center justify-between text-xs text-muted-foreground">
            <span>{postText.length} caracteres</span>
            <span className={postText.length >= 1600 && postText.length <= 2200 ? "text-emerald-600 font-medium" : "text-amber-600 font-medium"}>
              Max: 2200
            </span>
          </div>
        </CardContent>
      </Card>

      <Card className="bg-muted/30">
        <CardContent className="p-4">
          <p className="text-xs font-medium text-muted-foreground mb-3">Pre-visualizacao</p>
          <div className="whitespace-pre-wrap text-sm leading-relaxed text-foreground">{postText}</div>
        </CardContent>
      </Card>

      <Button className="w-full" onClick={handleApprove} disabled={saving || !postText.trim()}>
        {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
        <Check className="mr-2 h-4 w-4" />
        {saving ? "Salvando..." : "Aprovar e Continuar para YouTube"}
      </Button>
    </div>
  )
}
