import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'

const CATEGORIES = [
  '', 'Aria', 'Duet', 'Chorus', 'Overture', 'Recitative',
  'Ensemble', 'Ballet', 'Intermezzo', 'Other',
]

export default function NewProject() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [form, setForm] = useState({
    artist: '', work: '', composer: '', composition_year: '',
    nationality: '', nationality_flag: '', voice_type: '', birth_date: '', death_date: '',
    album_opera: '', category: '', hook: '', highlights: '',
    original_duration: '', cut_start: '', cut_end: '',
  })

  const set = (key: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
    setForm({ ...form, [key]: e.target.value })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.artist || !form.work || !form.composer) {
      setError('Artist, Work, and Composer are required.')
      return
    }
    setError('')
    setLoading(true)
    try {
      const project = await api.createProject(form)
      // Auto-generate content
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
        <div className="card" style={{ marginBottom: 16 }}>
          <h3 style={{ marginBottom: 16, fontSize: 16 }}>Artist & Work</h3>
          <div className="form-row">
            <div className="form-group">
              <label>Artist *</label>
              <input value={form.artist} onChange={set('artist')} placeholder="e.g. Maria Callas" />
            </div>
            <div className="form-group">
              <label>Work *</label>
              <input value={form.work} onChange={set('work')} placeholder="e.g. Casta Diva" />
            </div>
          </div>
          <div className="form-row">
            <div className="form-group">
              <label>Composer *</label>
              <input value={form.composer} onChange={set('composer')} placeholder="e.g. Bellini" />
            </div>
            <div className="form-group">
              <label>Composition Year</label>
              <input value={form.composition_year} onChange={set('composition_year')} placeholder="e.g. 1831" />
            </div>
          </div>
          <div className="form-row">
            <div className="form-group">
              <label>Nationality</label>
              <input value={form.nationality} onChange={set('nationality')} placeholder="e.g. Greek-American" />
            </div>
            <div className="form-group">
              <label>Flag Emoji</label>
              <input value={form.nationality_flag} onChange={set('nationality_flag')} placeholder="🇬🇷" style={{ fontSize: 20 }} />
            </div>
          </div>
          <div className="form-row">
            <div className="form-group">
              <label>Voice Type</label>
              <input value={form.voice_type} onChange={set('voice_type')} placeholder="e.g. Soprano" />
            </div>
          </div>
          <div className="form-row">
            <div className="form-group">
              <label>Birth Date</label>
              <input value={form.birth_date} onChange={set('birth_date')} placeholder="e.g. 1923" />
            </div>
            <div className="form-group">
              <label>Death Date</label>
              <input value={form.death_date} onChange={set('death_date')} placeholder="e.g. 1977" />
            </div>
          </div>
          <div className="form-row">
            <div className="form-group">
              <label>Album / Opera</label>
              <input value={form.album_opera} onChange={set('album_opera')} placeholder="e.g. Norma" />
            </div>
            <div className="form-group">
              <label>Category</label>
              <select value={form.category} onChange={set('category')}>
                {CATEGORIES.map((c) => (
                  <option key={c} value={c}>{c || '— Select —'}</option>
                ))}
              </select>
            </div>
          </div>
        </div>

        <div className="card" style={{ marginBottom: 16 }}>
          <h3 style={{ marginBottom: 16, fontSize: 16 }}>Creative Direction</h3>
          <div className="form-group">
            <label>Hook / Angle</label>
            <textarea value={form.hook} onChange={set('hook')} placeholder="What makes this performance special? What's the emotional hook?" />
          </div>
          <div className="form-group">
            <label>Highlights</label>
            <textarea value={form.highlights} onChange={set('highlights')} placeholder="Key moments, interesting facts, historical context..." />
          </div>
        </div>

        <div className="card" style={{ marginBottom: 24 }}>
          <h3 style={{ marginBottom: 16, fontSize: 16 }}>Video Timing</h3>
          <div className="form-row">
            <div className="form-group">
              <label>Original Duration</label>
              <input value={form.original_duration} onChange={set('original_duration')} placeholder="e.g. 04:30" />
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
              <div className="form-group">
                <label>Cut Start</label>
                <input value={form.cut_start} onChange={set('cut_start')} placeholder="e.g. 00:30" />
              </div>
              <div className="form-group">
                <label>Cut End</label>
                <input value={form.cut_end} onChange={set('cut_end')} placeholder="e.g. 01:30" />
              </div>
            </div>
          </div>
        </div>

        <button type="submit" className="btn-primary" disabled={loading} style={{ width: '100%', padding: 14, fontSize: 16 }}>
          {loading ? 'Creating & Generating Content...' : 'Create Project & Generate Content'}
        </button>
      </form>
    </div>
  )
}
