import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api, Project } from '../api'
import ProjectHeader from '../components/ProjectHeader'
import RegenerateButton from '../components/RegenerateButton'
import CharCounter from '../components/CharCounter'
import CopyButton from '../components/CopyButton'

export default function ApprovePost() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [project, setProject] = useState<Project | null>(null)
  const [postText, setPostText] = useState('')
  const [loading, setLoading] = useState(true)
  const [regenerating, setRegenerating] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const projectId = Number(id)

  useEffect(() => {
    api.getProject(projectId).then((p) => {
      setProject(p)
      setPostText(p.post_text || '')
    }).finally(() => setLoading(false))
  }, [projectId])

  const handleRegenerate = async (customPrompt?: string) => {
    setRegenerating(true)
    setError('')
    try {
      const p = await api.regeneratePost(projectId, customPrompt)
      setProject(p)
      setPostText(p.post_text || '')
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
      const p = await api.approvePost(projectId, postText)
      setProject(p)
      navigate(`/project/${projectId}/approve-youtube`)
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
      <h3 style={{ marginBottom: 16 }}>Step 3 — Approve Post Text</h3>
      {error && <div className="error-msg">{error}</div>}

      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <RegenerateButton onRegenerate={handleRegenerate} loading={regenerating} />
        <CopyButton text={postText} />
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
          <label style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-light)' }}>Post Text</label>
          <CharCounter value={postText} max={2200} />
        </div>
        <textarea
          value={postText}
          onChange={(e) => setPostText(e.target.value)}
          style={{ minHeight: 400, fontFamily: 'var(--font-body)', lineHeight: 1.7 }}
        />
      </div>

      {/* Preview */}
      <div className="card" style={{ marginBottom: 16, background: '#FAFAFA' }}>
        <h4 style={{ fontSize: 14, color: 'var(--text-light)', marginBottom: 12 }}>Preview</h4>
        <div style={{ whiteSpace: 'pre-wrap', fontSize: 14, lineHeight: 1.7 }}>
          {postText}
        </div>
      </div>

      <button className="btn-success" onClick={handleApprove} disabled={saving || !postText.trim()} style={{ width: '100%', padding: 14 }}>
        {saving ? 'Saving...' : 'Approve & Continue to YouTube'}
      </button>
    </div>
  )
}
