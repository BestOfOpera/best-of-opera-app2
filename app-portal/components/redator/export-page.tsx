"use client"

import { useEffect, useState } from "react"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Download, FolderOpen, Copy, Loader2 } from "lucide-react"
import { redatorApi, type Project, type ExportData } from "@/lib/api/redator"

const LANGUAGES = [
  { code: "pt", name: "Portugues", flag: "🇧🇷" },
  { code: "en", name: "English", flag: "🇬🇧" },
  { code: "es", name: "Espanol", flag: "🇪🇸" },
  { code: "fr", name: "Francais", flag: "🇫🇷" },
  { code: "de", name: "Deutsch", flag: "🇩🇪" },
  { code: "it", name: "Italiano", flag: "🇮🇹" },
  { code: "pl", name: "Polski", flag: "🇵🇱" },
]

export function RedatorExportPage({ projectId }: { projectId: number }) {
  const [project, setProject] = useState<Project | null>(null)
  const [activeLang, setActiveLang] = useState("pt")
  const [exportData, setExportData] = useState<ExportData | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadingLang, setLoadingLang] = useState(false)
  const [translating, setTranslating] = useState(false)
  const [retranslating, setRetranslating] = useState(false)
  const [error, setError] = useState("")

  const [editingPost, setEditingPost] = useState(false)
  const [editPostText, setEditPostText] = useState("")
  const [editingYt, setEditingYt] = useState(false)
  const [editYtTitle, setEditYtTitle] = useState("")
  const [editYtTags, setEditYtTags] = useState("")
  const [editingOverlay, setEditingOverlay] = useState(false)
  const [editOverlay, setEditOverlay] = useState<{ timestamp: string; text: string }[]>([])
  const [saving, setSaving] = useState(false)

  const [hasExportPath, setHasExportPath] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [exportSuccess, setExportSuccess] = useState("")

  useEffect(() => {
    redatorApi.getProject(projectId).then(setProject).finally(() => setLoading(false))
    redatorApi.getExportConfig().then(c => setHasExportPath(!!c.export_path)).catch(() => {})
  }, [projectId])

  const loadLang = (lang: string) => {
    setLoadingLang(true)
    setEditingPost(false)
    setEditingYt(false)
    setEditingOverlay(false)
    redatorApi.exportLang(projectId, lang)
      .then(setExportData)
      .catch(() => setExportData(null))
      .finally(() => setLoadingLang(false))
  }

  useEffect(() => { loadLang(activeLang) }, [projectId, activeLang])

  const handleTranslate = async () => {
    setTranslating(true)
    setError("")
    try {
      const p = await redatorApi.translate(projectId)
      setProject(p)
      loadLang(activeLang)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setTranslating(false)
    }
  }

  const handleRetranslate = async () => {
    setRetranslating(true)
    setError("")
    try {
      await redatorApi.retranslate(projectId, activeLang)
      loadLang(activeLang)
    } catch (err: any) {
      setError("Erro ao retraduzir: " + err.message)
    } finally {
      setRetranslating(false)
    }
  }

  const handleSave = async (type: "post" | "yt" | "overlay") => {
    setSaving(true)
    try {
      if (type === "post") {
        await redatorApi.updateTranslation(projectId, activeLang, { post_text: editPostText })
        setEditingPost(false)
      } else if (type === "yt") {
        await redatorApi.updateTranslation(projectId, activeLang, { youtube_title: editYtTitle, youtube_tags: editYtTags })
        setEditingYt(false)
      } else {
        await redatorApi.updateTranslation(projectId, activeLang, { overlay_json: editOverlay })
        setEditingOverlay(false)
      }
      loadLang(activeLang)
    } catch (err: any) {
      setError("Erro ao salvar: " + err.message)
    } finally {
      setSaving(false)
    }
  }

  const downloadSrt = () => {
    if (!exportData?.srt) return
    const blob = new Blob([exportData.srt], { type: "text/plain" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = `subtitles_${activeLang}.srt`
    a.click()
    URL.revokeObjectURL(url)
  }

  const copyText = (text: string) => navigator.clipboard.writeText(text)

  if (loading || !project) {
    return <div className="flex items-center justify-center py-12 text-sm text-muted-foreground">Carregando...</div>
  }

  const hasTranslations = project.translations.length > 0

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-foreground">Exportar</h1>
          <p className="text-sm text-muted-foreground">{project.artist} — {project.work} · 7 idiomas</p>
        </div>
        <div className="flex gap-2">
          {hasExportPath && (
            <Button variant="outline" size="sm" disabled={exporting} onClick={async () => {
              setExporting(true); setExportSuccess(""); setError("")
              try {
                const res = await redatorApi.exportToFolder(projectId)
                setExportSuccess(`Exportado para: ${res.path}`)
              } catch (err: any) { setError("Erro ao exportar: " + err.message) }
              finally { setExporting(false) }
            }}>
              <FolderOpen className="mr-2 h-3.5 w-3.5" />
              {exporting ? "Exportando..." : "Exportar para Pasta"}
            </Button>
          )}
          <a href={redatorApi.exportZipUrl(projectId)} download>
            <Button size="sm">
              <Download className="mr-2 h-3.5 w-3.5" />
              Baixar ZIP
            </Button>
          </a>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">{error}</div>
      )}
      {exportSuccess && (
        <div className="rounded-lg border border-emerald-300 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">{exportSuccess}</div>
      )}

      <div className="flex gap-2 flex-wrap">
        <Button variant={hasTranslations ? "outline" : "default"} size="sm" onClick={handleTranslate} disabled={translating}>
          {translating && <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />}
          {translating ? "Traduzindo..." : hasTranslations ? "Retraduzir tudo" : "Traduzir para 7 idiomas"}
        </Button>
        {hasTranslations && (
          <Button variant="outline" size="sm" onClick={handleRetranslate} disabled={retranslating}>
            {retranslating && <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />}
            {retranslating ? "Retraduzindo..." : `Retraduzir ${LANGUAGES.find(l => l.code === activeLang)?.name}`}
          </Button>
        )}
      </div>

      <Card>
        <CardContent className="p-4">
          <Tabs value={activeLang} onValueChange={setActiveLang}>
            <TabsList className="w-full justify-start">
              {LANGUAGES.map((lang) => (
                <TabsTrigger key={lang.code} value={lang.code} className="gap-1.5 text-xs">
                  <span>{lang.flag}</span>
                  {lang.name}
                </TabsTrigger>
              ))}
            </TabsList>

            {LANGUAGES.map((lang) => (
              <TabsContent key={lang.code} value={lang.code} className="mt-4 space-y-4">
                {loadingLang ? (
                  <div className="flex items-center justify-center py-8 text-sm text-muted-foreground">
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />Carregando...
                  </div>
                ) : !exportData ? (
                  <div className="text-center py-8 text-sm text-muted-foreground">
                    Nenhum dado disponivel. Execute as traducoes primeiro.
                  </div>
                ) : (
                  <>
                    {/* Post */}
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Post</span>
                        <div className="flex gap-1">
                          {!editingPost && (
                            <Button variant="ghost" size="xs" onClick={() => { setEditingPost(true); setEditPostText(exportData.post_text || "") }}>Editar</Button>
                          )}
                          <Button variant="ghost" size="xs" onClick={() => copyText(exportData.post_text || "")}>
                            <Copy className="h-3 w-3" />
                          </Button>
                        </div>
                      </div>
                      {editingPost ? (
                        <div className="space-y-2">
                          <Textarea value={editPostText} onChange={(e) => setEditPostText(e.target.value)} className="min-h-[200px] text-sm" />
                          <div className="flex gap-2">
                            <Button size="xs" onClick={() => handleSave("post")} disabled={saving}>{saving ? "Salvando..." : "Salvar"}</Button>
                            <Button variant="outline" size="xs" onClick={() => setEditingPost(false)}>Cancelar</Button>
                          </div>
                        </div>
                      ) : (
                        <div className="rounded-lg bg-muted/30 p-3 text-xs text-foreground leading-relaxed whitespace-pre-wrap">
                          {exportData.post_text || "—"}
                        </div>
                      )}
                    </div>

                    {/* YouTube */}
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">YouTube</span>
                        <div className="flex gap-1">
                          {!editingYt && (
                            <Button variant="ghost" size="xs" onClick={() => { setEditingYt(true); setEditYtTitle(exportData.youtube_title || ""); setEditYtTags(exportData.youtube_tags || "") }}>Editar</Button>
                          )}
                          <Button variant="ghost" size="xs" onClick={() => copyText(`${exportData.youtube_title}\n\n${exportData.youtube_tags}`)}>
                            <Copy className="h-3 w-3" />
                          </Button>
                        </div>
                      </div>
                      {editingYt ? (
                        <div className="space-y-2">
                          <Input value={editYtTitle} onChange={(e) => setEditYtTitle(e.target.value)} placeholder="Titulo" className="text-sm" />
                          <Input value={editYtTags} onChange={(e) => setEditYtTags(e.target.value)} placeholder="Tags" className="text-sm" />
                          <div className="flex gap-2">
                            <Button size="xs" onClick={() => handleSave("yt")} disabled={saving}>{saving ? "Salvando..." : "Salvar"}</Button>
                            <Button variant="outline" size="xs" onClick={() => setEditingYt(false)}>Cancelar</Button>
                          </div>
                        </div>
                      ) : (
                        <div className="rounded-lg bg-muted/30 p-3 text-xs space-y-1">
                          <p className="font-medium text-foreground">{exportData.youtube_title || "—"}</p>
                          <p className="text-muted-foreground">{exportData.youtube_tags || "—"}</p>
                        </div>
                      )}
                    </div>

                    {/* SRT */}
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Legendas (SRT)</span>
                        <div className="flex gap-1">
                          <Button variant="ghost" size="xs" onClick={() => copyText(exportData.srt || "")}>
                            <Copy className="h-3 w-3" />
                          </Button>
                          <Button variant="ghost" size="xs" onClick={downloadSrt}>Baixar .srt</Button>
                        </div>
                      </div>
                      <pre className="rounded-lg bg-muted/30 p-3 text-xs text-foreground overflow-auto max-h-60 font-mono">
                        {exportData.srt || "—"}
                      </pre>
                    </div>

                    {/* Overlay */}
                    {exportData.overlay_json && (
                      <div>
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Overlay</span>
                          {!editingOverlay && (
                            <Button variant="ghost" size="xs" onClick={() => { setEditingOverlay(true); setEditOverlay([...exportData.overlay_json!]) }}>Editar</Button>
                          )}
                        </div>
                        {editingOverlay ? (
                          <div className="space-y-2">
                            {editOverlay.map((entry, i) => (
                              <div key={i} className="flex gap-2 items-center text-sm">
                                <span className="text-primary font-semibold text-xs w-12">{entry.timestamp}</span>
                                <Input value={entry.text} onChange={(e) => {
                                  const u = [...editOverlay]; u[i] = { ...u[i], text: e.target.value }; setEditOverlay(u)
                                }} className="flex-1 text-xs" />
                              </div>
                            ))}
                            <div className="flex gap-2">
                              <Button size="xs" onClick={() => handleSave("overlay")} disabled={saving}>{saving ? "Salvando..." : "Salvar"}</Button>
                              <Button variant="outline" size="xs" onClick={() => setEditingOverlay(false)}>Cancelar</Button>
                            </div>
                          </div>
                        ) : (
                          <div className="rounded-lg bg-muted/30 p-3 text-xs font-mono space-y-1">
                            {exportData.overlay_json.map((entry, i) => (
                              <p key={i}><span className="text-primary font-semibold">[{entry.timestamp}]</span> {entry.text}</p>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </>
                )}
              </TabsContent>
            ))}
          </Tabs>
        </CardContent>
      </Card>
    </div>
  )
}
