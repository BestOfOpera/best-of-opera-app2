import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { editorApi } from '../api'
import { ArrowLeft, Search, Check, RefreshCw, Loader2, ExternalLink } from 'lucide-react'

export default function ValidarLetra() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [edicao, setEdicao] = useState(null)
  const [letra, setLetra] = useState('')
  const [fonte, setFonte] = useState('')
  const [loading, setLoading] = useState(true)
  const [buscando, setBuscando] = useState(false)
  const [salvando, setSalvando] = useState(false)
  const [error, setError] = useState('')
  const [videoStatus, setVideoStatus] = useState(null)

  useEffect(() => {
    editorApi.obterEdicao(id).then(e => {
      setEdicao(e)
      if (e.eh_instrumental) {
        navigate(`/edicao/${id}/conclusao`)
        return
      }
      setLoading(false)
      // Iniciar download do vídeo em background se ainda não foi feito
      if (!e.arquivo_video_completo) {
        editorApi.garantirVideo(id).catch(() => {})
      }
    })
  }, [id])

  // Polling do status do vídeo
  useEffect(() => {
    if (!edicao) return
    const check = () => {
      editorApi.statusVideo(id).then(s => setVideoStatus(s)).catch(() => {})
    }
    check()
    const interval = setInterval(check, 5000)
    return () => clearInterval(interval)
  }, [edicao, id])

  const buscarLetra = async () => {
    setBuscando(true)
    setError('')
    try {
      const result = await editorApi.buscarLetra(id)
      setLetra(result.letra || '')
      setFonte(result.fonte || 'desconhecida')
    } catch (err) {
      setError('Erro ao buscar letra: ' + (err.response?.data?.detail || err.message))
    } finally {
      setBuscando(false)
    }
  }

  const aprovarLetra = async () => {
    if (!letra.trim()) return
    setSalvando(true)
    setError('')
    try {
      await editorApi.aprovarLetra(id, { letra, fonte: fonte || 'manual' })

      // Disparar transcrição em background (não esperar — extração de áudio pode demorar)
      editorApi.iniciarTranscricao(id).catch(() => {})

      navigate(`/edicao/${id}/alinhamento`)
    } catch (err) {
      setError('Erro ao salvar: ' + (err.response?.data?.detail || err.message))
      setSalvando(false)
    }
  }

  if (loading || !edicao) return <div className="text-center py-16 text-gray-400">Carregando...</div>

  const videoReady = videoStatus?.video_completo
  const jaTemLetra = letra.trim().length > 0

  return (
    <div className="max-w-3xl mx-auto">
      <button onClick={() => navigate('/')} className="flex items-center gap-2 text-gray-400 hover:text-gray-600 text-sm mb-6">
        <ArrowLeft size={16} /> Voltar à fila
      </button>

      <div className="mb-6">
        <h2 className="text-2xl font-bold">{edicao.artista} — {edicao.musica}</h2>
        <p className="text-sm text-gray-400 mt-1">
          {edicao.compositor} {edicao.opera ? `· ${edicao.opera}` : ''} · {edicao.idioma?.toUpperCase()}
          {edicao.youtube_url && (
            <a href={edicao.youtube_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 ml-3 text-purple hover:underline">
              <ExternalLink size={12} /> Abrir no YouTube
            </a>
          )}
        </p>
      </div>

      {/* Status do vídeo */}
      <div className={`flex items-center gap-2 text-xs px-3 py-2 rounded-lg mb-4 ${videoReady ? 'bg-green-50 text-green-700' : 'bg-blue-50 text-blue-700'}`}>
        {videoReady ? (
          <><Check size={14} /> Vídeo disponível</>
        ) : (
          <><Loader2 size={14} className="animate-spin" /> Baixando vídeo em background...</>
        )}
      </div>

      {/* Mini player YouTube */}
      {edicao.youtube_video_id && (
        <div className="bg-white rounded-xl shadow-sm border p-4 mb-4">
          <p className="text-xs text-gray-400 mb-2">Ouça enquanto valida a letra:</p>
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

      <div className="bg-white rounded-xl shadow-sm border p-6">
        <h3 className="font-semibold text-lg mb-4">Passo 2 — Validar Letra</h3>

        {/* Botões de ação - bem visíveis */}
        <div className="flex flex-wrap gap-2 mb-4">
          <button
            onClick={buscarLetra}
            disabled={buscando}
            className="flex items-center gap-2 bg-purple text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-purple/90 transition disabled:opacity-50"
          >
            {buscando ? <RefreshCw size={14} className="animate-spin" /> : <Search size={14} />}
            {buscando ? 'Buscando...' : jaTemLetra ? 'Buscar Novamente' : 'Buscar Letra (Gemini)'}
          </button>
        </div>

        {fonte && (
          <div className="mb-3 text-xs text-gray-400">
            Fonte: <span className="font-medium">{fonte}</span>
            {fonte === 'gemini' && <span className="ml-2 text-yellow-600">— Verifique a letra antes de aprovar</span>}
          </div>
        )}

        {error && <div className="bg-red-50 text-red-600 text-sm rounded-lg p-3 mb-4">{error}</div>}

        <textarea
          value={letra}
          onChange={e => { setLetra(e.target.value); if (!fonte) setFonte('manual') }}
          placeholder="Cole ou busque a letra original aqui..."
          className="w-full border rounded-lg px-4 py-3 text-sm font-mono min-h-[400px] resize-y"
        />

        <div className="flex items-center justify-between mt-4">
          <span className="text-xs text-gray-400">{letra.split('\n').filter(l => l.trim()).length} versos</span>
          <button
            onClick={aprovarLetra}
            disabled={salvando || !letra.trim()}
            className="flex items-center gap-2 bg-green-500 text-white px-6 py-2 rounded-lg text-sm font-medium hover:bg-green-600 transition disabled:opacity-50"
          >
            <Check size={16} />
            {salvando ? 'Salvando...' : 'Aprovar Letra e Continuar'}
          </button>
        </div>
      </div>
    </div>
  )
}
