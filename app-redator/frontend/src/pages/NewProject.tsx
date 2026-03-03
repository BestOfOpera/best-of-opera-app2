import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, DetectedMetadata } from '../api'

const CATEGORIES = [
  '', 'Aria', 'Duet', 'Chorus', 'Overture', 'Recitative',
  'Ensemble', 'Ballet', 'Intermezzo', 'Other',
]

const HOOK_CATEGORIES = [
  { key: 'curiosidade_musica', label: 'Curiosidade Sobre a Música', emoji: '🎵', desc: 'Origem, contexto ou fato surpreendente sobre a música' },
  { key: 'curiosidade_interprete', label: 'Curiosidade Sobre o Intérprete', emoji: '🎤', desc: 'Momento marcante, história de bastidor ou peculiaridade' },
  { key: 'curiosidade_compositor', label: 'Curiosidade Sobre o Compositor', emoji: '✍️', desc: 'Circunstâncias da criação, rivalidades ou inspirações' },
  { key: 'valor_historico', label: 'Valor Histórico', emoji: '📜', desc: 'Por que esta gravação é um marco na ópera' },
  { key: 'climax_vocal', label: 'Clímax Vocal', emoji: '🔥', desc: 'A nota impossível ou passagem tecnicamente extraordinária' },
  { key: 'peso_emocional', label: 'Peso Emocional', emoji: '💔', desc: 'Drama do enredo ou emoção visível do intérprete' },
  { key: 'transformacao_progressiva', label: 'Transformação Progressiva', emoji: '🌅', desc: 'Como a interpretação evolui do início ao clímax' },
  { key: 'dueto_encontro', label: 'Dueto / Encontro', emoji: '🤝', desc: 'Química e diálogo entre vozes' },
  { key: 'reacao_impacto_visual', label: 'Reação / Impacto Visual', emoji: '😱', desc: 'Plateia em êxtase, aplausos ou momento viral' },
  { key: 'conexao_cultural', label: 'Conexão Cultural', emoji: '🌍', desc: 'Referências em cinema, TV ou cultura popular' },
  { key: 'prefiro_escrever', label: 'Prefiro Escrever', emoji: '✏️', desc: 'Escreva seu próprio ângulo criativo' },
] as const

interface Interpreter {
  artist: string
  nationality: string
  nationality_flag: string
  voice_type: string
  birth_date: string
  death_date: string
}

const emptyInterpreter = (): Interpreter => ({
  artist: '', nationality: '', nationality_flag: '',
  voice_type: '', birth_date: '', death_date: '',
})

export default function NewProject() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Step A — human input
  const [youtubeUrl, setYoutubeUrl] = useState('')
  const [hook, setHook] = useState('')
  const [hookCategory, setHookCategory] = useState('')
  const [category, setCategory] = useState('')
  const [cutStart, setCutStart] = useState('')
  const [cutEnd, setCutEnd] = useState('')

  // Screenshot & detection
  const [screenshotFile, setScreenshotFile] = useState<File | null>(null)
  const [screenshotPreview, setScreenshotPreview] = useState('')
  const [detecting, setDetecting] = useState(false)
  const [detected, setDetected] = useState(false)
  const [confidence, setConfidence] = useState('')

  // Step B — shared fields
  const [shared, setShared] = useState({
    work: '', composer: '', composition_year: '', album_opera: '',
  })

  // Step B — per-interpreter fields
  const [interpreters, setInterpreters] = useState<Interpreter[]>([emptyInterpreter()])

  const isMulti = category === 'Duet' || category === 'Ensemble'

  const setSharedField = (key: string, value: string) =>
    setShared(prev => ({ ...prev, [key]: value }))

  const setInterpreterField = (index: number, key: keyof Interpreter, value: string) =>
    setInterpreters(prev => prev.map((interp, i) =>
      i === index ? { ...interp, [key]: value } : interp
    ))

  const addInterpreter = () =>
    setInterpreters(prev => [...prev, emptyInterpreter()])

  const removeInterpreter = (index: number) =>
    setInterpreters(prev => prev.filter((_, i) => i !== index))

  // When category changes to Duet/Ensemble and only 1 interpreter, auto-add empty
  useEffect(() => {
    if (isMulti && interpreters.length < 2) {
      setInterpreters(prev => [...prev, emptyInterpreter()])
    }
  }, [category])

  const handleScreenshot = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setScreenshotFile(file)
    if (screenshotPreview) URL.revokeObjectURL(screenshotPreview)
    setScreenshotPreview(URL.createObjectURL(file))
    setDetected(false)
  }

  const handleDetect = async () => {
    if (!screenshotFile) return
    setDetecting(true)
    setError('')
    try {
      const result: DetectedMetadata = await api.detectMetadata(screenshotFile, youtubeUrl)
      setShared({
        work: result.work || '',
        composer: result.composer || '',
        composition_year: result.composition_year || '',
        album_opera: result.album_opera || '',
      })

      // Parse artists by " & " for multi-interpreter categories
      const artistStr = result.artist || ''
      const artists = artistStr.includes(' & ')
        ? artistStr.split(' & ').map(a => a.trim())
        : [artistStr]

      const nationalities = (result.nationality || '').split(' / ').map(s => s.trim())
      const flags = (result.nationality_flag || '').split(' / ').map(s => s.trim())
      // Also split flags by space (emoji pairs like "🇷🇺 🇦🇿")
      const flagsSplit = flags.length === 1 && artists.length > 1
        ? (result.nationality_flag || '').trim().split(/\s+/)
        : flags
      const voiceTypes = (result.voice_type || '').split(' / ').map(s => s.trim())
      const birthDates = (result.birth_date || '').split(' / ').map(s => s.trim())
      const deathDates = (result.death_date || '').split(' / ').map(s => s.trim())

      const newInterpreters: Interpreter[] = artists.map((a, i) => ({
        artist: a,
        nationality: nationalities[i] || nationalities[0] || '',
        nationality_flag: flagsSplit[i] || flagsSplit[0] || '',
        voice_type: voiceTypes[i] || voiceTypes[0] || '',
        birth_date: birthDates[i] || birthDates[0] || '',
        death_date: deathDates[i] || deathDates[0] || '',
      }))

      setInterpreters(newInterpreters)
      setConfidence(result.confidence || 'high')
      setDetected(true)
    } catch (err: any) {
      setError(`Falha na detecção automática: ${err.message}. Preencha os campos manualmente.`)
      setDetected(true)
      setConfidence('low')
    } finally {
      setDetecting(false)
    }
  }

  const isValidMMSS = (v: string) => /^\d{2}:\d{2}$/.test(v)
  const hookValid = hookCategory === 'prefiro_escrever'
    ? hook.trim().length > 0
    : hookCategory.length > 0
  const stepAComplete = hookValid && category && isValidMMSS(cutStart) && isValidMMSS(cutEnd)
  const canSubmit = stepAComplete && detected && interpreters[0]?.artist && shared.work && shared.composer

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!canSubmit) return
    setError('')
    setLoading(true)
    try {
      // Join interpreter fields with " & " / " / "
      const joinField = (key: keyof Interpreter) =>
        interpreters.map(i => i[key]).filter(Boolean).join(key === 'artist' ? ' & ' : ' / ')

      const project = await api.createProject({
        youtube_url: youtubeUrl,
        hook,
        hook_category: hookCategory,
        category,
        cut_start: cutStart,
        cut_end: cutEnd,
        artist: joinField('artist'),
        work: shared.work,
        composer: shared.composer,
        composition_year: shared.composition_year,
        nationality: joinField('nationality'),
        nationality_flag: joinField('nationality_flag'),
        voice_type: joinField('voice_type'),
        birth_date: joinField('birth_date'),
        death_date: joinField('death_date'),
        album_opera: shared.album_opera,
      })
      await api.generate(project.id)
      navigate(`/project/${project.id}/approve-overlay`)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const renderInterpreterBlock = (interp: Interpreter, index: number) => (
    <div key={index} style={{
      padding: 16, borderRadius: 8, border: '1px solid var(--border)',
      background: isMulti ? '#FAFAFA' : 'transparent',
      marginBottom: isMulti ? 12 : 0,
    }}>
      {isMulti && (
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--purple)' }}>
            Intérprete {index + 1}
          </span>
          {interpreters.length > 1 && (
            <button
              type="button"
              className="btn-secondary btn-small"
              onClick={() => removeInterpreter(index)}
              style={{ fontSize: 11, padding: '2px 8px' }}
            >
              Remover
            </button>
          )}
        </div>
      )}
      <div className="form-row">
        <div className="form-group">
          <label>Artista *</label>
          <input value={interp.artist} onChange={(e) => setInterpreterField(index, 'artist', e.target.value)} />
        </div>
        <div className="form-group">
          <label>Nacionalidade</label>
          <input value={interp.nationality} onChange={(e) => setInterpreterField(index, 'nationality', e.target.value)} />
        </div>
      </div>
      <div className="form-row">
        <div className="form-group">
          <label>Emoji da Bandeira</label>
          <input value={interp.nationality_flag} onChange={(e) => setInterpreterField(index, 'nationality_flag', e.target.value)} style={{ fontSize: 20 }} />
        </div>
        <div className="form-group">
          <label>Tipo de Voz / Instrumento</label>
          <input value={interp.voice_type} onChange={(e) => setInterpreterField(index, 'voice_type', e.target.value)} />
        </div>
      </div>
      <div className="form-row">
        <div className="form-group">
          <label>Data de Nascimento</label>
          <input value={interp.birth_date} onChange={(e) => setInterpreterField(index, 'birth_date', e.target.value)} placeholder="dd/mm/yyyy" />
        </div>
        <div className="form-group">
          <label>Data de Falecimento</label>
          <input value={interp.death_date} onChange={(e) => setInterpreterField(index, 'death_date', e.target.value)} placeholder="Vazio se vivo" />
        </div>
      </div>
    </div>
  )

  return (
    <div>
      <h2 style={{ marginBottom: 24 }}>Novo Projeto</h2>
      {error && <div className="error-msg">{error}</div>}
      <form onSubmit={handleSubmit}>
        {/* STEP A — Human input */}
        <div className="card" style={{ marginBottom: 16 }}>
          <h3 style={{ marginBottom: 16, fontSize: 16 }}>Etapa A — Seus Dados</h3>

          {/* Screenshot upload */}
          <div className="form-group">
            <label>Screenshot do YouTube *</label>
            <p style={{ fontSize: 13, color: 'var(--text-light)', marginBottom: 8 }}>
              Tire um screenshot da página do vídeo no YouTube (mostrando título, descrição, nome do canal)
            </p>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              onChange={handleScreenshot}
              style={{ display: 'none' }}
            />
            <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
              <button
                type="button"
                className="btn-secondary"
                onClick={() => fileInputRef.current?.click()}
              >
                {screenshotFile ? 'Trocar Screenshot' : 'Enviar Screenshot'}
              </button>
              {screenshotFile && (
                <button
                  type="button"
                  className="btn-primary"
                  onClick={handleDetect}
                  disabled={detecting}
                >
                  {detecting ? 'Detectando...' : detected ? 'Re-detectar' : 'Detectar Metadados'}
                </button>
              )}
            </div>
            {screenshotPreview && (
              <img
                src={screenshotPreview}
                alt="YouTube screenshot"
                style={{
                  marginTop: 12,
                  maxWidth: '100%',
                  maxHeight: 250,
                  borderRadius: 8,
                  border: '1px solid var(--border)',
                }}
              />
            )}
          </div>

          <div className="form-group">
            <label>Link do YouTube (opcional)</label>
            <input
              value={youtubeUrl}
              onChange={(e) => setYoutubeUrl(e.target.value)}
              placeholder="https://www.youtube.com/watch?v=..."
            />
          </div>

          <div className="form-group">
            <label>Categoria do Gancho *</label>
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(2, 1fr)',
              gap: 8,
              marginBottom: 12,
            }}>
              {HOOK_CATEGORIES.map((hc) => (
                <button
                  key={hc.key}
                  type="button"
                  onClick={() => {
                    setHookCategory(hc.key)
                    if (hc.key !== 'prefiro_escrever' && hookCategory === 'prefiro_escrever') {
                      setHook('')
                    }
                  }}
                  style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: 8,
                    padding: '10px 12px',
                    borderRadius: 8,
                    border: hookCategory === hc.key
                      ? '2px solid var(--purple)'
                      : '1px solid var(--border)',
                    background: hookCategory === hc.key ? '#F3E8FF' : '#FFF',
                    cursor: 'pointer',
                    textAlign: 'left',
                    transition: 'all 0.15s',
                  }}
                >
                  <span style={{ fontSize: 20, lineHeight: 1 }}>{hc.emoji}</span>
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)' }}>{hc.label}</div>
                    <div style={{ fontSize: 11, color: 'var(--text-light)', marginTop: 2 }}>{hc.desc}</div>
                  </div>
                </button>
              ))}
            </div>

            {hookCategory && hookCategory !== 'prefiro_escrever' && (
              <div style={{ marginTop: 4 }}>
                <label style={{ fontSize: 13 }}>Complemento (opcional)</label>
                <textarea
                  value={hook}
                  onChange={(e) => setHook(e.target.value)}
                  placeholder="Quer acrescentar algo ao prompt?"
                  style={{ minHeight: 60 }}
                />
              </div>
            )}

            {hookCategory === 'prefiro_escrever' && (
              <div style={{ marginTop: 4 }}>
                <label style={{ fontSize: 13 }}>Seu gancho *</label>
                <textarea
                  value={hook}
                  onChange={(e) => setHook(e.target.value)}
                  placeholder="Escreva seu ângulo criativo..."
                  style={{ minHeight: 80 }}
                />
              </div>
            )}
          </div>

          <div className="form-row">
            <div className="form-group">
              <label>Categoria *</label>
              <select value={category} onChange={(e) => setCategory(e.target.value)}>
                {CATEGORIES.map((c) => (
                  <option key={c} value={c}>{c || '— Selecionar —'}</option>
                ))}
              </select>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
              <div className="form-group">
                <label>Início do Corte *</label>
                <input
                  value={cutStart}
                  onChange={(e) => setCutStart(e.target.value)}
                  placeholder="01:15"
                  maxLength={5}
                  style={cutStart && !isValidMMSS(cutStart) ? { borderColor: '#EF4444' } : {}}
                />
                {cutStart && !isValidMMSS(cutStart) && (
                  <span style={{ fontSize: 11, color: '#EF4444' }}>Formato: MM:SS (ex: 01:15)</span>
                )}
              </div>
              <div className="form-group">
                <label>Fim do Corte *</label>
                <input
                  value={cutEnd}
                  onChange={(e) => setCutEnd(e.target.value)}
                  placeholder="02:45"
                  maxLength={5}
                  style={cutEnd && !isValidMMSS(cutEnd) ? { borderColor: '#EF4444' } : {}}
                />
                {cutEnd && !isValidMMSS(cutEnd) && (
                  <span style={{ fontSize: 11, color: '#EF4444' }}>Formato: MM:SS (ex: 02:45)</span>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* STEP B — Auto-detected fields */}
        {(detected || detecting) && (
          <div className="card" style={{ marginBottom: 24, opacity: detecting ? 0.6 : 1, transition: 'opacity 0.3s' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <h3 style={{ fontSize: 16 }}>Etapa B — Metadados Detectados</h3>
              {detected && !detecting && (
                <span style={{
                  fontSize: 13,
                  padding: '4px 10px',
                  borderRadius: 12,
                  background: confidence === 'high' ? '#D1FAE5' : '#FEF3C7',
                  color: confidence === 'high' ? '#065F46' : '#92400E',
                }}>
                  {confidence === 'high' ? 'Detectado' : 'Baixa confiança — por favor revise'}
                </span>
              )}
            </div>

            {detecting && (
              <div style={{ textAlign: 'center', padding: 32, color: 'var(--text-light)' }}>
                Analisando screenshot...
              </div>
            )}

            {detected && !detecting && (
              <>
                {/* Per-interpreter blocks */}
                {interpreters.map((interp, i) => renderInterpreterBlock(interp, i))}

                {isMulti && (
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={addInterpreter}
                    style={{ marginBottom: 16, fontSize: 13 }}
                  >
                    + Adicionar Intérprete
                  </button>
                )}

                {/* Shared fields */}
                <div className="form-row">
                  <div className="form-group">
                    <label style={!shared.work ? { color: '#DC2626', fontWeight: 700 } : {}}>
                      Obra * {!shared.work && '— preencha manualmente'}
                    </label>
                    <input
                      value={shared.work}
                      onChange={(e) => setSharedField('work', e.target.value)}
                      placeholder={!shared.work ? 'Nome da ária/peça não detectado — digite aqui' : ''}
                      style={!shared.work ? {
                        borderColor: '#DC2626',
                        borderWidth: 2,
                        background: '#FEF2F2',
                      } : {}}
                    />
                    {!shared.work && (
                      <span style={{ fontSize: 12, color: '#DC2626', marginTop: 4, display: 'block' }}>
                        O nome da música não foi encontrado no título/descrição do vídeo. Por favor, preencha manualmente.
                      </span>
                    )}
                  </div>
                  <div className="form-group">
                    <label>Compositor *</label>
                    <input value={shared.composer} onChange={(e) => setSharedField('composer', e.target.value)} />
                  </div>
                </div>
                <div className="form-row">
                  <div className="form-group">
                    <label>Ano de Composição</label>
                    <input value={shared.composition_year} onChange={(e) => setSharedField('composition_year', e.target.value)} />
                  </div>
                  <div className="form-group">
                    <label>Álbum / Ópera</label>
                    <input value={shared.album_opera} onChange={(e) => setSharedField('album_opera', e.target.value)} />
                  </div>
                </div>
              </>
            )}
          </div>
        )}

        {/* Submit */}
        <button
          type="submit"
          className="btn-primary"
          disabled={loading || !canSubmit || !detected}
          style={{ width: '100%', padding: 14, fontSize: 16, opacity: (canSubmit && detected) ? 1 : 0.5, marginTop: detected ? 0 : 24 }}
        >
          {loading ? 'Criando & Gerando Conteúdo...' : 'Criar Projeto e Gerar Conteúdo'}
        </button>
        {(!canSubmit || !detected) && !loading && (
          <p style={{ textAlign: 'center', fontSize: 13, color: 'var(--text-light)', marginTop: 8 }}>
            {!detected ? 'Faça o upload do screenshot e detecte os metadados primeiro' : 'Preencha todos os campos obrigatórios (*) para continuar'}
          </p>
        )}
      </form>
    </div>
  )
}
