import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { editorApi } from '../api'
import { ArrowLeft, Check, RefreshCw, Scissors } from 'lucide-react'

const FLAG_STYLES = {
  VERDE: 'border-l-green-500 bg-green-50',
  AMARELO: 'border-l-yellow-500 bg-yellow-50',
  VERMELHO: 'border-l-red-500 bg-red-50',
  ROXO: 'border-l-purple bg-purple-bg',
}

const FLAG_DOTS = {
  VERDE: '🟢',
  AMARELO: '🟡',
  VERMELHO: '🔴',
  ROXO: '🟣',
}

export default function ValidarAlinhamento() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [edicao, setEdicao] = useState(null)
  const [alinhamento, setAlinhamento] = useState(null)
  const [janela, setJanela] = useState(null)
  const [segmentos, setSegmentos] = useState([])
  const [loading, setLoading] = useState(true)
  const [salvando, setSalvando] = useState(false)
  const [cortando, setCortando] = useState(false)
  const [error, setError] = useState('')
  const [polling, setPolling] = useState(false)

  const load = async () => {
    try {
      const e = await editorApi.obterEdicao(id)
      setEdicao(e)

      if (e.status === 'transcricao') {
        setPolling(true)
        return
      }
      setPolling(false)

      const result = await editorApi.obterAlinhamento(id)
      setAlinhamento(result.alinhamento)
      setJanela(result.janela)
      setSegmentos(result.alinhamento?.segmentos || [])
    } catch (err) {
      if (polling) return
      setError('Erro ao carregar alinhamento: ' + (err.response?.data?.detail || err.message))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [id])

  // Polling durante transcrição
  useEffect(() => {
    if (!polling) return
    const timer = setInterval(load, 5000)
    return () => clearInterval(timer)
  }, [polling])

  const updateSegmento = (index, field, value) => {
    const updated = [...segmentos]
    updated[index] = { ...updated[index], [field]: value }
    setSegmentos(updated)
  }

  const handleValidar = async () => {
    setSalvando(true)
    setError('')
    try {
      await editorApi.validarAlinhamento(id, { segmentos })
      // Aplicar corte automaticamente
      setCortando(true)
      try {
        await editorApi.aplicarCorte(id)
      } catch {}
      setCortando(false)
      navigate(`/edicao/${id}/conclusao`)
    } catch (err) {
      setError('Erro: ' + (err.response?.data?.detail || err.message))
    } finally {
      setSalvando(false)
    }
  }

  if (loading || !edicao) return <div className="text-center py-16 text-gray-400">Carregando...</div>

  if (polling) {
    return (
      <div className="max-w-3xl mx-auto text-center py-16">
        <RefreshCw size={32} className="mx-auto mb-4 text-purple animate-spin" />
        <h3 className="text-lg font-semibold mb-2">Transcrição em andamento...</h3>
        <p className="text-sm text-gray-400">O Gemini está analisando o áudio. Isso pode levar alguns minutos.</p>
        <p className="text-xs text-gray-300 mt-4">Atualizando automaticamente...</p>
      </div>
    )
  }

  if (!alinhamento) {
    return (
      <div className="max-w-3xl mx-auto text-center py-16">
        <p className="text-gray-400">Alinhamento não disponível. Inicie a transcrição primeiro.</p>
        <button onClick={() => navigate(`/edicao/${id}/letra`)} className="text-purple text-sm mt-4 hover:underline">
          Voltar para letra
        </button>
      </div>
    )
  }

  const dentroJanela = janela ? segmentos.filter(s => {
    const start = parseTimestamp(s.start)
    return start >= (janela.inicio || 0) && start <= (janela.fim || Infinity)
  }) : segmentos
  const foraJanela = janela ? segmentos.filter(s => {
    const start = parseTimestamp(s.start)
    return start < (janela.inicio || 0) || start > (janela.fim || Infinity)
  }) : []

  return (
    <div className="max-w-4xl mx-auto">
      <button onClick={() => navigate('/')} className="flex items-center gap-2 text-gray-400 hover:text-gray-600 text-sm mb-6">
        <ArrowLeft size={16} /> Voltar à fila
      </button>

      <div className="mb-6">
        <h2 className="text-2xl font-bold">{edicao.artista} — {edicao.musica}</h2>
        <p className="text-sm text-gray-400 mt-1">Passo 4 — Validar Alinhamento</p>
      </div>

      {/* Mini player YouTube */}
      {edicao.youtube_video_id && (
        <div className="bg-white rounded-xl shadow-sm border p-4 mb-4">
          <p className="text-xs text-gray-400 mb-2">Ouça enquanto valida o alinhamento:</p>
          <iframe
            width="100%"
            height="80"
            src={`https://www.youtube.com/embed/${edicao.youtube_video_id}?rel=0`}
            allow="autoplay; encrypted-media"
            allowFullScreen
            className="rounded-lg"
            style={{ maxWidth: '100%' }}
          />
        </div>
      )}

      {/* Info bar */}
      <div className="flex items-center gap-4 mb-6 flex-wrap">
        <div className="bg-white rounded-lg border px-4 py-2 text-sm">
          Rota <span className="font-bold text-purple">{alinhamento.rota}</span>
        </div>
        <div className="bg-white rounded-lg border px-4 py-2 text-sm">
          Confiança <span className="font-bold">{((alinhamento.confianca_media || 0) * 100).toFixed(0)}%</span>
        </div>
        {janela && (
          <div className="bg-white rounded-lg border px-4 py-2 text-sm flex items-center gap-2">
            <Scissors size={14} className="text-purple" />
            Corte: {formatSec(janela.inicio)} → {formatSec(janela.fim)} ({formatSec(janela.duracao)})
          </div>
        )}
        <div className="flex gap-2 text-xs">
          <span>🟢 {segmentos.filter(s => s.flag === 'VERDE').length}</span>
          <span>🟡 {segmentos.filter(s => s.flag === 'AMARELO').length}</span>
          <span>🔴 {segmentos.filter(s => s.flag === 'VERMELHO').length}</span>
          <span>🟣 {segmentos.filter(s => s.flag === 'ROXO').length}</span>
        </div>
      </div>

      {error && <div className="bg-red-50 text-red-600 text-sm rounded-lg p-3 mb-4">{error}</div>}

      {/* Segmentos dentro da janela */}
      <div className="mb-4">
        <h4 className="text-sm font-semibold text-gray-500 mb-2 uppercase tracking-wider">Dentro do corte ({dentroJanela.length} segmentos)</h4>
        <div className="space-y-2">
          {segmentos.map((seg, i) => {
            const isDentro = !janela || (parseTimestamp(seg.start) >= (janela.inicio || 0) && parseTimestamp(seg.start) <= (janela.fim || Infinity))
            return (
              <div
                key={i}
                className={`border-l-4 rounded-lg p-3 ${FLAG_STYLES[seg.flag] || 'border-l-gray-300 bg-gray-50'} ${!isDentro ? 'opacity-40' : ''}`}
              >
                <div className="flex items-start gap-3">
                  <span className="text-xs mt-1">{FLAG_DOTS[seg.flag]}</span>
                  <span className="text-xs text-gray-400 mt-1 font-mono w-24 shrink-0">
                    {seg.start} → {seg.end}
                  </span>
                  <div className="flex-1">
                    <input
                      value={seg.texto_final || ''}
                      onChange={e => updateSegmento(i, 'texto_final', e.target.value)}
                      className="w-full bg-transparent border-b border-transparent hover:border-gray-300 focus:border-purple outline-none text-sm py-1"
                    />
                    {seg.texto_gemini && seg.texto_gemini !== seg.texto_final && (
                      <div className="text-xs text-gray-400 mt-1">Gemini: {seg.texto_gemini}</div>
                    )}
                    {seg.candidato_letra && (
                      <div className="text-xs text-yellow-600 mt-1">Candidato: {seg.candidato_letra}</div>
                    )}
                  </div>
                  <span className="text-xs text-gray-300">{((seg.confianca || 0) * 100).toFixed(0)}%</span>
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Ações */}
      <div className="flex gap-3 mt-6 sticky bottom-4">
        <button
          onClick={handleValidar}
          disabled={salvando || cortando}
          className="flex-1 flex items-center justify-center gap-2 bg-green-500 text-white py-3 rounded-lg font-medium hover:bg-green-600 transition disabled:opacity-50"
        >
          <Check size={18} />
          {cortando ? 'Aplicando corte...' : salvando ? 'Salvando...' : 'Aprovar Alinhamento e Continuar'}
        </button>
      </div>
    </div>
  )
}

function parseTimestamp(ts) {
  if (!ts) return 0
  const parts = ts.replace(',', '.').split(':')
  if (parts.length === 3) return parseFloat(parts[0]) * 3600 + parseFloat(parts[1]) * 60 + parseFloat(parts[2])
  if (parts.length === 2) return parseFloat(parts[0]) * 60 + parseFloat(parts[1])
  return parseFloat(parts[0])
}

function formatSec(sec) {
  if (!sec && sec !== 0) return '--:--'
  const m = Math.floor(sec / 60)
  const s = Math.floor(sec % 60)
  return `${m}:${String(s).padStart(2, '0')}`
}
