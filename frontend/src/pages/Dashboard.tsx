import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, Project } from '../api'

const STATUS_LABELS: Record<string, string> = {
  input_complete: 'Dados Completos',
  generating: 'Gerando...',
  awaiting_approval: 'Aguardando Aprovação',
  translating: 'Traduzindo...',
  export_ready: 'Pronto para Exportar',
}

function nextStepLink(p: Project): string {
  if (p.status === 'input_complete' || p.status === 'generating') return `/project/${p.id}/approve-overlay`
  if (!p.overlay_approved) return `/project/${p.id}/approve-overlay`
  if (!p.post_approved) return `/project/${p.id}/approve-post`
  if (!p.youtube_approved) return `/project/${p.id}/approve-youtube`
  return `/project/${p.id}/export`
}

export default function Dashboard() {
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.listProjects().then(setProjects).finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="loading">Carregando projetos...</div>

  return (
    <div>
      <h2 style={{ marginBottom: 24 }}>Projetos</h2>
      {projects.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: 48 }}>
          <p style={{ color: 'var(--text-light)', marginBottom: 16 }}>Nenhum projeto ainda.</p>
          <Link to="/new-project">
            <button className="btn-primary">Crie seu primeiro projeto</button>
          </Link>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {projects.map((p) => (
            <Link key={p.id} to={nextStepLink(p)} style={{ textDecoration: 'none', color: 'inherit' }}>
              <div className="card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer' }}>
                <div>
                  <h3 style={{ fontSize: 18, marginBottom: 4 }}>{p.artist} — {p.work}</h3>
                  <p style={{ color: 'var(--text-light)', fontSize: 13 }}>
                    {p.composer} {p.category ? `· ${p.category}` : ''}
                  </p>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <div style={{ textAlign: 'right', fontSize: 12, color: 'var(--text-light)' }}>
                    {p.overlay_approved && <div style={{ color: 'var(--success)' }}>Legendas OK</div>}
                    {p.post_approved && <div style={{ color: 'var(--success)' }}>Post OK</div>}
                    {p.youtube_approved && <div style={{ color: 'var(--success)' }}>YouTube OK</div>}
                  </div>
                  <span className={`status-badge status-${p.status}`}>
                    {STATUS_LABELS[p.status] || p.status}
                  </span>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
