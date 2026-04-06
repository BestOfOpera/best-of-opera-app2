"use client"

import { useState, useEffect, useRef } from "react"
import { editorApi, Edicao, Render } from "@/lib/api/editor"
import { Project } from "@/lib/api/redator"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  ChevronDown,
  Download,
  Package,
  Copy,
  CheckCircle2,
  Circle,
  Loader2,
  AlertCircle,
  RefreshCw,
} from "lucide-react"
import { toast } from "sonner"
import { cn } from "@/lib/utils"

const IDIOMAS = [
  { code: "en", flag: "\u{1F1EC}\u{1F1E7}", label: "Ingl\u00eas" },
  { code: "pt", flag: "\u{1F1E7}\u{1F1F7}", label: "Portugu\u00eas" },
  { code: "es", flag: "\u{1F1EA}\u{1F1F8}", label: "Espanhol" },
  { code: "de", flag: "\u{1F1E9}\u{1F1EA}", label: "Alem\u00e3o" },
  { code: "fr", flag: "\u{1F1EB}\u{1F1F7}", label: "Franc\u00eas" },
  { code: "it", flag: "\u{1F1EE}\u{1F1F9}", label: "Italiano" },
  { code: "pl", flag: "\u{1F1F5}\u{1F1F1}", label: "Polon\u00eas" },
]

function formatBytes(bytes: number | null): string {
  if (!bytes) return "-"
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return "-"
  return new Date(dateStr).toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric" })
}

interface FinalizadoCardProps {
  edicao: Edicao
  redatorProject: Project | null
  onRefresh: () => void
}

export function FinalizadoCard({ edicao, redatorProject, onRefresh }: FinalizadoCardProps) {
  const [expanded, setExpanded] = useState(false)
  const [renders, setRenders] = useState<Render[]>([])
  const [loadingRenders, setLoadingRenders] = useState(false)
  const [postLang, setPostLang] = useState("pt")
  const [publishing, setPublishing] = useState(false)
  const [baixandoZip, setBaixandoZip] = useState(false)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const rendersLoaded = useRef(false)

  // Load renders on first expand
  useEffect(() => {
    if (expanded && !rendersLoaded.current) {
      rendersLoaded.current = true
      setLoadingRenders(true)
      editorApi.listarRenders(edicao.id)
        .then(setRenders)
        .catch(() => toast.error("Erro ao carregar renders"))
        .finally(() => setLoadingRenders(false))
    }
  }, [expanded, edicao.id])

  // Cleanup poll on unmount
  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [])

  const concluidos = renders.filter((r) => r.status === "concluido")
  const erros = renders.filter((r) => r.status === "erro")

  const handleDownloadRender = (renderId: number) => {
    window.open(editorApi.downloadRenderUrl(edicao.id, renderId), "_blank")
  }

  const handleDownloadZip = async () => {
    setBaixandoZip(true)
    try {
      await editorApi.iniciarPacote(edicao.id)
      // Poll status
      pollRef.current = setInterval(async () => {
        try {
          const status = await editorApi.statusPacote(edicao.id)
          if (status.status === "pronto") {
            if (pollRef.current) clearInterval(pollRef.current)
            pollRef.current = null
            setBaixandoZip(false)
            window.open(editorApi.pacoteDownloadUrl(edicao.id), "_blank")
          } else if (status.status === "erro") {
            if (pollRef.current) clearInterval(pollRef.current)
            pollRef.current = null
            setBaixandoZip(false)
            toast.error("Erro ao gerar pacote ZIP")
          }
        } catch {
          if (pollRef.current) clearInterval(pollRef.current)
          pollRef.current = null
          setBaixandoZip(false)
          toast.error("Erro ao verificar status do pacote")
        }
      }, 2000)
    } catch {
      setBaixandoZip(false)
      toast.error("Erro ao iniciar pacote")
    }
  }

  const handleCopyPost = (text: string) => {
    navigator.clipboard.writeText(text)
    toast.success("Post copiado!")
  }

  const handleTogglePublished = async () => {
    setPublishing(true)
    try {
      await editorApi.marcarPublicado(edicao.id)
      toast.success(edicao.published_at ? "Publicação removida" : "Marcado como publicado!")
      onRefresh()
    } catch {
      toast.error("Erro ao atualizar publicação")
    } finally {
      setPublishing(false)
    }
  }

  // Get post text for selected language
  const getPostText = (): string | null => {
    if (!redatorProject) return null
    if (postLang === "pt") return redatorProject.post_text
    const translation = redatorProject.translations?.find((t) => t.language === postLang)
    return translation?.post_text ?? null
  }

  const postText = getPostText()
  const isPublished = !!edicao.published_at
  const isRC = redatorProject?.brand_slug === "reels-classics"

  return (
    <Card className="transition-shadow hover:shadow-md">
      <CardHeader
        className="cursor-pointer select-none"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-3 w-full">
          <div className="flex-1 min-w-0">
            <CardTitle className="text-base font-semibold truncate">
              {edicao.artista} — {edicao.musica}
            </CardTitle>
            <p className="text-xs text-muted-foreground mt-0.5">
              {edicao.compositor && `${edicao.compositor} · `}
              {edicao.opera && `${edicao.opera} · `}
              {formatDate(edicao.created_at)}
            </p>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {isPublished ? (
              <Badge variant="default" className="bg-green-600 text-white text-[10px]">Publicado</Badge>
            ) : (
              <Badge variant="secondary" className="text-[10px]">Pendente</Badge>
            )}
            <ChevronDown className={cn("h-4 w-4 text-muted-foreground transition-transform", expanded && "rotate-180")} />
          </div>
        </div>
      </CardHeader>

      {expanded && (
        <CardContent className="space-y-6 pt-0">
          {/* --- Section A: Renders --- */}
          <div>
            <h4 className="text-sm font-semibold mb-3 flex items-center gap-2">
              <Download className="h-4 w-4" />
              Videos Renderizados
              {!loadingRenders && renders.length > 0 && (
                <span className="text-xs text-muted-foreground font-normal">
                  ({concluidos.length}/{IDIOMAS.length} concluidos{erros.length > 0 && `, ${erros.length} erros`})
                </span>
              )}
            </h4>
            {loadingRenders ? (
              <div className="flex items-center gap-2 text-sm text-muted-foreground py-4">
                <Loader2 className="h-4 w-4 animate-spin" /> Carregando renders...
              </div>
            ) : (
              <div className="grid gap-1.5">
                {IDIOMAS.map(({ code, flag, label }) => {
                  const render = renders.find((r) => r.idioma === code)
                  const isConcluido = render?.status === "concluido"
                  const isErro = render?.status === "erro"
                  return (
                    <div
                      key={code}
                      className={cn(
                        "flex items-center gap-3 py-2 px-3 rounded-lg text-sm",
                        isConcluido ? "bg-green-50" : isErro ? "bg-red-50" : "bg-muted/50"
                      )}
                    >
                      <span className="text-base">{flag}</span>
                      <span className="flex-1 font-medium">{label}</span>
                      {render && <span className="text-xs text-muted-foreground">{formatBytes(render.tamanho_bytes)}</span>}
                      {isConcluido && render ? (
                        <Button
                          size="sm"
                          variant="ghost"
                          className="h-7 gap-1.5 text-xs"
                          onClick={() => handleDownloadRender(render.id)}
                        >
                          <Download className="h-3 w-3" /> Baixar
                        </Button>
                      ) : isErro ? (
                        <span className="text-xs text-red-600 flex items-center gap-1">
                          <AlertCircle className="h-3 w-3" /> Erro
                        </span>
                      ) : (
                        <span className="text-xs text-muted-foreground">—</span>
                      )}
                    </div>
                  )
                })}
              </div>
            )}
            {/* ZIP download */}
            {concluidos.length > 0 && (
              <Button
                size="sm"
                variant="outline"
                className="mt-3 gap-1.5"
                onClick={handleDownloadZip}
                disabled={baixandoZip}
              >
                {baixandoZip ? <RefreshCw className="h-3.5 w-3.5 animate-spin" /> : <Package className="h-3.5 w-3.5" />}
                {baixandoZip ? "Gerando pacote..." : "Baixar ZIP completo"}
              </Button>
            )}
          </div>

          {/* --- Section B: Posts / Descriptions --- */}
          <div>
            <h4 className="text-sm font-semibold mb-3 flex items-center gap-2">
              <Copy className="h-4 w-4" />
              Post / Descricao
            </h4>
            {redatorProject ? (
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <Select value={postLang} onValueChange={setPostLang}>
                    <SelectTrigger className="w-[160px] h-8 text-xs">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {IDIOMAS.map(({ code, flag, label }) => (
                        <SelectItem key={code} value={code}>
                          {flag} {label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {postText && (
                    <Button
                      size="sm"
                      variant="outline"
                      className="h-8 gap-1.5 text-xs"
                      onClick={() => handleCopyPost(postText)}
                    >
                      <Copy className="h-3 w-3" /> Copiar
                    </Button>
                  )}
                </div>
                {postText ? (
                  <div className="bg-muted/50 rounded-lg p-3 text-sm whitespace-pre-wrap max-h-48 overflow-y-auto">
                    {postText}
                  </div>
                ) : (
                  <p className="text-xs text-muted-foreground py-2">
                    Sem post disponivel para este idioma.
                  </p>
                )}
              </div>
            ) : (
              <p className="text-xs text-muted-foreground py-2">
                Projeto redator nao vinculado — dados de post indisponiveis.
              </p>
            )}
          </div>

          {/* --- Section C: Automation (RC only) --- */}
          {isRC && redatorProject?.automation_json && (
            <div>
              <h4 className="text-sm font-semibold mb-3">Automacao (RC)</h4>
              <div className="space-y-2">
                {Object.entries(redatorProject.automation_json).map(([key, value]) => (
                  <div key={key} className="flex items-start gap-2">
                    <span className="text-xs font-medium text-muted-foreground uppercase min-w-[80px] pt-0.5">{key}:</span>
                    <div className="flex-1 text-sm bg-muted/50 rounded px-2 py-1 whitespace-pre-wrap">
                      {typeof value === "string" ? value : JSON.stringify(value, null, 2)}
                    </div>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-7 shrink-0"
                      onClick={() => {
                        navigator.clipboard.writeText(typeof value === "string" ? value : JSON.stringify(value))
                        toast.success(`${key} copiado!`)
                      }}
                    >
                      <Copy className="h-3 w-3" />
                    </Button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* --- Section D: Publish toggle --- */}
          <div className="flex items-center gap-3 pt-2 border-t border-border">
            <Button
              size="sm"
              variant={isPublished ? "outline" : "default"}
              className={cn("gap-1.5", isPublished && "text-green-700 border-green-300 hover:bg-green-50")}
              onClick={handleTogglePublished}
              disabled={publishing}
            >
              {publishing ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : isPublished ? (
                <CheckCircle2 className="h-3.5 w-3.5" />
              ) : (
                <Circle className="h-3.5 w-3.5" />
              )}
              {isPublished ? "Publicado" : "Marcar como publicado"}
            </Button>
            {isPublished && edicao.published_at && (
              <span className="text-xs text-muted-foreground">
                em {formatDate(edicao.published_at)}
              </span>
            )}
          </div>
        </CardContent>
      )}
    </Card>
  )
}
