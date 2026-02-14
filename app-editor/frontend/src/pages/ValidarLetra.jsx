import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { editorApi } from '../api'
import { ArrowLeft, Search, Check, RefreshCw } from 'lucide-react'

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

  useEffect(() => {
    editorApi.obterEdicao(id).then(e => {
      setEdicao(e)
      if (e.eh_instrumental) {
        navigate(`/edicao/${id}/conclusao`)
        return
      }
      setLoading(false)
    })
  }, [id])

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
      // Iniciar download de vídeo + transcrição
      try { await editorApi.garantirVideo(id) } catch {}
      try { await editorApi.iniciarTranscricao(id) } catch {}
      navigate(`/edicao/${id}/alinhamento`)
    } catch (err) {
      setError('Erro ao salvar: ' + (err.response?.data?.detail || err.message))
    } finally {
      setSalvando(false)
    }
  }

  if (loading || !edicao) return <div className="text-center py-16 text-gray-400">Carregando...</div>

  return (
    <div className="max-w-3xl mx-auto">
      <button onClick={() => navigate('/')} className="flex items-center gap-2 text-gray-400 hover:text-gray-600 text-sm mb-6">
        <ArrowLeft size={16} /> Voltar à fila
      </button>

      <div className="mb-6">
        <h2 className="text-2xl font-bold">{edicao.artista} — {edicao.musica}</h2>
        <p className="text-sm text-gray-400 mt-1">
          {edicao.compositor} {edicao.opera ? `· ${edicao.opera}` : ''} · {edicao.idioma?.toUpperCase()}
        </p>
      </div>

      <div className="bg-white rounded-xl shadow-sm border p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold text-lg">Passo 2 — Validar Letra</h3>
          <div className="flex gap-2">
            <button
              onClick={buscarLetra}
              disabled={buscando}
              className="flex items-center gap-2 bg-purple-bg text-purple px-4 py-2 rounded-lg text-sm font-medium hover:bg-purple hover:text-white transition disabled:opacity-50"
            >
              {buscando ? <RefreshCw size={14} className="animate-spin" /> : <Search size={14} />}
              {buscando ? 'Buscando...' : 'Buscar Letra'}
            </button>
          </div>
        </div>

        {fonte && (
          <div className="mb-3 text-xs text-gray-400">
            Fonte: <span className="font-medium">{fonte}</span>
          </div>
        )}

        {error && <div className="bg-red-50 text-red-600 text-sm rounded-lg p-3 mb-4">{error}</div>}

        <textarea
          value={letra}
          onChange={e => setLetra(e.target.value)}
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
