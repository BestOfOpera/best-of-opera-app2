import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api, Project } from '../api'
import ProjectHeader from '../components/ProjectHeader'
import RegenerateButton from '../components/RegenerateButton'
import CharCounter from '../components/CharCounter'
import CopyButton from '../components/CopyButton'

export default function ApproveYoutube() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [project, setProject] = useState<Project | null>(null)
  const [title, setTitle] = useState('')
  const [tags, setTags] = useState('')
  const [loading, setLoading] = useState(true)
  const [regenerating, setRegenerating] = useState(false)
  const [saving, setSaving] = useState(false)
  const [translating, setTranslating] = useState(false)
  const [error, setError] = useState('')

  const projectId = Number(id)

  useEffect(() => {
    api.getProject(projectId).then((p) => {
      setProject(p)
      setTitle(p.youtube_title || '')
      setTags(p.youtube_tags || '')
    }).finally(() => setLoading(false))
  }, [projectId])

  const handleRegenerate = async (customPrompt?: string) => {
    setRegenerating(true)
    setError('')
    try {
      const p = await api.regenerateYoutube(projectId, customPrompt)
      setProject(p)
      setTitle(p.youtube_title || '')
      setTags(p.youtube_tags || '')
    } catch (err: any) {
      setError(err.message)
    } finally {
      setRegenerating(false)
    }
  }

  const handleApprove = async () => {
    setSaving(true)
    setError('')
    try {
      let p = await api.approveYoutube(projectId, title, tags)
      setProject(p)

      // If overlay and post are already approved, trigger translation
      if (p.overlay_approved && p.post_approved) {
        setTranslating(true)
        try {
          p = await api.translate(projectId)
          setProject(p)
        } catch (err: any) {
          // Translation failure is non-blocking, user can retry from export
          console.warn('Translation failed:', err.message)
        } finally {
          setTranslating(false)
        }
      }

      navigate(`/project/${projectId}/export`)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  if (loading || !project) return <div className="loading">Loading...</div>

  return (
    <div>
      <ProjectHeader project={project} />
      <h3 style={{ marginBottom: 16 }}>Step 4 — Approve YouTube Title & Tags</h3>
      {error && <div className="error-msg">{error}</div>}

      <div style={{ marginBottom: 16 }}>
        <RegenerateButton onRegenerate={handleRegenerate} loading={regenerating} />
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <div className="form-group">
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
            <label>YouTube Title</label>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <CharCounter value={title} max={100} />
              <CopyButton text={title} />
            </div>
          </div>
          <input value={title} onChange={(e) => setTitle(e.target.value)} />
        </div>

        <div className="form-group">
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
            <label>Tags (comma-separated)</label>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <CharCounter value={tags} max={450} />
              <CopyButton text={tags} />
            </div>
          </div>
          <textarea
            value={tags}
            onChange={(e) => setTags(e.target.value)}
            style={{ minHeight: 100 }}
          />
        </div>
      </div>

      <button
        className="btn-success"
        onClick={handleApprove}
        disabled={saving || translating || !title.trim()}
        style={{ width: '100%', padding: 14 }}
      >
        {translating ? 'Translating to 6 languages...' : saving ? 'Saving...' : 'Approve & Translate'}
      </button>
    </div>
  )
}
