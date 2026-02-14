import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { editorApi } from '../api'
import { Plus, Play, Trash2, Clock, Music, Mic, Clapperboard, Download, ChevronDown, ChevronUp, Loader2, Globe, CheckCircle } from 'lucide-react'

const STATUS_LABELS = {
  aguardando: { label: 'Aguardando', color: 'bg-gray-200 text-gray-700' },
  baixando: { label: 'Baixando...', color: 'bg-blue-100 text-blue-700' },
  letra: { label: 'Letra', color: 'bg-yellow-100 text-yellow-700' },
  transcricao: { label: 'Transcrição', color: 'bg-orange-100 text-orange-700' },
  alinhamento: { label: 'Alinhamento', color: 'bg-purple-bg text-purple' },
  corte: { label: 'Corte', color: 'bg-indigo-100 text-indigo-700' },
  traducao: { label: 'Tradução', color: 'bg-cyan-100 text-cyan-700' },
  montagem: { label: 'Montagem', color: 'bg-teal-100 text-teal-700' },
  renderizando: { label: 'Renderizando...', color: 'bg-amber-100 text-amber-700' },
  concluido: { label: 'Concluído', color: 'bg-green-100 text-green-700' },
  erro: { label: 'Erro', color: 'bg-red-100 text-red-700' },
}

const REDATOR_STATUS_LABELS = {
  input_complete: { label: 'Input', color: 'bg-gray-200 text-gray-700' },
  generating: { label: 'Gerando...', color: 'bg-blue-100 text-blue-700' },
  awaiting_approval: { label: 'Aprovação', color: 'bg-yellow-100 text-yellow-700' },
  translating: { label: 'Traduzindo...', color: 'bg-cyan-100 text-cyan-700' },
  export_ready: { label: 'Pronto', color: 'bg-green-100 text-green-700' },
}

function formatDuration(sec) {
  if (!sec) return '--:--'
  const m = Math.floor(sec / 60)
  const s = Math.floor(sec % 60)
  return `${m}:${String(s).padStart(2, '0')}`
}

function nextStepPath(e) {
  if (e.status === 'aguardando' || e.status === 'baixando') return `/edicao/${e.id}/letra`
  if (e.status === 'letra') return `/edicao/${e.id}/letra`
  if (e.status === 'transcricao' || e.status === 'alinhamento') return `/edicao/${e.id}/alinhamento`
  if (e.status === 'concluido') return `/edicao/${e.id}/conclusao`
  return `/edicao/${e.id}/conclusao`
}

export default function FilaEdicao() {
  const [edicoes, setEdicoes] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({
    youtube_url: '', youtube_video_id: '', artista: '', musica: '',
    compositor: '', opera: '', categoria: '', idioma: 'it', eh_instrumental: false,
  })
  const [saving, setSaving] = useState(false)

  // Importar do Redator
  const [showImportar, setShowImportar] = useState(false)
  const [projetosRedator, setProjetosRedator] = useState([])
  const [loadingRedator, setLoadingRedator] = useState(false)
  const [importando, setImportando] = useState(null)
  const [erroRedator, setErroRedator] = useState('')

  const loadEdicoes = () => {
    editorApi.listarEdicoes().then(setEdicoes).finally(() => setLoading(false))
  }

  useEffect(loadEdicoes, [])

  const extractVideoId = (url) => {
    const match = url.match(/(?:v=|youtu\.be\/)([a-zA-Z0-9_-]{11})/)
    return match ? match[1] : ''
  }

  const handleUrlChange = (url) => {
    setForm(f => ({ ...f, youtube_url: url, youtube_video_id: extractVideoId(url) }))
  }

  const handleCreate = async (e) => {
    e.preventDefault()
    if (!form.youtube_url || !form.artista || !form.musica || !form.idioma) return
    setSaving(true)
    try {
      await editorApi.criarEdicao(form)
      setShowForm(false)
      setForm({ youtube_url: '', youtube_video_id: '', artista: '', musica: '', compositor: '', opera: '', categoria: '', idioma: 'it', eh_instrumental: false })
      loadEdicoes()
    } catch (err) {
      alert('Erro ao criar: ' + (err.response?.data?.detail || err.message))
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (id) => {
    if (!confirm('Remover esta edição?')) return
    await editorApi.removerEdicao(id)
    loadEdicoes()
  }

  const carregarProjetosRedator = async () => {
    setLoadingRedator(true)
    setErroRedator('')
    try {
      const data = await editorApi.listarProjetosRedator()
      setProjetosRedator(data)
    } catch (err) {
      setErroRedator('Erro ao conectar com o Redator: ' + (err.response?.data?.detail || err.message))
    } finally {
      setLoadingRedator(false)
    }
  }

  const handleImportar = async (projectId) => {
    setImportando(projectId)
    try {
      const result = await editorApi.importarDoRedator(projectId)
      setShowImportar(false)
      loadEdicoes()
      alert(`Edição criada: ${result.artista} — ${result.musica}\nOverlays: ${result.overlays_count} idiomas | Posts: ${result.posts_count} | SEO: ${result.seo_count}`)
    } catch (err) {
      alert('Erro ao importar: ' + (err.response?.data?.detail || err.message))
    } finally {
      setImportando(null)
    }
  }

  const toggleImportar = () => {
    const next = !showImportar
    setShowImportar(next)
    if (next && projetosRedator.length === 0) {
      carregarProjetosRedator()
    }
    if (next) setShowForm(false)
  }

  if (loading) return <div className="text-center py-16 text-gray-400">Carregando...</div>

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold">Fila de Edição</h2>
        <div className="flex items-center gap-2">
          <button
            onClick={toggleImportar}
            className="flex items-center gap-2 bg-green-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-green-700 transition"
          >
            <Download size={16} /> Importar do Redator
          </button>
          <button
            onClick={() => { setShowForm(!showForm); if (!showForm) setShowImportar(false) }}
            className="flex items-center gap-2 bg-purple text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-purple/90 transition"
          >
            <Plus size={16} /> Criar Manual
          </button>
        </div>
      </div>

      {/* Painel Importar do Redator */}
      {showImportar && (
        <div className="bg-white rounded-xl shadow-sm border p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-lg flex items-center gap-2">
              <Globe size={20} className="text-green-600" />
              Projetos do Redator
            </h3>
            <button
              onClick={carregarProjetosRedator}
              disabled={loadingRedator}
              className="text-sm text-gray-500 hover:text-gray-700 transition"
            >
              {loadingRedator ? 'Carregando...' : 'Atualizar'}
            </button>
          </div>

          {erroRedator && (
            <div className="bg-red-50 text-red-700 px-4 py-3 rounded-lg text-sm mb-4">{erroRedator}</div>
          )}

          {loadingRedator && projetosRedator.length === 0 ? (
            <div className="text-center py-8 text-gray-400">
              <Loader2 size={24} className="mx-auto mb-2 animate-spin" />
              Conectando ao Redator...
            </div>
          ) : projetosRedator.length === 0 && !loadingRedator && !erroRedator ? (
            <div className="text-center py-8 text-gray-400">Nenhum projeto encontrado no Redator.</div>
          ) : (
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {projetosRedator.map(p => {
                const st = REDATOR_STATUS_LABELS[p.status] || REDATOR_STATUS_LABELS.input_complete
                return (
                  <div key={p.id} className="flex items-center gap-4 p-3 rounded-lg border hover:bg-gray-50 transition">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-0.5">
                        <span className="font-medium truncate">{p.artist} — {p.work}</span>
                        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${st.color}`}>{st.label}</span>
                      </div>
                      <div className="flex items-center gap-3 text-xs text-gray-400">
                        {p.composer && <span>{p.composer}</span>}
                        {p.album_opera && <span>· {p.album_opera}</span>}
                        {p.category && <span>· {p.category}</span>}
                        <span>· {p.translations_count} traduções</span>
                      </div>
                    </div>
                    <button
                      onClick={() => handleImportar(p.id)}
                      disabled={importando !== null}
                      className="flex items-center gap-1.5 bg-green-600 text-white px-3 py-1.5 rounded-lg text-sm font-medium hover:bg-green-700 transition disabled:opacity-50 whitespace-nowrap"
                    >
                      {importando === p.id ? (
                        <><Loader2 size={14} className="animate-spin" /> Importando...</>
                      ) : (
                        <><Download size={14} /> Importar</>
                      )}
                    </button>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}

      {/* Formulário nova edição manual */}
      {showForm && (
        <form onSubmit={handleCreate} className="bg-white rounded-xl shadow-sm border p-6 mb-6 space-y-4">
          <h3 className="font-semibold text-lg mb-2">Nova Edição (Manual)</h3>
          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <label className="block text-sm font-medium text-gray-600 mb-1">URL do YouTube *</label>
              <input
                value={form.youtube_url}
                onChange={e => handleUrlChange(e.target.value)}
                placeholder="https://www.youtube.com/watch?v=..."
                className="w-full border rounded-lg px-3 py-2 text-sm"
                required
              />
              {form.youtube_video_id && (
                <span className="text-xs text-gray-400 mt-1">ID: {form.youtube_video_id}</span>
              )}
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-600 mb-1">Artista *</label>
              <input value={form.artista} onChange={e => setForm(f => ({ ...f, artista: e.target.value }))} className="w-full border rounded-lg px-3 py-2 text-sm" required />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-600 mb-1">Música *</label>
              <input value={form.musica} onChange={e => setForm(f => ({ ...f, musica: e.target.value }))} className="w-full border rounded-lg px-3 py-2 text-sm" required />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-600 mb-1">Compositor</label>
              <input value={form.compositor} onChange={e => setForm(f => ({ ...f, compositor: e.target.value }))} className="w-full border rounded-lg px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-600 mb-1">Ópera</label>
              <input value={form.opera} onChange={e => setForm(f => ({ ...f, opera: e.target.value }))} className="w-full border rounded-lg px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-600 mb-1">Idioma *</label>
              <select value={form.idioma} onChange={e => setForm(f => ({ ...f, idioma: e.target.value }))} className="w-full border rounded-lg px-3 py-2 text-sm">
                <option value="it">Italiano</option>
                <option value="de">Alemão</option>
                <option value="fr">Francês</option>
                <option value="en">Inglês</option>
                <option value="es">Espanhol</option>
                <option value="pt">Português</option>
                <option value="ru">Russo</option>
                <option value="cs">Tcheco</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-600 mb-1">Categoria</label>
              <select value={form.categoria} onChange={e => setForm(f => ({ ...f, categoria: e.target.value }))} className="w-full border rounded-lg px-3 py-2 text-sm">
                <option value="">—</option>
                <option value="Aria">Ária</option>
                <option value="Duet">Dueto</option>
                <option value="Chorus">Coro</option>
                <option value="Overture">Abertura</option>
                <option value="Other">Outro</option>
              </select>
            </div>
          </div>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={form.eh_instrumental} onChange={e => setForm(f => ({ ...f, eh_instrumental: e.target.checked }))} className="rounded" />
            Instrumental (sem letra)
          </label>
          <div className="flex gap-3">
            <button type="submit" disabled={saving || !form.youtube_url || !form.artista || !form.musica || !form.idioma} className="bg-purple text-white px-6 py-2 rounded-lg text-sm font-medium hover:bg-purple/90 transition disabled:opacity-50">
              {saving ? 'Criando...' : 'Criar Edição'}
            </button>
            <button type="button" onClick={() => setShowForm(false)} className="text-gray-500 text-sm hover:text-gray-700">Cancelar</button>
          </div>
        </form>
      )}

      {/* Lista */}
      {edicoes.length === 0 ? (
        <div className="text-center py-16 text-gray-400">
          <Clapperboard size={48} className="mx-auto mb-4 opacity-50" />
          <p>Nenhuma edição ainda.</p>
          <p className="text-sm mt-1">Clique em "Importar do Redator" ou "Criar Manual" para começar.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {edicoes.map(e => {
            const st = STATUS_LABELS[e.status] || STATUS_LABELS.aguardando
            return (
              <div key={e.id} className="bg-white rounded-xl shadow-sm border p-4 flex items-center gap-4 hover:shadow-md transition">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3 mb-1">
                    <Link to={nextStepPath(e)} className="font-semibold text-lg hover:text-purple transition truncate">
                      {e.artista} — {e.musica}
                    </Link>
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${st.color}`}>{st.label}</span>
                    {e.eh_instrumental && <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-500">Instrumental</span>}
                  </div>
                  <div className="flex items-center gap-4 text-xs text-gray-400">
                    {e.compositor && <span>{e.compositor}</span>}
                    {e.opera && <span>· {e.opera}</span>}
                    {e.categoria && <span>· {e.categoria}</span>}
                    <span>· {e.idioma?.toUpperCase()}</span>
                    {e.duracao_corte_sec && (
                      <span className="flex items-center gap-1">
                        <Clock size={12} /> Corte: {formatDuration(e.duracao_corte_sec)}
                      </span>
                    )}
                    {e.rota_alinhamento && <span>· Rota {e.rota_alinhamento}</span>}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Link to={nextStepPath(e)} className="bg-purple-bg text-purple px-4 py-2 rounded-lg text-sm font-medium hover:bg-purple hover:text-white transition">
                    Editar
                  </Link>
                  <button onClick={() => handleDelete(e.id)} className="text-gray-300 hover:text-red-500 transition p-2">
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
