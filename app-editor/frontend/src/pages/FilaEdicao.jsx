import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { editorApi } from '../api'
import { Plus, Play, Trash2, Clock, Music, Mic, Clapperboard } from 'lucide-react'

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

  if (loading) return <div className="text-center py-16 text-gray-400">Carregando...</div>

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold">Fila de Edição</h2>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-2 bg-purple text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-purple/90 transition"
        >
          <Plus size={16} /> Nova Edição
        </button>
      </div>

      {/* Formulário nova edição */}
      {showForm && (
        <form onSubmit={handleCreate} className="bg-white rounded-xl shadow-sm border p-6 mb-6 space-y-4">
          <h3 className="font-semibold text-lg mb-2">Nova Edição</h3>
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
          <p className="text-sm mt-1">Clique em "Nova Edição" para começar.</p>
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
