import type { Project } from '../api'

const STATUS_LABELS: Record<string, string> = {
  input_complete: 'Dados Completos',
  generating: 'Gerando...',
  awaiting_approval: 'Aguardando Aprovação',
  translating: 'Traduzindo...',
  export_ready: 'Pronto para Exportar',
}

export default function ProjectHeader({ project }: { project: Project }) {
  return (
    <div style={{ marginBottom: 24 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 4 }}>
        <h2 style={{ fontSize: 22 }}>{project.artist} — {project.work}</h2>
        <span className={`status-badge status-${project.status}`}>
          {STATUS_LABELS[project.status] || project.status}
        </span>
      </div>
      <p style={{ color: 'var(--text-light)', fontSize: 14 }}>
        {project.composer} {project.composition_year ? `(${project.composition_year})` : ''}
        {project.voice_type ? ` · ${project.voice_type}` : ''}
        {project.category ? ` · ${project.category}` : ''}
      </p>
    </div>
  )
}
