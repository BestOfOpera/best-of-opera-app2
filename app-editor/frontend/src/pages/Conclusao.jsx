import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { editorApi } from '../api'
import { ArrowLeft, Download, Play, RefreshCw, CheckCircle, XCircle } from 'lucide-react'

const IDIOMAS = [
  { code: 'en', flag: '🇬🇧', label: 'Inglês' },
  { code: 'pt', flag: '🇧🇷', label: 'Português' },
  { code: 'es', flag: '🇪🇸', label: 'Espanhol' },
  { code: 'de', flag: '🇩🇪', label: 'Alemão' },
  { code: 'fr', flag: '🇫🇷', label: 'Francês' },
  { code: 'it', flag: '🇮🇹', label: 'Italiano' },
  { code: 'pl', flag: '🇵🇱', label: 'Polonês' },
]

function formatBytes(bytes) {
  if (!bytes) return '--'
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatSec(sec) {
  if (!sec && sec !== 0) return '--:--'
  const m = Math.floor(sec / 60)
  const s = Math.floor(sec % 60)
  return `${m}:${String(s).padStart(2, '0')}`
}

export default function Conclusao() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [edicao, setEdicao] = useState(null)
  const [renders, setRenders] = useState([])
  const [loading, setLoading] = useState(true)
  const [renderizando, setRenderizando] = useState(false)
  const [traduzindo, setTraduzindo] = useState(false)
  const [error, setError] = useState('')

  const load = async () => {
    try {
      const e = await editorApi.obterEdicao(id)
      setEdicao(e)
      const r = await editorApi.listarRenders(id)
      setRenders(r)
    } catch (err) {
      setError('Erro ao carregar dados: ' + (err.response?.data?.detail || err.message))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [id])

  // Polling durante renderização
  useEffect(() => {
    if (!edicao || edicao.status !== 'renderizando') return
    const timer = setInterval(load, 5000)
    return () => clearInterval(timer)
  }, [edicao?.status])

  const handleTraduzir = async () => {
    setTraduzindo(true)
    setError('')
    try {
      await editorApi.traduzirLyrics(id)
      await load()
    } catch (err) {
      setError('Erro na tradução: ' + (err.response?.data?.detail || err.message))
    } finally {
      setTraduzindo(false)
    }
  }

  const handleRenderizar = async () => {
    setRenderizando(true)
    setError('')
    try {
      await editorApi.renderizar(id)
      await load()
    } catch (err) {
      setError('Erro na renderização: ' + (err.response?.data?.detail || err.message))
    } finally {
      setRenderizando(false)
    }
  }

  if (loading || !edicao) return <div className="text-center py-16 text-gray-400">Carregando...</div>

  const concluidos = renders.filter(r => r.status === 'concluido')
  const erros = renders.filter(r => r.status === 'erro')

  return (
    <div className="max-w-4xl mx-auto">
      <button onClick={() => navigate('/')} className="flex items-center gap-2 text-gray-400 hover:text-gray-600 text-sm mb-6">
        <ArrowLeft size={16} /> Voltar à fila
      </button>

      <div className="mb-6">
        <h2 className="text-2xl font-bold">{edicao.artista} — {edicao.musica}</h2>
        <p className="text-sm text-gray-400 mt-1">Conclusão</p>
      </div>

      {error && <div className="bg-red-50 text-red-600 text-sm rounded-lg p-3 mb-4">{error}</div>}

      {/* Resumo */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white rounded-xl border p-4">
          <div className="text-xs text-gray-400 mb-1">Status</div>
          <div className="font-semibold text-sm capitalize">{edicao.status}</div>
        </div>
        <div className="bg-white rounded-xl border p-4">
          <div className="text-xs text-gray-400 mb-1">Duração do Corte</div>
          <div className="font-semibold text-sm">{formatSec(edicao.duracao_corte_sec)}</div>
        </div>
        <div className="bg-white rounded-xl border p-4">
          <div className="text-xs text-gray-400 mb-1">Rota</div>
          <div className="font-semibold text-sm">{edicao.rota_alinhamento || '—'}</div>
        </div>
        <div className="bg-white rounded-xl border p-4">
          <div className="text-xs text-gray-400 mb-1">Confiança</div>
          <div className="font-semibold text-sm">{edicao.confianca_alinhamento ? `${(edicao.confianca_alinhamento * 100).toFixed(0)}%` : '—'}</div>
        </div>
      </div>

      {/* Ações */}
      <div className="flex gap-3 mb-6 flex-wrap">
        {!edicao.eh_instrumental && (
          <button
            onClick={handleTraduzir}
            disabled={traduzindo}
            className="flex items-center gap-2 bg-purple-bg text-purple px-4 py-2 rounded-lg text-sm font-medium hover:bg-purple hover:text-white transition disabled:opacity-50"
          >
            {traduzindo ? <RefreshCw size={14} className="animate-spin" /> : null}
            {traduzindo ? 'Traduzindo...' : 'Traduzir Lyrics ×7 idiomas'}
          </button>
        )}
        <button
          onClick={handleRenderizar}
          disabled={renderizando || edicao.status === 'renderizando'}
          className="flex items-center gap-2 bg-purple text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-purple/90 transition disabled:opacity-50"
        >
          {renderizando || edicao.status === 'renderizando' ? <RefreshCw size={14} className="animate-spin" /> : <Play size={14} />}
          {renderizando || edicao.status === 'renderizando' ? 'Renderizando...' : 'Renderizar 7 Vídeos'}
        </button>
      </div>

      {/* Renders */}
      {renders.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border p-6">
          <h3 className="font-semibold mb-4">Renders ({concluidos.length}/{renders.length})</h3>
          <div className="space-y-2">
            {IDIOMAS.map(({ code, flag, label }) => {
              const render = renders.find(r => r.idioma === code)
              if (!render) return (
                <div key={code} className="flex items-center gap-3 py-2 px-3 rounded-lg bg-gray-50 text-gray-400 text-sm">
                  <span className="text-lg">{flag}</span>
                  <span className="flex-1">{label}</span>
                  <span className="text-xs">Pendente</span>
                </div>
              )
              return (
                <div key={code} className={`flex items-center gap-3 py-2 px-3 rounded-lg text-sm ${render.status === 'concluido' ? 'bg-green-50' : 'bg-red-50'}`}>
                  <span className="text-lg">{flag}</span>
                  <span className="flex-1 font-medium">{label}</span>
                  {render.status === 'concluido' ? (
                    <>
                      <span className="text-xs text-gray-400">{formatBytes(render.tamanho_bytes)}</span>
                      <CheckCircle size={16} className="text-green-500" />
                    </>
                  ) : (
                    <>
                      <span className="text-xs text-red-500 truncate max-w-[200px]">{render.erro_msg}</span>
                      <XCircle size={16} className="text-red-500" />
                    </>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Próximo vídeo */}
      <div className="mt-8 text-center">
        <Link to="/" className="text-purple hover:underline text-sm font-medium">
          ← Voltar à Fila de Edição
        </Link>
      </div>
    </div>
  )
}
