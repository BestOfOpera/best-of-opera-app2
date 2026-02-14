import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { editorApi } from '../api'
import { ArrowLeft, Download, Play, RefreshCw, CheckCircle, XCircle, PartyPopper, ExternalLink } from 'lucide-react'

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
  const [exportando, setExportando] = useState(false)
  const [exportResult, setExportResult] = useState(null)
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

  // Polling durante tradução ou renderização
  useEffect(() => {
    if (!edicao || !['renderizando', 'traducao'].includes(edicao.status)) return
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

  const handleExportar = async () => {
    setExportando(true)
    setError('')
    setExportResult(null)
    try {
      const result = await editorApi.exportarRenders(id)
      setExportResult(result)
    } catch (err) {
      setError('Erro ao exportar: ' + (err.response?.data?.detail || err.message))
    } finally {
      setExportando(false)
    }
  }

  if (loading || !edicao) return <div className="text-center py-16 text-gray-400">Carregando...</div>

  const concluidos = renders.filter(r => r.status === 'concluido')
  const erros = renders.filter(r => r.status === 'erro')
  const todosOk = concluidos.length === 7 && erros.length === 0
  const isConcluido = edicao.status === 'concluido'

  return (
    <div className="max-w-4xl mx-auto">
      <button onClick={() => navigate('/')} className="flex items-center gap-2 text-gray-400 hover:text-gray-600 text-sm mb-6">
        <ArrowLeft size={16} /> Voltar à fila
      </button>

      {/* Header com status de conclusão */}
      {isConcluido && todosOk ? (
        <div className="bg-green-50 border border-green-200 rounded-xl p-6 mb-6 text-center">
          <CheckCircle size={48} className="mx-auto mb-3 text-green-500" />
          <h2 className="text-2xl font-bold text-green-800">{edicao.artista} — {edicao.musica}</h2>
          <p className="text-green-600 mt-1">Edição concluída com sucesso! {concluidos.length} vídeos renderizados.</p>
        </div>
      ) : (
        <div className="mb-6">
          <h2 className="text-2xl font-bold">{edicao.artista} — {edicao.musica}</h2>
          <p className="text-sm text-gray-400 mt-1">
            Conclusão
            {edicao.youtube_url && (
              <a href={edicao.youtube_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 ml-3 text-purple hover:underline">
                <ExternalLink size={12} /> YouTube
              </a>
            )}
          </p>
        </div>
      )}

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
            disabled={traduzindo || edicao.status === 'traducao'}
            className="flex items-center gap-2 bg-purple-bg text-purple px-4 py-2 rounded-lg text-sm font-medium hover:bg-purple hover:text-white transition disabled:opacity-50"
          >
            {traduzindo || edicao.status === 'traducao' ? <RefreshCw size={14} className="animate-spin" /> : null}
            {traduzindo || edicao.status === 'traducao' ? 'Traduzindo...' : 'Traduzir Lyrics x7 idiomas'}
          </button>
        )}
        <button
          onClick={handleRenderizar}
          disabled={renderizando || traduzindo || edicao.status === 'renderizando' || edicao.status === 'traducao'}
          className="flex items-center gap-2 bg-purple text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-purple/90 transition disabled:opacity-50"
        >
          {renderizando || edicao.status === 'renderizando' ? <RefreshCw size={14} className="animate-spin" /> : <Play size={14} />}
          {renderizando || edicao.status === 'renderizando' ? 'Renderizando...' : edicao.status === 'traducao' || traduzindo ? 'Aguardando tradução...' : renders.length > 0 ? 'Re-renderizar' : 'Renderizar 7 Vídeos'}
        </button>
        {concluidos.length > 0 && (
          <button
            onClick={handleExportar}
            disabled={exportando}
            className="flex items-center gap-2 bg-green-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-green-700 transition disabled:opacity-50"
          >
            {exportando ? <RefreshCw size={14} className="animate-spin" /> : <Download size={14} />}
            {exportando ? 'Exportando...' : 'Salvar no iCloud'}
          </button>
        )}
      </div>

      {exportResult && (
        <div className="bg-green-50 border border-green-200 text-green-700 text-sm rounded-lg p-4 mb-6">
          <p className="font-medium">{exportResult.arquivos_exportados} vídeos exportados para:</p>
          <p className="text-xs mt-1 font-mono break-all">{exportResult.pasta}</p>
        </div>
      )}

      {/* Renders com download */}
      {renders.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold">Vídeos Renderizados ({concluidos.length}/{IDIOMAS.length})</h3>
            {concluidos.length > 0 && (
              <span className="text-xs text-gray-400">Clique para baixar</span>
            )}
          </div>
          <div className="space-y-2">
            {IDIOMAS.map(({ code, flag, label }) => {
              const render = renders.find(r => r.idioma === code)
              if (!render) return (
                <div key={code} className="flex items-center gap-3 py-3 px-4 rounded-lg bg-gray-50 text-gray-400 text-sm">
                  <span className="text-lg">{flag}</span>
                  <span className="flex-1">{label}</span>
                  <span className="text-xs">Pendente</span>
                </div>
              )
              return (
                <div key={code} className={`flex items-center gap-3 py-3 px-4 rounded-lg text-sm ${render.status === 'concluido' ? 'bg-green-50 hover:bg-green-100 transition' : 'bg-red-50'}`}>
                  <span className="text-lg">{flag}</span>
                  <span className="flex-1 font-medium">{label}</span>
                  {render.status === 'concluido' ? (
                    <>
                      <span className="text-xs text-gray-400">{formatBytes(render.tamanho_bytes)}</span>
                      <a
                        href={editorApi.downloadRenderUrl(id, render.id)}
                        download
                        className="flex items-center gap-1.5 bg-green-600 text-white px-3 py-1.5 rounded-lg text-xs font-medium hover:bg-green-700 transition"
                      >
                        <Download size={14} /> Baixar
                      </a>
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

      {/* Rodapé */}
      <div className="mt-8 text-center pb-8">
        <Link to="/" className="bg-purple-bg text-purple px-6 py-3 rounded-lg text-sm font-medium hover:bg-purple hover:text-white transition inline-flex items-center gap-2">
          <ArrowLeft size={14} /> Voltar à Fila de Edição
        </Link>
      </div>
    </div>
  )
}
