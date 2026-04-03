"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Badge } from "@/components/ui/badge"
import { Loader2, RefreshCw, Star, ChevronDown, ChevronUp } from "lucide-react"
import { cn } from "@/lib/utils"
import { redatorApi, type Project } from "@/lib/api/redator"

export function RedatorApproveHooksRC({ projectId }: { projectId: number }) {
  const router = useRouter()
  const [project, setProject] = useState<Project | null>(null)
  const [loading, setLoading] = useState(true)
  const [selecting, setSelecting] = useState<number | null>(null)
  const [customHook, setCustomHook] = useState("")
  const [submittingCustom, setSubmittingCustom] = useState(false)
  const [regenerating, setRegenerating] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState("")
  const [showDiscarded, setShowDiscarded] = useState(false)
  const [expandedNarrative, setExpandedNarrative] = useState<number | null>(null)

  useEffect(() => {
    redatorApi.getProject(projectId).then(setProject).finally(() => setLoading(false))
  }, [projectId])

  const ganchos = project?.hooks_json?.ganchos || []
  const hasHooks = ganchos.length > 0

  const handleSelect = async (index: number) => {
    setSelecting(index)
    setError("")
    try {
      await redatorApi.selectHook(projectId, { hook_index: index })
    } catch (e: any) {
      setError(`Erro ao selecionar gancho: ${e.message}`)
      setSelecting(null)
      return
    }
    try {
      await redatorApi.generateOverlayRC(projectId)
    } catch (e: any) {
      setError(`Gancho selecionado, mas erro ao gerar overlay: ${e.message}`)
      setSelecting(null)
      return
    }
    router.push(`/redator/projeto/${projectId}/overlay`)
  }

  const handleCustom = async () => {
    if (!customHook.trim()) return
    setSubmittingCustom(true)
    setError("")
    try {
      await redatorApi.selectHook(projectId, { custom_hook: customHook.trim() })
    } catch (e: any) {
      setError(`Erro ao salvar gancho: ${e.message}`)
      setSubmittingCustom(false)
      return
    }
    try {
      await redatorApi.generateOverlayRC(projectId)
    } catch (e: any) {
      setError(`Gancho salvo, mas erro ao gerar overlay: ${e.message}`)
      setSubmittingCustom(false)
      return
    }
    router.push(`/redator/projeto/${projectId}/overlay`)
  }

  const handleRegenerate = async () => {
    setRegenerating(true)
    setError("")
    try {
      await redatorApi.generateHooksRC(projectId)
      const p = await redatorApi.getProject(projectId)
      setProject(p)
    } catch (e: any) {
      setError(`Erro ao regenerar ganchos: ${e.message}`)
    } finally {
      setRegenerating(false)
    }
  }

  const handleGenerate = async () => {
    setGenerating(true)
    setError("")
    try {
      await redatorApi.generateHooksRC(projectId)
      const p = await redatorApi.getProject(projectId)
      setProject(p)
    } catch (e: any) {
      setError(`Erro ao gerar ganchos: ${e.message}`)
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

  // Empty state: hooks not generated yet
  if (!hasHooks) {
    return (
      <div className="mx-auto max-w-3xl space-y-6">
        <div>
          <h1 className="text-xl font-semibold text-foreground">Selecionar Gancho</h1>
          <p className="text-sm text-muted-foreground">{project.composer} — {project.work}</p>
        </div>
        {error && (
          <div className="rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">{error}</div>
        )}
        <Card>
          <CardContent className="p-8 text-center space-y-4">
            <p className="text-sm text-muted-foreground">Ganchos ainda nao foram gerados</p>
            <Button onClick={handleGenerate} disabled={generating}>
              {generating && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {generating ? "Gerando ganchos..." : "Gerar ganchos"}
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  // Separate ranked hooks from discarded
  const ranked = ganchos.filter((_: any, i: number) => i < 5)
  const discarded = ganchos.filter((_: any, i: number) => i >= 5)

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-foreground">Selecionar Gancho</h1>
          <p className="text-sm text-muted-foreground">{project.composer} — {project.work}</p>
        </div>
        <Button variant="outline" size="sm" onClick={handleRegenerate} disabled={regenerating}>
          {regenerating ? <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="mr-2 h-3.5 w-3.5" />}
          {regenerating ? "Regenerando..." : "Regenerar"}
        </Button>
      </div>

      {error && (
        <div className="rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">{error}</div>
      )}

      <div className="space-y-3">
        {ranked.map((gancho: any, i: number) => (
          <Card key={i} className={cn("transition-all", selecting === i && "ring-2 ring-primary")}>
            <CardContent className="p-4 space-y-3">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-2">
                  {i === 0 && <Star className="h-4 w-4 text-amber-500 fill-amber-500" />}
                  <span className="text-xs font-medium text-muted-foreground">#{i + 1}</span>
                  {gancho.angulo && <Badge variant="secondary" className="text-[10px]">{gancho.angulo}</Badge>}
                  {gancho.tipo && <Badge variant="outline" className="text-[10px]">{gancho.tipo}</Badge>}
                </div>
                <Button
                  size="sm"
                  onClick={() => handleSelect(i)}
                  disabled={selecting !== null || submittingCustom}
                >
                  {selecting === i ? (
                    <>
                      <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />
                      Gerando overlay...
                    </>
                  ) : "Selecionar"}
                </Button>
              </div>
              <p className="text-sm font-medium text-foreground leading-relaxed">{gancho.texto}</p>
              {gancho.fio_narrativo && (
                <div>
                  <button
                    type="button"
                    onClick={() => setExpandedNarrative(expandedNarrative === i ? null : i)}
                    className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
                  >
                    {expandedNarrative === i ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                    Fio narrativo
                  </button>
                  {expandedNarrative === i && (
                    <p className="mt-2 text-xs text-muted-foreground leading-relaxed pl-4 border-l-2 border-border">
                      {gancho.fio_narrativo}
                    </p>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      {discarded.length > 0 && (
        <div>
          <button
            type="button"
            onClick={() => setShowDiscarded(!showDiscarded)}
            className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            {showDiscarded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
            Ganchos descartados ({discarded.length})
          </button>
          {showDiscarded && (
            <div className="mt-3 space-y-2">
              {discarded.map((gancho: any, i: number) => (
                <Card key={i} className="opacity-60">
                  <CardContent className="p-3">
                    <p className="text-xs text-muted-foreground">{gancho.texto}</p>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      <Card>
        <CardContent className="p-4 space-y-3">
          <p className="text-sm font-medium text-foreground">Prefiro escrever meu proprio gancho</p>
          <Textarea
            value={customHook}
            onChange={(e) => setCustomHook(e.target.value)}
            placeholder="Escreva seu angulo criativo..."
            className="min-h-[80px] text-sm"
          />
          <Button
            size="sm"
            onClick={handleCustom}
            disabled={!customHook.trim() || selecting !== null || submittingCustom}
          >
            {submittingCustom ? (
              <>
                <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />
                Gerando overlay...
              </>
            ) : "Usar meu gancho"}
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
