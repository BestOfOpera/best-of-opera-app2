"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { Check, RefreshCw, Loader2 } from "lucide-react"
import { redatorApi, type Project } from "@/lib/api/redator"

export function RedatorApproveYouTube({ projectId }: { projectId: number }) {
  const router = useRouter()
  const [project, setProject] = useState<Project | null>(null)
  const [title, setTitle] = useState("")
  const [tags, setTags] = useState("")
  const [loading, setLoading] = useState(true)
  const [regenerating, setRegenerating] = useState(false)
  const [saving, setSaving] = useState(false)
  const [translating, setTranslating] = useState(false)
  const [error, setError] = useState("")
  const [showPrompt, setShowPrompt] = useState(false)
  const [customPrompt, setCustomPrompt] = useState("")

  useEffect(() => {
    redatorApi.getProject(projectId).then((p) => {
      setProject(p)
      setTitle(p.youtube_title || "")
      setTags(p.youtube_tags || "")
    }).finally(() => setLoading(false))
  }, [projectId])

  const handleRegenerate = async () => {
    setRegenerating(true)
    setError("")
    try {
      const p = await redatorApi.regenerateYoutube(projectId, customPrompt || undefined)
      setProject(p)
      setTitle(p.youtube_title || "")
      setTags(p.youtube_tags || "")
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
      let p = await redatorApi.approveYoutube(projectId, title, tags)
      setProject(p)
      if (p.overlay_approved && p.post_approved) {
        setTranslating(true)
        try {
          await redatorApi.translate(projectId)
        } catch {
          // Translation failure is non-blocking
        } finally {
          setTranslating(false)
        }
      }
      router.push(`/redator/projeto/${projectId}/exportar`)
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
          <h1 className="text-xl font-semibold text-foreground">Aprovar YouTube</h1>
          <p className="text-sm text-muted-foreground">{project.artist} — {project.work}</p>
        </div>
        <Button variant="outline" size="sm" onClick={() => setShowPrompt(!showPrompt)}>
          <RefreshCw className="mr-2 h-3.5 w-3.5" />
          Regenerar
        </Button>
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
        <CardHeader>
          <CardTitle className="text-sm">Preview SEO</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="rounded-lg bg-muted/30 p-4">
            <p className="text-base font-medium text-blue-700 leading-snug">{title}</p>
            <p className="mt-1 text-xs text-emerald-700">youtube.com &gt; Best of Opera</p>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label>Titulo</Label>
              <span className="text-[11px] text-muted-foreground tabular-nums">{title.length}/100</span>
            </div>
            <Input value={title} onChange={(e) => setTitle(e.target.value)} />
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label>Tags</Label>
              <span className="text-[11px] text-muted-foreground tabular-nums">{tags.length}/450</span>
            </div>
            <Textarea value={tags} onChange={(e) => setTags(e.target.value)} className="min-h-[80px] text-sm" />
            <div className="flex flex-wrap gap-1">
              {tags.split(",").filter(Boolean).map((tag, i) => (
                <span key={i} className="rounded bg-muted px-2 py-0.5 text-[11px] text-muted-foreground">
                  {tag.trim()}
                </span>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      <Button className="w-full" onClick={handleApprove} disabled={saving || translating || !title.trim()}>
        {(saving || translating) && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
        <Check className="mr-2 h-4 w-4" />
        {translating ? "Traduzindo para 6 idiomas..." : saving ? "Salvando..." : "Aprovar e Traduzir"}
      </Button>
    </div>
  )
}
