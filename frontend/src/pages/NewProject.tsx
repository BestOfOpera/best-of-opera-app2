import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, DetectedMetadata } from '../api'

const CATEGORIES = [
  '', 'Aria', 'Duet', 'Chorus', 'Overture', 'Recitative',
  'Ensemble', 'Ballet', 'Intermezzo', 'Other',
]

export default function NewProject() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  // Step A — human input
  const [youtubeUrl, setYoutubeUrl] = useState('')
  const [hook, setHook] = useState('')
  const [category, setCategory] = useState('')
  const [cutStart, setCutStart] = useState('')
  const [cutEnd, setCutEnd] = useState('')

  // Detection state
  const [detecting, setDetecting] = useState(false)
  const [detected, setDetected] = useState(false)
  const [confidence, setConfidence] = useState('')
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Step B — auto-detected fields (editable)
  const [meta, setMeta] = useState({
    artist: '', work: '', composer: '', composition_year: '',
    nationality: '', nationality_flag: '', voice_type: '',
    birth_date: '', death_date: '', album_opera: '',
  })

  const setField = (key: string, value: string) =>
    setMeta(prev => ({ ...prev, [key]: value }))

  // Auto-detect when YouTube URL changes
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current)

    if (youtubeUrl.length < 15) {
      setDetected(false)
      return
    }

    debounceRef.current = setTimeout(async () => {
      setDetecting(true)
      setError('')
      try {
        const result: DetectedMetadata = await api.detectMetadata(youtubeUrl)
        setMeta({
          artist: result.artist || '',
          work: result.work || '',
          composer: result.composer || '',
          composition_year: result.composition_year || '',
          nationality: result.nationality || '',
          nationality_flag: result.nationality_flag || '',
          voice_type: result.voice_type || '',
          birth_date: result.birth_date || '',
          death_date: result.death_date || '',
          album_opera: result.album_opera || '',
        })
        setConfidence(result.confidence || 'high')
        setDetected(true)
      } catch (err: any) {
        setError('Auto-detection failed. Please fill in the fields manually.')
        setDetected(true)
        setConfidence('low')
      } finally {
        setDetecting(false)
      }
    }, 1500)

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
  }, [youtubeUrl])

  const stepAComplete = youtubeUrl.length > 10 && hook.trim() && category && cutStart && cutEnd
  const canSubmit = stepAComplete && detected && meta.artist && meta.work && meta.composer

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!canSubmit) return
    setError('')
    setLoading(true)
    try {
      const project = await api.createProject({
        youtube_url: youtubeUrl,
        hook,
        category,
        cut_start: cutStart,
        cut_end: cutEnd,
        ...meta,
      })
      await api.generate(project.id)
      navigate(`/project/${project.id}/approve-overlay`)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h2 style={{ marginBottom: 24 }}>New Project</h2>
      {error && <div className="error-msg">{error}</div>}
      <form onSubmit={handleSubmit}>
        {/* STEP A — Human input */}
        <div className="card" style={{ marginBottom: 16 }}>
          <h3 style={{ marginBottom: 16, fontSize: 16 }}>Step A — Your Input</h3>

          <div className="form-group">
            <label>YouTube Link *</label>
            <input
              value={youtubeUrl}
              onChange={(e) => setYoutubeUrl(e.target.value)}
              placeholder="https://www.youtube.com/watch?v=..."
            />
            {detecting && (
              <span style={{ fontSize: 13, color: 'var(--purple)', marginTop: 4, display: 'block' }}>
                Detecting metadata from video...
              </span>
            )}
          </div>

          <div className="form-group">
            <label>Hook / Creative Angle *</label>
            <textarea
              value={hook}
              onChange={(e) => setHook(e.target.value)}
              placeholder="What makes this performance special? The emotional angle for the post..."
              style={{ minHeight: 80 }}
            />
          </div>

          <div className="form-row">
            <div className="form-group">
              <label>Category *</label>
              <select value={category} onChange={(e) => setCategory(e.target.value)}>
                {CATEGORIES.map((c) => (
                  <option key={c} value={c}>{c || '— Select —'}</option>
                ))}
              </select>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
              <div className="form-group">
                <label>Cut Start *</label>
                <input value={cutStart} onChange={(e) => setCutStart(e.target.value)} placeholder="1:15" />
              </div>
              <div className="form-group">
                <label>Cut End *</label>
                <input value={cutEnd} onChange={(e) => setCutEnd(e.target.value)} placeholder="2:45" />
              </div>
            </div>
          </div>
        </div>

        {/* STEP B — Auto-detected fields */}
        {(detected || detecting) && (
          <div className="card" style={{ marginBottom: 24, opacity: detecting ? 0.6 : 1, transition: 'opacity 0.3s' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <h3 style={{ fontSize: 16 }}>Step B — Detected Metadata</h3>
              {detected && !detecting && (
                <span style={{
                  fontSize: 13,
                  padding: '4px 10px',
                  borderRadius: 12,
                  background: confidence === 'high' ? '#D1FAE5' : '#FEF3C7',
                  color: confidence === 'high' ? '#065F46' : '#92400E',
                }}>
                  {confidence === 'high' ? 'Detected' : 'Low confidence — please review'}
                </span>
              )}
            </div>

            {detecting && (
              <div style={{ textAlign: 'center', padding: 32, color: 'var(--text-light)' }}>
                Analyzing video metadata...
              </div>
            )}

            {detected && !detecting && (
              <>
                <div className="form-row">
                  <div className="form-group">
                    <label>Artist *</label>
                    <input value={meta.artist} onChange={(e) => setField('artist', e.target.value)} />
                  </div>
                  <div className="form-group">
                    <label>Work *</label>
                    <input value={meta.work} onChange={(e) => setField('work', e.target.value)} />
                  </div>
                </div>
                <div className="form-row">
                  <div className="form-group">
                    <label>Composer *</label>
                    <input value={meta.composer} onChange={(e) => setField('composer', e.target.value)} />
                  </div>
                  <div className="form-group">
                    <label>Composition Year</label>
                    <input value={meta.composition_year} onChange={(e) => setField('composition_year', e.target.value)} />
                  </div>
                </div>
                <div className="form-row">
                  <div className="form-group">
                    <label>Nationality</label>
                    <input value={meta.nationality} onChange={(e) => setField('nationality', e.target.value)} />
                  </div>
                  <div className="form-group">
                    <label>Flag Emoji</label>
                    <input value={meta.nationality_flag} onChange={(e) => setField('nationality_flag', e.target.value)} style={{ fontSize: 20 }} />
                  </div>
                </div>
                <div className="form-row">
                  <div className="form-group">
                    <label>Voice Type / Instrument</label>
                    <input value={meta.voice_type} onChange={(e) => setField('voice_type', e.target.value)} />
                  </div>
                  <div className="form-group">
                    <label>Album / Opera</label>
                    <input value={meta.album_opera} onChange={(e) => setField('album_opera', e.target.value)} />
                  </div>
                </div>
                <div className="form-row">
                  <div className="form-group">
                    <label>Date of Birth</label>
                    <input value={meta.birth_date} onChange={(e) => setField('birth_date', e.target.value)} placeholder="dd/mm/yyyy" />
                  </div>
                  <div className="form-group">
                    <label>Date of Death</label>
                    <input value={meta.death_date} onChange={(e) => setField('death_date', e.target.value)} placeholder="Empty if alive" />
                  </div>
                </div>
              </>
            )}
          </div>
        )}

        {/* Submit */}
        {canSubmit && (
          <button
            type="submit"
            className="btn-primary"
            disabled={loading}
            style={{ width: '100%', padding: 14, fontSize: 16 }}
          >
            {loading ? 'Creating & Generating Content...' : 'Create Project & Generate Content'}
          </button>
        )}
      </form>
    </div>
  )
}
