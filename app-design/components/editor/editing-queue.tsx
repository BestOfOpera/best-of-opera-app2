"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { editorApi, type Edicao, type RedatorProject } from "@/lib/api/editor"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Checkbox } from "@/components/ui/checkbox"
import { Plus, Trash2, Clock, Clapperboard, Download, Loader2, Globe } from "lucide-react"

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
  if (e.status === "aguardando" || e.status === "baixando" || e.status === "letra") return `/editor/edicao/${e.id}/letra`
  if (e.status === "transcricao" || e.status === "alinhamento") return `/editor/edicao/${e.id}/alinhamento`
  return `/editor/edicao/${e.id}/conclusao`
}

export function EditorEditingQueue() {
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

  const loadEdicoes = () => {
    editorApi.listarEdicoes().then(setEdicoes).finally(() => setLoading(false))
  }

  useEffect(loadEdicoes, [])

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
      await editorApi.criarEdicao(form as unknown as Partial<Edicao>)
      setShowForm(false)
      setForm({ youtube_url: "", youtube_video_id: "", artista: "", musica: "", compositor: "", opera: "", categoria: "", idioma: "it", eh_instrumental: false })
      loadEdicoes()
    } catch (err: unknown) {
      alert("Erro ao criar: " + (err instanceof Error ? err.message : "Erro desconhecido"))
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
      const data = await editorApi.listarProjetosRedator()
      setProjetosRedator(data)
    } catch (err: unknown) {
      setErroRedator("Erro ao conectar com o Redator: " + (err instanceof Error ? err.message : "Erro desconhecido"))
    } finally {
      setLoadingRedator(false)
    }
  }

  const handleImportar = async (projectId: number) => {
    setImportando(projectId)
    try {
      const result = await editorApi.importarDoRedator(projectId)
      setShowImportar(false)
      loadEdicoes()
      alert(`Edição criada: ${result.artista} — ${result.musica}\nOverlays: ${result.overlays_count} idiomas | Posts: ${result.posts_count} | SEO: ${result.seo_count}`)
    } catch (err: unknown) {
      alert("Erro ao importar: " + (err instanceof Error ? err.message : "Erro desconhecido"))
    } finally {
      setImportando(null)
    }
  }

  const toggleImportar = () => {
    const next = !showImportar
    setShowImportar(next)
    if (next && projetosRedator.length === 0) carregarProjetosRedator()
    if (next) setShowForm(false)
  }

  if (loading) return <div className="text-center py-16 text-muted-foreground">Carregando...</div>

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
            <Button variant="ghost" size="sm" onClick={carregarProjetosRedator} disabled={loadingRedator}>
              {loadingRedator ? "Carregando..." : "Atualizar"}
            </Button>
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
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {projetosRedator.map(p => {
                  const st = REDATOR_STATUS_LABELS[p.status] || REDATOR_STATUS_LABELS.input_complete
                  return (
                    <div key={p.id} className="flex items-center gap-4 p-3 rounded-lg border hover:bg-muted/50 transition">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-0.5">
                          <span className="font-medium truncate">{p.artist} — {p.work}</span>
                          <Badge variant={st.variant}>{st.label}</Badge>
                        </div>
                        <div className="flex items-center gap-3 text-xs text-muted-foreground">
                          {p.composer && <span>{p.composer}</span>}
                          {p.album_opera && <span>· {p.album_opera}</span>}
                          {p.category && <span>· {p.category}</span>}
                          <span>· {p.translations_count} traduções</span>
                        </div>
                      </div>
                      <Button size="sm" onClick={() => handleImportar(p.id)} disabled={importando !== null} className="gap-1.5">
                        {importando === p.id ? (
                          <><Loader2 className="h-3.5 w-3.5 animate-spin" /> Importando...</>
                        ) : (
                          <><Download className="h-3.5 w-3.5" /> Importar</>
                        )}
                      </Button>
                    </div>
                  )
                })}
              </div>
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

      {edicoes.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground">
          <Clapperboard className="h-12 w-12 mx-auto mb-4 opacity-50" />
          <p>Nenhuma edição ainda.</p>
          <p className="text-sm mt-1">Clique em &quot;Importar do Redator&quot; ou &quot;Criar Manual&quot; para começar.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {edicoes.map(e => {
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
                    <Button asChild variant="secondary" size="sm">
                      <Link href={nextStepPath(e)}>Editar</Link>
                    </Button>
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
