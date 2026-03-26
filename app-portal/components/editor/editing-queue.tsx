"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { editorApi, type Edicao, type RedatorProject } from "@/lib/api/editor"
import { ApiError } from "@/lib/api/base"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Checkbox } from "@/components/ui/checkbox"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog"
import { Plus, Trash2, Clock, Clapperboard, Download, Loader2, Globe, CheckCircle2, AlertTriangle, RotateCcw } from "lucide-react"
import { useBrand } from "@/lib/brand-context"
import { toast } from "sonner"
import { extractErrorMessage } from "@/lib/utils"

const STATUS_LABELS: Record<string, { label: string; variant: "default" | "secondary" | "destructive" | "outline" }> = {
  aguardando: { label: "Aguardando", variant: "secondary" },
  baixando: { label: "Baixando...", variant: "outline" },
  letra: { label: "Letra", variant: "outline" },
  transcricao: { label: "Transcrição", variant: "outline" },
  alinhamento: { label: "Alinhamento", variant: "outline" },
  corte: { label: "Corte", variant: "outline" },
  traducao: { label: "Tradução", variant: "outline" },
  montagem: { label: "Montagem", variant: "outline" },
  renderizando: { label: "Renderizando...", variant: "outline" },
  concluido: { label: "Concluído", variant: "default" },
  erro: { label: "Erro", variant: "destructive" },
}

const REDATOR_STATUS_LABELS: Record<string, { label: string; variant: "default" | "secondary" | "outline" }> = {
  input_complete: { label: "Input", variant: "secondary" },
  generating: { label: "Gerando...", variant: "outline" },
  awaiting_approval: { label: "Aprovação", variant: "outline" },
  translating: { label: "Traduzindo...", variant: "outline" },
  export_ready: { label: "Pronto", variant: "default" },
}

function formatDuration(sec: number | null | undefined) {
  if (!sec) return "--:--"
  const m = Math.floor(sec / 60)
  const s = Math.floor(sec % 60)
  return `${m}:${String(s).padStart(2, "0")}`
}

function nextStepPath(e: Edicao) {
  // passo_atual >= 2 → vai para a página do passo correspondente
  if (e.passo_atual >= 2) {
    if (e.passo_atual <= 2) return `/editor/edicao/${e.id}/letra`
    if (e.passo_atual <= 4) return `/editor/edicao/${e.id}/alinhamento`
    return `/editor/edicao/${e.id}/conclusao`
  }
  // passo_atual = 1 (ou undefined) com status aguardando → overview
  if (e.status === "aguardando") return `/editor/edicao/${e.id}/overview`
  // fallback: status-based para compatibilidade
  if (e.status === "baixando" || e.status === "letra") return `/editor/edicao/${e.id}/letra`
  if (e.status === "transcricao" || e.status === "alinhamento") return `/editor/edicao/${e.id}/alinhamento`
  return `/editor/edicao/${e.id}/conclusao`
}

export function EditorEditingQueue() {
  const router = useRouter()
  const { selectedBrand } = useBrand()
  const [edicoes, setEdicoes] = useState<Edicao[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({
    youtube_url: "", youtube_video_id: "", artista: "", musica: "",
    compositor: "", opera: "", categoria: "", idioma: "it", eh_instrumental: false,
  })
  const [saving, setSaving] = useState(false)

  const [showImportar, setShowImportar] = useState(false)
  const [projetosRedator, setProjetosRedator] = useState<RedatorProject[]>([])
  const [loadingRedator, setLoadingRedator] = useState(false)
  const [importando, setImportando] = useState<number | null>(null)
  const [erroRedator, setErroRedator] = useState("")

  const [modalIdioma, setModalIdioma] = useState<{ projectId: number, artist: string, work: string, category?: string } | null>(null)
  const [idiomaEscolhido, setIdiomaEscolhido] = useState("auto")
  const [outroIdioma, setOutroIdioma] = useState("")
  const [temLetraImport, setTemLetraImport] = useState<boolean | null>(null)

  // Modal duplicata (409)
  const [modalDuplicata, setModalDuplicata] = useState<{
    edicao_id: number
    status: string
    mensagem: string
  } | null>(null)

  const [showTodosStatus, setShowTodosStatus] = useState(false)

  const [limparConfirmId, setLimparConfirmId] = useState<number | null>(null)
  const [limpando, setLimpando] = useState(false)
  const [erroLimpar, setErroLimpar] = useState("")

  const loadEdicoes = () => {
    editorApi.listarEdicoes(undefined, selectedBrand?.id)
      .then(setEdicoes)
      .catch(err => {
        const msg = extractErrorMessage(err)
        toast.error(`Erro ao carregar edições: ${msg}`)
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    setLoading(true)
    editorApi.listarEdicoes(undefined, selectedBrand?.id).then(data => {
      setEdicoes(data)
      if (data.length === 0) {
        setShowImportar(true)
        setLoadingRedator(true)
        editorApi.listarProjetosRedator(selectedBrand?.id)
          .then(setProjetosRedator)
          .catch((err: unknown) => setErroRedator("Erro ao conectar com o Redator: " + (err instanceof Error ? err.message : "Erro desconhecido")))
          .finally(() => setLoadingRedator(false))
      }
    }).finally(() => setLoading(false))
  }, [selectedBrand?.id])

  const extractVideoId = (url: string) => {
    const match = url.match(/(?:v=|youtu\.be\/)([a-zA-Z0-9_-]{11})/)
    return match ? match[1] : ""
  }

  const handleUrlChange = (url: string) => {
    setForm(f => ({ ...f, youtube_url: url, youtube_video_id: extractVideoId(url) }))
  }

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.youtube_url || !form.artista || !form.musica || !form.idioma) return
    setSaving(true)
    try {
      await editorApi.criarEdicao({ 
        ...form, 
        perfil_id: selectedBrand?.id 
      } as unknown as Partial<Edicao>)
      setShowForm(false)
      setForm({ youtube_url: "", youtube_video_id: "", artista: "", musica: "", compositor: "", opera: "", categoria: "", idioma: "it", eh_instrumental: false })
      toast.success("Edição criada com sucesso!")
      loadEdicoes()
    } catch (err: unknown) {
      const msg = extractErrorMessage(err)
      toast.error(`Erro ao criar edição: ${msg}`)
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm("Remover esta edição?")) return
    await editorApi.removerEdicao(id)
    loadEdicoes()
  }

  const carregarProjetosRedator = async () => {
    setLoadingRedator(true)
    setErroRedator("")
    try {
      const data = await editorApi.listarProjetosRedator(selectedBrand?.id)
      setProjetosRedator(data)
    } catch (err: unknown) {
      setErroRedator("Erro ao conectar com o Redator: " + (err instanceof Error ? err.message : "Erro desconhecido"))
    } finally {
      setLoadingRedator(false)
    }
  }

  const handleImportar = async (projectId: number, idioma?: string) => {
    setImportando(projectId)
    try {
      const finalIdioma = (idioma === "auto" || idioma === "other") ? undefined : idioma
      const result = await editorApi.importarDoRedator(projectId, finalIdioma, !temLetraImport, selectedBrand?.id)
      setShowImportar(false)
      setTemLetraImport(null)
      loadEdicoes()
      toast.success(`Edição importada: ${result.artista} — ${result.musica}`)
    } catch (err: unknown) {
      if (err instanceof ApiError && err.status === 422 && (err.detail as Record<string, unknown>)?.idioma_necessario === true) {
        const projeto = projetosRedator.find(p => p.id === projectId)
        setModalIdioma({
          projectId,
          artist: projeto?.artist || "",
          work: projeto?.work || "",
          category: projeto?.category,
        })
        setIdiomaEscolhido("auto")
        setOutroIdioma("")
        setTemLetraImport(null)
        toast.error("Idioma não detectado automaticamente. Selecione abaixo.")
      } else if (err instanceof ApiError && err.status === 409 && (err.detail as Record<string, unknown>)?.duplicata === true) {
        const detail = err.detail as Record<string, unknown>
        setModalDuplicata({
          edicao_id: detail.edicao_existente_id as number,
          status: detail.status as string,
          mensagem: detail.mensagem as string,
        })
      } else {
        const msg = extractErrorMessage(err)
        toast.error(`Erro ao importar: ${msg}`)
      }
    } finally {
      setImportando(null)
    }
  }

  const handleConfirmarIdioma = () => {
    const idioma = outroIdioma.trim() || idiomaEscolhido
    if (!idioma || !modalIdioma) return
    handleImportar(modalIdioma.projectId, idioma)
  }

  const handleLimparEdicao = async () => {
    if (!limparConfirmId) return
    setLimpando(true)
    setErroLimpar("")
    try {
      await editorApi.limparEdicao(limparConfirmId)
      setLimparConfirmId(null)
      loadEdicoes()
    } catch (err: unknown) {
      if (err instanceof ApiError && err.status === 409) {
        setErroLimpar((err as ApiError).message || "Edição está sendo processada agora.")
      } else {
        setErroLimpar("Erro ao limpar: " + (err instanceof Error ? err.message : "Erro"))
      }
    } finally {
      setLimpando(false)
    }
  }

  const toggleImportar = () => {
    const next = !showImportar
    setShowImportar(next)
    if (next && projetosRedator.length === 0) carregarProjetosRedator()
    if (next) setShowForm(false)
  }

  if (loading) return <div className="text-center py-16 text-muted-foreground">Carregando...</div>

  const ativas = edicoes.filter(e => e.status !== "concluido")

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold">Fila de Edição</h2>
        <div className="flex items-center gap-2">
          <Button onClick={toggleImportar} variant="outline" className="gap-2">
            <Download className="h-4 w-4" /> Importar do Redator
          </Button>
          <Button onClick={() => { setShowForm(!showForm); if (!showForm) setShowImportar(false) }} className="gap-2">
            <Plus className="h-4 w-4" /> Criar Manual
          </Button>
        </div>
      </div>

      {showImportar && (
        <Card className="mb-6">
          <CardHeader className="flex flex-row items-center justify-between pb-3">
            <CardTitle className="flex items-center gap-2 text-lg">
              <Globe className="h-5 w-5 text-green-600" />
              Projetos do Redator
            </CardTitle>
            <div className="flex items-center gap-2">
              <Button variant="ghost" size="sm" onClick={() => setProjetosRedator([])} disabled={loadingRedator}>
                Limpar lista
              </Button>
              <Button variant="ghost" size="sm" onClick={carregarProjetosRedator} disabled={loadingRedator}>
                {loadingRedator ? "Carregando..." : "Atualizar"}
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {erroRedator && (
              <div className="bg-destructive/10 text-destructive px-4 py-3 rounded-lg text-sm mb-4">{erroRedator}</div>
            )}
            {loadingRedator && projetosRedator.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <Loader2 className="h-6 w-6 mx-auto mb-2 animate-spin" />
                Conectando ao Redator...
              </div>
            ) : projetosRedator.length === 0 && !loadingRedator && !erroRedator ? (
              <div className="text-center py-8 text-muted-foreground">Nenhum projeto encontrado no Redator.</div>
            ) : (
              <>
                <div className="flex items-center gap-3 mb-3 text-xs text-muted-foreground">
                  <label className="flex items-center gap-1.5 cursor-pointer select-none">
                    <input type="checkbox" checked={showTodosStatus} onChange={e => setShowTodosStatus(e.target.checked)} className="accent-primary" />
                    Mostrar todos os status
                  </label>
                </div>
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {projetosRedator.filter(p => {
                  if (p.editor_status === "concluido") return false
                  if (!showTodosStatus && p.status !== "export_ready") return false
                  return true
                }).map(p => {
                  const st = REDATOR_STATUS_LABELS[p.status] || REDATOR_STATUS_LABELS.input_complete
                  const prontoNoRedator = p.status === "export_ready"
                  return (
                    <div key={p.id} className={`flex items-center gap-4 p-3 rounded-lg border transition ${p.editor_status === "concluido" ? "opacity-50 bg-muted/30" :
                      p.editor_status === "em_andamento" ? "opacity-80 bg-muted/20" :
                        "hover:bg-muted/50"
                      }`}>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-0.5">
                          <span className="font-medium truncate">{p.artist} — {p.work}</span>
                          {p.editor_status === "concluido" ? (
                            <Badge variant="outline" className="border-gray-400 text-gray-500 text-[10px]">
                              <CheckCircle2 className="h-3 w-3 mr-1" />
                              Concluído ✓
                            </Badge>
                          ) : p.editor_status === "em_andamento" ? (
                            <Link href={`/editor/edicao/${p.editor_edicao_id}/conclusao`}>
                              <Badge variant="outline" className="border-amber-500 text-amber-600 text-[10px] cursor-pointer hover:bg-amber-50">
                                <AlertTriangle className="h-3 w-3 mr-1" />
                                Em edição #{p.editor_edicao_id}
                              </Badge>
                            </Link>
                          ) : prontoNoRedator ? (
                            <Badge variant="outline" className="border-green-500 text-green-600 text-[10px]">
                              Disponível para edição
                            </Badge>
                          ) : (
                            <Badge variant={st.variant}>{st.label}</Badge>
                          )}
                        </div>
                        <div className="flex items-center gap-3 text-xs text-muted-foreground">
                          {p.composer && <span>{p.composer}</span>}
                          {p.album_opera && <span>· {p.album_opera}</span>}
                          {p.category && <span>· {p.category}</span>}
                          <span>· {p.translations_count} traduções</span>
                        </div>
                      </div>
                      {p.editor_status === "concluido" ? (
                        <Button size="sm" variant="outline" disabled className="gap-1.5 opacity-50">
                          <CheckCircle2 className="h-3.5 w-3.5" /> Concluído
                        </Button>
                      ) : p.editor_status === "em_andamento" ? (
                        <Button size="sm" variant="outline" asChild className="gap-1.5">
                          <Link href={`/editor/edicao/${p.editor_edicao_id}/conclusao`}>
                            Ir para edição #{p.editor_edicao_id}
                          </Link>
                        </Button>
                      ) : (
                        <Button size="sm" onClick={() => {
                          setModalIdioma({ projectId: p.id, artist: p.artist, work: p.work, category: p.category })
                          setIdiomaEscolhido("auto")
                          setOutroIdioma("")
                          // RC é instrumental por padrão — pré-selecionar Sem Lyrics
                          setTemLetraImport(selectedBrand?.sigla === "RC" ? false : null)
                        }} disabled={importando !== null} className="gap-1.5">
                          {importando === p.id ? (
                            <><Loader2 className="h-3.5 w-3.5 animate-spin" /> ...</>
                          ) : (
                            <><Download className="h-3.5 w-3.5" /> Importar</>
                          )}
                        </Button>
                      )}
                    </div>
                  )
                })}
              </div>
              </>
            )}
          </CardContent>
        </Card>
      )}

      {showForm && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Nova Edição (Manual)</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleCreate} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="col-span-2">
                  <Label>URL do YouTube *</Label>
                  <Input
                    value={form.youtube_url}
                    onChange={e => handleUrlChange(e.target.value)}
                    placeholder="https://www.youtube.com/watch?v=..."
                    required
                  />
                  {form.youtube_video_id && (
                    <span className="text-xs text-muted-foreground mt-1">ID: {form.youtube_video_id}</span>
                  )}
                </div>
                <div>
                  <Label>Artista *</Label>
                  <Input value={form.artista} onChange={e => setForm(f => ({ ...f, artista: e.target.value }))} required />
                </div>
                <div>
                  <Label>Música *</Label>
                  <Input value={form.musica} onChange={e => setForm(f => ({ ...f, musica: e.target.value }))} required />
                </div>
                <div>
                  <Label>Compositor</Label>
                  <Input value={form.compositor} onChange={e => setForm(f => ({ ...f, compositor: e.target.value }))} />
                </div>
                <div>
                  <Label>Ópera</Label>
                  <Input value={form.opera} onChange={e => setForm(f => ({ ...f, opera: e.target.value }))} />
                </div>
                <div>
                  <Label>Idioma *</Label>
                  <Select value={form.idioma} onValueChange={v => setForm(f => ({ ...f, idioma: v }))}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="it">Italiano</SelectItem>
                      <SelectItem value="de">Alemão</SelectItem>
                      <SelectItem value="fr">Francês</SelectItem>
                      <SelectItem value="en">Inglês</SelectItem>
                      <SelectItem value="es">Espanhol</SelectItem>
                      <SelectItem value="pt">Português</SelectItem>
                      <SelectItem value="ru">Russo</SelectItem>
                      <SelectItem value="cs">Tcheco</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>Categoria</Label>
                  <Select value={form.categoria} onValueChange={v => setForm(f => ({ ...f, categoria: v }))}>
                    <SelectTrigger><SelectValue placeholder="—" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Aria">Ária</SelectItem>
                      <SelectItem value="Duet">Dueto</SelectItem>
                      <SelectItem value="Chorus">Coro</SelectItem>
                      <SelectItem value="Overture">Abertura</SelectItem>
                      <SelectItem value="Other">Outro</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Checkbox
                  id="instrumental"
                  checked={form.eh_instrumental}
                  onCheckedChange={(checked) => setForm(f => ({ ...f, eh_instrumental: !!checked }))}
                />
                <Label htmlFor="instrumental" className="text-sm">Instrumental (sem letra)</Label>
              </div>
              <div className="flex gap-3">
                <Button type="submit" disabled={saving || !form.youtube_url || !form.artista || !form.musica || !form.idioma}>
                  {saving ? "Criando..." : "Criar Edição"}
                </Button>
                <Button type="button" variant="ghost" onClick={() => setShowForm(false)}>Cancelar</Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {/* Modal: seleção de idioma quando detecção falha */}
      <Dialog open={!!modalIdioma} onOpenChange={open => { if (!open) setModalIdioma(null) }}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Importar do Redator</DialogTitle>
            <DialogDescription>
              {modalIdioma?.artist} — {modalIdioma?.work}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-5 pt-2">
            <div>
              <Label className="mb-2 block text-sm font-medium">Idioma da música</Label>
              <Select
                value={idiomaEscolhido}
                onValueChange={v => { setIdiomaEscolhido(v); if (v !== "other") setOutroIdioma("") }}
              >
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="auto">Detectar automaticamente (se possível)</SelectItem>
                  <SelectItem value="it">Italiano (it)</SelectItem>
                  <SelectItem value="en">English (en)</SelectItem>
                  <SelectItem value="de">Deutsch (de)</SelectItem>
                  <SelectItem value="fr">Français (fr)</SelectItem>
                  <SelectItem value="es">Español (es)</SelectItem>
                  <SelectItem value="pt">Português (pt)</SelectItem>
                  <SelectItem value="la">Latim (la)</SelectItem>
                  <SelectItem value="ru">Russo (ru)</SelectItem>
                  <SelectItem value="cs">Tcheco (cs)</SelectItem>
                  <SelectItem value="other">Outro...</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {idiomaEscolhido === "other" && (
              <div>
                <Label className="mb-1 block text-xs">Código ISO do idioma</Label>
                <Input
                  value={outroIdioma}
                  onChange={e => setOutroIdioma(e.target.value)}
                  placeholder="ex: ru, cs, hu..."
                  maxLength={10}
                />
              </div>
            )}

            <div className="space-y-3">
              <Label className="text-sm font-medium">Transcrição de Letra (Lyrics)</Label>
              <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => setTemLetraImport(true)}
                  className={`flex flex-col items-center justify-center p-4 rounded-xl border-2 transition-all ${temLetraImport === true
                    ? "border-amber-500 bg-amber-50 text-amber-900 shadow-sm"
                    : "border-muted bg-white hover:border-muted-foreground/30 text-muted-foreground hover:text-foreground"
                    }`}
                >
                  <span className="text-2xl mb-2">🎵</span>
                  <span className="text-xs font-bold uppercase tracking-wider">Com Lyrics</span>
                  <span className="text-[10px] opacity-70 mt-1 text-center">Fazer transcrição e tradução</span>
                </button>

                <button
                  type="button"
                  onClick={() => setTemLetraImport(false)}
                  className={`flex flex-col items-center justify-center p-4 rounded-xl border-2 transition-all ${temLetraImport === false
                    ? "border-blue-500 bg-blue-50 text-blue-900 shadow-sm"
                    : "border-muted bg-white hover:border-muted-foreground/30 text-muted-foreground hover:text-foreground"
                    }`}
                >
                  <span className="text-2xl mb-2">🎼</span>
                  <span className="text-xs font-bold uppercase tracking-wider">Sem Lyrics</span>
                  <span className="text-[10px] opacity-70 mt-1 text-center">Instrumental ou sem legenda</span>
                </button>
              </div>

              {modalIdioma && (
                <div className="flex justify-center">
                  {selectedBrand?.sigla === "RC" ? (
                    <span className="text-[10px] text-blue-600 bg-blue-50 px-2 py-0.5 rounded-full border border-blue-100 italic">
                      💡 Reels Classics: Sem Lyrics pré-selecionado (instrumental por padrão)
                    </span>
                  ) : ["Aria", "Duet", "Chorus"].includes(modalIdioma.category || "") ? (
                    <span className="text-[10px] text-amber-600 bg-amber-50 px-2 py-0.5 rounded-full border border-amber-100 italic">
                      💡 Recomendado: Com Lyrics (detectada categoria vocal: {modalIdioma.category})
                    </span>
                  ) : modalIdioma.category === "Overture" ? (
                    <span className="text-[10px] text-blue-600 bg-blue-50 px-2 py-0.5 rounded-full border border-blue-100 italic">
                      💡 Recomendado: Sem Lyrics (detectada categoria instrumental: Abertura)
                    </span>
                  ) : null}
                </div>
              )}

              <p className="text-[10px] text-center text-muted-foreground">
                A escolha é obrigatória. Ela define se haverá transcrição de lyrics e traducão nos vídeos finalizados.
              </p>
            </div>

            <div className="flex gap-3 justify-end pt-2">
              <Button variant="ghost" onClick={() => setModalIdioma(null)} disabled={importando !== null}>
                Cancelar
              </Button>
              <Button
                onClick={handleConfirmarIdioma}
                disabled={importando !== null || temLetraImport === null}
                className={`transition-all ${temLetraImport === null ? "opacity-50 grayscale" : "bg-green-600 hover:bg-green-700"}`}
              >
                {importando !== null ? (
                  <><Loader2 className="h-4 w-4 animate-spin mr-2" />Importando...</>
                ) : (
                  "Iniciar Importação"
                )}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Modal: projeto já importado (duplicata 409) */}
      <Dialog open={!!modalDuplicata} onOpenChange={open => { if (!open) setModalDuplicata(null) }}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-yellow-500" />
              Projeto já importado
            </DialogTitle>
            <DialogDescription>
              {modalDuplicata?.mensagem}
            </DialogDescription>
          </DialogHeader>
          <div className="flex gap-3 justify-end pt-4">
            <Button variant="ghost" onClick={() => setModalDuplicata(null)}>Cancelar</Button>
            <Button onClick={() => {
              if (!modalDuplicata) return
              const path = modalDuplicata.status === "aguardando"
                ? `/editor/edicao/${modalDuplicata.edicao_id}/overview`
                : modalDuplicata.status === "concluido"
                  ? `/editor/edicao/${modalDuplicata.edicao_id}/conclusao`
                  : `/editor/edicao/${modalDuplicata.edicao_id}/letra`
              setModalDuplicata(null)
              router.push(path)
            }}>
              Ir para edição #{modalDuplicata?.edicao_id}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Modal: confirmação Limpar Edição */}
      <Dialog open={!!limparConfirmId} onOpenChange={open => { if (!open) { setLimparConfirmId(null); setErroLimpar("") } }}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-red-700">
              <AlertTriangle className="h-5 w-5" />
              Limpar Edição
            </DialogTitle>
            <DialogDescription>
              Tem certeza? Todo o progresso desta edição será apagado e ela voltará ao início.
            </DialogDescription>
          </DialogHeader>
          {erroLimpar && (
            <div className="bg-destructive/10 text-destructive px-4 py-3 rounded-lg text-sm">{erroLimpar}</div>
          )}
          <div className="flex gap-3 justify-end pt-2">
            <Button variant="ghost" onClick={() => { setLimparConfirmId(null); setErroLimpar("") }} disabled={limpando}>
              Cancelar
            </Button>
            <Button variant="destructive" onClick={handleLimparEdicao} disabled={limpando} className="gap-2">
              {limpando ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Trash2 className="h-3.5 w-3.5" />}
              {limpando ? "Limpando..." : "Sim, Limpar Tudo"}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {ativas.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground">
          <Clapperboard className="h-12 w-12 mx-auto mb-4 opacity-50" />
          <p>Nenhuma edição ainda.</p>
          <p className="text-sm mt-1">Clique em &quot;Importar do Redator&quot; ou &quot;Criar Manual&quot; para começar.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {ativas.map(e => {
            const st = STATUS_LABELS[e.status] || STATUS_LABELS.aguardando
            return (
              <Card key={e.id} className="hover:shadow-md transition">
                <CardContent className="flex items-center gap-4 p-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 mb-1">
                      <Link href={nextStepPath(e)} className="font-semibold text-lg hover:text-primary transition truncate">
                        {e.artista} — {e.musica}
                      </Link>
                      <Badge variant={st.variant}>{st.label}</Badge>
                      {e.eh_instrumental && <Badge variant="secondary">Instrumental</Badge>}
                    </div>
                    <div className="flex items-center gap-4 text-xs text-muted-foreground">
                      {selectedBrand && (
                        <span
                          className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wide"
                          style={{ backgroundColor: selectedBrand.cor_secundaria + "22", color: selectedBrand.cor_secundaria, border: `1px solid ${selectedBrand.cor_secundaria}44` }}
                        >
                          {selectedBrand.sigla}
                        </span>
                      )}
                      {e.compositor && <span>{e.compositor}</span>}
                      {e.opera && <span>· {e.opera}</span>}
                      {e.categoria && <span>· {e.categoria}</span>}
                      <span>· {e.idioma?.toUpperCase()}</span>
                      {e.duracao_corte_sec != null && (
                        <span className="flex items-center gap-1">
                          <Clock className="h-3 w-3" /> Corte: {formatDuration(e.duracao_corte_sec)}
                        </span>
                      )}
                      {e.rota_alinhamento && <span>· Rota {e.rota_alinhamento}</span>}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {e.status === "concluido" || e.status === "preview_pronto" ? (
                      <Button asChild variant="outline" size="sm" className="gap-1.5">
                        <Link href={nextStepPath(e)}>
                          <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" /> Ver / Baixar
                        </Link>
                      </Button>
                    ) : (
                      <Button asChild variant="secondary" size="sm">
                        <Link href={nextStepPath(e)}>Editar</Link>
                      </Button>
                    )}
                    {e.status !== "concluido" && e.status !== "preview_pronto" && e.status !== "aguardando" && (
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => setLimparConfirmId(e.id)}
                        className="text-muted-foreground hover:text-red-600"
                        title="Limpar Edição"
                      >
                        <RotateCcw className="h-4 w-4" />
                      </Button>
                    )}
                    <Button variant="ghost" size="icon" onClick={() => handleDelete(e.id)} className="text-muted-foreground hover:text-destructive">
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}
    </div>
  )
}
