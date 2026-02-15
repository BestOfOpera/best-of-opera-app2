import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api, Project } from '../api'
import ProjectHeader from '../components/ProjectHeader'
import RegenerateButton from '../components/RegenerateButton'
import CharCounter from '../components/CharCounter'

export default function ApproveOverlay() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [project, setProject] = useState<Project | null>(null)
  const [overlay, setOverlay] = useState<{ timestamp: string; text: string }[]>([])
  const [loading, setLoading] = useState(true)
  const [regenerating, setRegenerating] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const projectId = Number(id)

  useEffect(() => {
    api.getProject(projectId).then((p) => {
      setProject(p)
      setOverlay(p.overlay_json || [])
    }).finally(() => setLoading(false))
  }, [projectId])

  const handleRegenerate = async (customPrompt?: string) => {
    setRegenerating(true)
    setError('')
    try {
      const p = await api.regenerateOverlay(projectId, customPrompt)
      setProject(p)
      setOverlay(p.overlay_json || [])
    } catch (err: any) {
      setError(err.message)
    } finally {
      setRegenerating(false)
    }
  }

  const updateEntry = (index: number, field: 'timestamp' | 'text', value: string) => {
    const updated = [...overlay]
    updated[index] = { ...updated[index], [field]: value }
    setOverlay(updated)
  }

  const removeEntry = (index: number) => {
    setOverlay(overlay.filter((_, i) => i !== index))
  }

  const addEntry = () => {
    setOverlay([...overlay, { timestamp: '00:00', text: '' }])
  }

  const handleApprove = async () => {
    setSaving(true)
    setError('')
    try {
      const p = await api.approveOverlay(projectId, overlay)
      setProject(p)
      navigate(`/project/${projectId}/approve-post`)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  if (loading || !project) return <div className="loading">Carregando...</div>

  return (
    <div>
      <ProjectHeader project={project} />
      <h3 style={{ marginBottom: 16 }}>Etapa 2 — Aprovar Legendas</h3>
      {error && <div className="error-msg">{error}</div>}

      <div style={{ marginBottom: 16 }}>
        <RegenerateButton onRegenerate={handleRegenerate} loading={regenerating} />
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        {overlay.map((entry, i) => (
          <div key={i} style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 12, paddingBottom: 12, borderBottom: i < overlay.length - 1 ? '1px solid var(--border)' : 'none' }}>
            <span style={{ color: 'var(--text-light)', fontSize: 13, minWidth: 24 }}>#{i + 1}</span>
            <input
              value={entry.timestamp}
              onChange={(e) => updateEntry(i, 'timestamp', e.target.value)}
              style={{ width: 80 }}
              placeholder="MM:SS"
            />
            <div style={{ flex: 1 }}>
              <input
                value={entry.text}
                onChange={(e) => updateEntry(i, 'text', e.target.value)}
                placeholder="Texto da legenda"
              />
              <CharCounter value={entry.text} max={70} />
            </div>
            <button className="btn-danger btn-small" onClick={() => removeEntry(i)} style={{ padding: '6px 10px' }}>
              X
            </button>
          </div>
        ))}
        <button className="btn-secondary btn-small" onClick={addEntry} style={{ marginTop: 8 }}>
          + Adicionar Legenda
        </button>
      </div>

      <div style={{ display: 'flex', gap: 12 }}>
        <button className="btn-success" onClick={handleApprove} disabled={saving || overlay.length === 0} style={{ flex: 1, padding: 14 }}>
          {saving ? 'Salvando...' : 'Aprovar e Continuar para o Post'}
        </button>
      </div>
    </div>
  )
}
