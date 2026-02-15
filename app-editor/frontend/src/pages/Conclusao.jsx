import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { editorApi } from '../api'
import { ArrowLeft, Download, Play, RefreshCw, CheckCircle, XCircle, ExternalLink, Pencil, RotateCcw, Eye, MessageSquare } from 'lucide-react'

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
  const [editandoCorte, setEditandoCorte] = useState(false)
  const [corteInicio, setCorteInicio] = useState('')
  const [corteFim, setCorteFim] = useState('')
  const [reaplicando, setReaplicando] = useState(false)
  const [notasRevisao, setNotasRevisao] = useState('')
  const [mostrarRevisao, setMostrarRevisao] = useState(false)
  const [aprovando, setAprovando] = useState(false)

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

  // Polling durante tradução, renderização ou preview
  useEffect(() => {
    if (!edicao || !['renderizando', 'traducao', 'preview'].includes(edicao.status)) return
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

  const handleRenderizarPreview = async () => {
    setRenderizando(true)
    setError('')
    try {
      await editorApi.renderizarPreview(id)
      await load()
    } catch (err) {
      setError('Erro na renderização: ' + (err.response?.data?.detail || err.message))
    } finally {
      setRenderizando(false)
    }
  }

  const handleAprovarPreview = async () => {
    setAprovando(true)
    setError('')
    try {
      await editorApi.aprovarPreview(id, { aprovado: true })
      await load()
    } catch (err) {
      setError('Erro ao aprovar: ' + (err.response?.data?.detail || err.message))
    } finally {
      setAprovando(false)
    }
  }

  const handleSolicitarRevisao = async () => {
    setAprovando(true)
    setError('')
    try {
      await editorApi.aprovarPreview(id, { aprovado: false, notas_revisao: notasRevisao })
      setMostrarRevisao(false)
      setNotasRevisao('')
      await load()
    } catch (err) {
      setError('Erro ao solicitar revisão: ' + (err.response?.data?.detail || err.message))
    } finally {
      setAprovando(false)
    }
  }

  const handleRenderizarTodos = async () => {
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

  const parseMMSS = (val) => {
    const parts = val.split(':')
    if (parts.length === 2) return parseFloat(parts[0]) * 60 + parseFloat(parts[1])
    return parseFloat(val) || 0
  }

  const handleReaplicarCorte = async (params) => {
    setReaplicando(true)
    setError('')
    try {
      await editorApi.aplicarCorte(id, params)
      await load()
      setEditandoCorte(false)
    } catch (err) {
      setError('Erro ao reaplicar corte: ' + (err.response?.data?.detail || err.message))
    } finally {
      setReaplicando(false)
    }
  }

  if (loading || !edicao) return <div className="text-center py-16 text-gray-400">Carregando...</div>

  const concluidos = renders.filter(r => r.status === 'concluido')
  const erros = renders.filter(r => r.status === 'erro')
  const todosOk = concluidos.length === 7 && erros.length === 0
  const isConcluido = edicao.status === 'concluido'
  const isPreviewPronto = edicao.status === 'preview_pronto'
  const isPreview = edicao.status === 'preview'
  const isRevisao = edicao.status === 'revisao'

  // Find the preview render (idioma original)
  const previewRender = renders.find(r => r.idioma === edicao.idioma && r.status === 'concluido')

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

      {/* Card de revisão */}
      {isRevisao && edicao.notas_revisao && (
        <div className="bg-yellow-50 border border-yellow-300 rounded-xl p-5 mb-6">
          <div className="flex items-start gap-3">
            <MessageSquare size={20} className="text-yellow-600 mt-0.5" />
            <div className="flex-1">
              <h3 className="font-semibold text-yellow-800 mb-1">Revisão Solicitada</h3>
              <p className="text-sm text-yellow-700 whitespace-pre-wrap">{edicao.notas_revisao}</p>
              <button
                onClick={() => navigate(`/edicao/${id}/alinhamento`)}
                className="mt-3 flex items-center gap-2 bg-yellow-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-yellow-700 transition"
              >
                <ArrowLeft size={14} />
                Voltar ao Alinhamento
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Preview pronto — player + aprovação */}
      {isPreviewPronto && previewRender && (
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-6 mb-6">
          <h3 className="font-semibold text-blue-800 mb-3 flex items-center gap-2">
            <Eye size={18} /> Preview — {edicao.idioma.toUpperCase()}
          </h3>
          <video
            src={editorApi.downloadRenderUrl(id, previewRender.id)}
            controls
            className="w-full max-w-md mx-auto rounded-lg shadow-md mb-4"
            style={{ maxHeight: '500px' }}
          />
          <div className="flex gap-3 justify-center flex-wrap">
            <button
              onClick={handleAprovarPreview}
              disabled={aprovando}
              className="flex items-center gap-2 bg-green-600 text-white px-5 py-2.5 rounded-lg text-sm font-medium hover:bg-green-700 transition disabled:opacity-50"
            >
              {aprovando ? <RefreshCw size={14} className="animate-spin" /> : <CheckCircle size={14} />}
              Aprovar e Renderizar Todos
            </button>
            <button
              onClick={() => setMostrarRevisao(!mostrarRevisao)}
              className="flex items-center gap-2 bg-yellow-500 text-white px-5 py-2.5 rounded-lg text-sm font-medium hover:bg-yellow-600 transition"
            >
              <MessageSquare size={14} />
              Solicitar Revisão
            </button>
          </div>
          {mostrarRevisao && (
            <div className="mt-4 max-w-md mx-auto">
              <textarea
                value={notasRevisao}
                onChange={e => setNotasRevisao(e.target.value)}
                placeholder="Descreva o que precisa ser ajustado..."
                rows={3}
                className="w-full border rounded-lg p-3 text-sm"
              />
              <button
                onClick={handleSolicitarRevisao}
                disabled={aprovando || !notasRevisao.trim()}
                className="mt-2 w-full bg-yellow-500 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-yellow-600 transition disabled:opacity-50"
              >
                {aprovando ? 'Enviando...' : 'Enviar Revisão'}
              </button>
            </div>
          )}
        </div>
      )}

      {/* Resumo */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white rounded-xl border p-4">
          <div className="text-xs text-gray-400 mb-1">Status</div>
          <div className="font-semibold text-sm capitalize">{edicao.status}</div>
        </div>
        <div className="bg-white rounded-xl border p-4">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-gray-400">Duração do Corte</span>
            <button
              onClick={() => {
                setEditandoCorte(!editandoCorte)
                if (!editandoCorte && edicao) {
                  const toMMSS = (sec) => { const m = Math.floor(sec / 60); const s = Math.floor(sec % 60); return `${m}:${String(s).padStart(2, '0')}` }
                  setCorteInicio(toMMSS(edicao.janela_inicio_sec || 0))
                  setCorteFim(toMMSS(edicao.janela_fim_sec || 0))
                }
              }}
              className="text-purple hover:text-purple/70"
              title="Editar corte"
            >
              <Pencil size={12} />
            </button>
          </div>
          <div className="font-semibold text-sm">{formatSec(edicao.duracao_corte_sec)}</div>
          <div className="text-xs text-gray-400">{formatSec(edicao.janela_inicio_sec)} → {formatSec(edicao.janela_fim_sec)}</div>
          {editandoCorte && (
            <div className="mt-2 space-y-2 border-t pt-2">
              <div className="flex gap-2 items-center">
                <input
                  value={corteInicio}
                  onChange={e => setCorteInicio(e.target.value)}
                  placeholder="MM:SS"
                  className="w-20 border rounded px-2 py-1 text-xs font-mono"
                />
                <span className="text-xs text-gray-400">→</span>
                <input
                  value={corteFim}
                  onChange={e => setCorteFim(e.target.value)}
                  placeholder="MM:SS"
                  className="w-20 border rounded px-2 py-1 text-xs font-mono"
                />
              </div>
              <button
                onClick={() => handleReaplicarCorte({
                  janela_inicio: parseMMSS(corteInicio),
                  janela_fim: parseMMSS(corteFim),
                })}
                disabled={reaplicando}
                className="w-full bg-purple text-white text-xs px-2 py-1 rounded hover:bg-purple/90 disabled:opacity-50"
              >
                {reaplicando ? 'Reaplicando...' : 'Reaplicar Corte'}
              </button>
            </div>
          )}
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
        <button
          onClick={() => navigate(`/edicao/${id}/alinhamento`)}
          className="flex items-center gap-2 bg-gray-100 text-gray-600 px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-200 transition"
        >
          <ArrowLeft size={14} />
          Voltar ao Alinhamento
        </button>
        <button
          onClick={() => handleReaplicarCorte()}
          disabled={reaplicando}
          className="flex items-center gap-2 bg-gray-100 text-gray-600 px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-200 transition disabled:opacity-50"
        >
          <RotateCcw size={14} />
          {reaplicando ? 'Recalculando...' : 'Refazer Corte'}
        </button>
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
        {/* Preview button — shown when no renders yet or in revisão */}
        {(!isConcluido && !isPreviewPronto && !isPreview && edicao.status !== 'renderizando') && (
          <button
            onClick={handleRenderizarPreview}
            disabled={renderizando || traduzindo || edicao.status === 'traducao'}
            className="flex items-center gap-2 bg-purple text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-purple/90 transition disabled:opacity-50"
          >
            {renderizando || isPreview ? <RefreshCw size={14} className="animate-spin" /> : <Eye size={14} />}
            {renderizando || isPreview ? 'Renderizando preview...' : 'Renderizar Preview'}
          </button>
        )}
        {/* Spinner during preview rendering */}
        {isPreview && (
          <div className="flex items-center gap-2 bg-blue-100 text-blue-700 px-4 py-2 rounded-lg text-sm font-medium">
            <RefreshCw size={14} className="animate-spin" />
            Renderizando preview...
          </div>
        )}
        {/* Re-renderizar todos (only shown after concluido or if user wants to redo) */}
        {isConcluido && (
          <button
            onClick={handleRenderizarTodos}
            disabled={renderizando || edicao.status === 'renderizando'}
            className="flex items-center gap-2 bg-purple text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-purple/90 transition disabled:opacity-50"
          >
            {renderizando || edicao.status === 'renderizando' ? <RefreshCw size={14} className="animate-spin" /> : <Play size={14} />}
            {renderizando || edicao.status === 'renderizando' ? 'Renderizando...' : 'Re-renderizar Todos'}
          </button>
        )}
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
