"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Check, RefreshCw, ArrowLeft, Loader2 } from "lucide-react"
import { redatorApi, type Project } from "@/lib/api/redator"

export function RedatorApproveAutomationRC({ projectId }: { projectId: number }) {
  const router = useRouter()
  const [project, setProject] = useState<Project | null>(null)
  const [loading, setLoading] = useState(true)
  const [approving, setApproving] = useState(false)
  const [regenerating, setRegenerating] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState("")
  const [videoLink, setVideoLink] = useState("")

  useEffect(() => {
    redatorApi.getProject(projectId).then(setProject).finally(() => setLoading(false))
  }, [projectId])

  const automation = project?.automation_json as any

  const handleApprove = async () => {
    setApproving(true)
    setError("")
    try {
      await redatorApi.approveAutomation(projectId)
      router.push(`/redator/projeto/${projectId}/exportar`)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setApproving(false)
    }
  }

  const handleRegenerate = async () => {
    setRegenerating(true)
    setError("")
    try {
      await redatorApi.generateAutomationRC(projectId)
      const p = await redatorApi.getProject(projectId)
      setProject(p)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setRegenerating(false)
    }
  }

  const handleGenerate = async () => {
    setGenerating(true)
    setError("")
    try {
      await redatorApi.generateAutomationRC(projectId)
      const p = await redatorApi.getProject(projectId)
      setProject(p)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setGenerating(false)
    }
  }

  if (loading) {
    return <div className="flex items-center justify-center py-12 text-sm text-muted-foreground">Carregando...</div>
  }

  if (!project) {
    return <div className="flex items-center justify-center py-12 text-sm text-destructive">Projeto nao encontrado</div>
  }

  // Empty state
  if (!automation) {
    return (
      <div className="mx-auto max-w-3xl space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-foreground">Aprovar Automacao</h1>
            <p className="text-sm text-muted-foreground">{project.artist} — {project.work}</p>
          </div>
          <Button variant="outline" size="sm" onClick={() => router.push(`/redator/projeto/${projectId}/post`)}>
            <ArrowLeft className="mr-2 h-3.5 w-3.5" />
            Voltar
          </Button>
        </div>
        {error && (
          <div className="rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">{error}</div>
        )}
        <Card>
          <CardContent className="p-8 text-center space-y-4">
            <p className="text-sm text-muted-foreground">Automacao ainda nao foi gerada</p>
            <Button onClick={handleGenerate} disabled={generating}>
              {generating && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {generating ? "Gerando automacao..." : "Gerar automacao"}
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  const respostasCurtas = automation.respostas_curtas || []
  const dmFixa = automation.dm_fixa || ""
  const comentarioObj = automation.comentario_keyword || {}
  const comentarioKeyword = typeof comentarioObj === "string" ? comentarioObj : (comentarioObj.texto_completo || "")
  const keyword = typeof comentarioObj === "string" ? "" : (comentarioObj.keyword || "")

  const dmPreview = videoLink ? dmFixa.replace("[link]", videoLink) : dmFixa

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-foreground">Aprovar Automacao</h1>
          <p className="text-sm text-muted-foreground">{project.artist} — {project.work}</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => router.push(`/redator/projeto/${projectId}/post`)}>
            <ArrowLeft className="mr-2 h-3.5 w-3.5" />
            Voltar
          </Button>
          <Button variant="outline" size="sm" onClick={handleRegenerate} disabled={regenerating}>
            {regenerating ? <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="mr-2 h-3.5 w-3.5" />}
            {regenerating ? "Regenerando..." : "Regenerar"}
          </Button>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">{error}</div>
      )}

      {/* Section 1: Respostas Curtas */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Respostas Curtas (ManyChat)</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {respostasCurtas.length > 0 ? (
            respostasCurtas.map((resp: string, i: number) => (
              <div key={i} className="space-y-1">
                <Label className="text-xs text-muted-foreground">Resposta {i + 1}</Label>
                <div className="rounded-md border bg-muted/30 px-3 py-2 text-sm">{resp}</div>
              </div>
            ))
          ) : (
            <p className="text-sm text-muted-foreground">Nenhuma resposta curta gerada</p>
          )}
        </CardContent>
      </Card>

      {/* Section 2: DM Fixa */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Mensagem DM Fixa</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="rounded-md border bg-muted/30 px-3 py-2 text-sm whitespace-pre-wrap">{dmFixa}</div>
          <div className="space-y-1">
            <Label className="text-xs">Link do video (substituir [link])</Label>
            <Input
              value={videoLink}
              onChange={(e) => setVideoLink(e.target.value)}
              placeholder="https://..."
            />
          </div>
          {videoLink && (
            <div className="space-y-1">
              <Label className="text-xs text-muted-foreground">Preview da DM</Label>
              <div className="rounded-md border border-primary/20 bg-primary/5 px-3 py-2 text-sm whitespace-pre-wrap">{dmPreview}</div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Section 3: Comentário Keyword */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Comentario Keyword</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <div className="rounded-md border bg-muted/30 px-3 py-2 text-sm whitespace-pre-wrap">{comentarioKeyword}</div>
          {keyword && (
            <p className="text-xs text-muted-foreground">
              Keyword: <span className="font-bold text-foreground uppercase">{keyword}</span>
            </p>
          )}
        </CardContent>
      </Card>

      <Button className="w-full" onClick={handleApprove} disabled={approving}>
        {approving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
        <Check className="mr-2 h-4 w-4" />
        {approving ? "Aprovando..." : "Aprovar e Continuar para Exportar"}
      </Button>
    </div>
  )
}
