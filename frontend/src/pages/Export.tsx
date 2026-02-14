import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { api, Project, ExportData } from '../api'
import ProjectHeader from '../components/ProjectHeader'
import CopyButton from '../components/CopyButton'

const LANGUAGES = [
  { code: 'en', label: 'Original' },
  { code: 'pt', label: 'Português' },
  { code: 'es', label: 'Espanhol' },
  { code: 'de', label: 'Alemão' },
  { code: 'fr', label: 'Francês' },
  { code: 'it', label: 'Italiano' },
  { code: 'pl', label: 'Polonês' },
]

export default function Export() {
  const { id } = useParams<{ id: string }>()
  const [project, setProject] = useState<Project | null>(null)
  const [activeLang, setActiveLang] = useState('en')
  const [exportData, setExportData] = useState<ExportData | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadingLang, setLoadingLang] = useState(false)
  const [translating, setTranslating] = useState(false)
  const [error, setError] = useState('')

  const projectId = Number(id)

  useEffect(() => {
    api.getProject(projectId).then(setProject).finally(() => setLoading(false))
  }, [projectId])

  useEffect(() => {
    setLoadingLang(true)
    api.exportLang(projectId, activeLang)
      .then(setExportData)
      .catch(() => setExportData(null))
      .finally(() => setLoadingLang(false))
  }, [projectId, activeLang])

  const handleTranslate = async () => {
    setTranslating(true)
    setError('')
    try {
      const p = await api.translate(projectId)
      setProject(p)
      // Reload current lang
      const data = await api.exportLang(projectId, activeLang)
      setExportData(data)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setTranslating(false)
    }
  }

  const downloadSrt = () => {
    if (!exportData?.srt) return
    const blob = new Blob([exportData.srt], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `subtitles_${activeLang}.srt`
    a.click()
    URL.revokeObjectURL(url)
  }

  if (loading || !project) return <div className="loading">Carregando...</div>

  const hasTranslations = project.translations.length > 0

  return (
    <div>
      <ProjectHeader project={project} />
      <h3 style={{ marginBottom: 16 }}>Etapa 6 — Exportar</h3>
      {error && <div className="error-msg">{error}</div>}

      <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
        {!hasTranslations && (
          <button className="btn-primary" onClick={handleTranslate} disabled={translating}>
            {translating ? 'Traduzindo...' : 'Traduzir para 6 idiomas'}
          </button>
        )}
        <a href={api.exportZipUrl(projectId)} download>
          <button className="btn-primary">Baixar ZIP</button>
        </a>
      </div>

      {/* Language tabs */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 16, flexWrap: 'wrap' }}>
        {LANGUAGES.map((lang) => {
          const available = lang.code === 'en' || hasTranslations
          return (
            <button
              key={lang.code}
              onClick={() => available && setActiveLang(lang.code)}
              style={{
                padding: '8px 16px',
                borderRadius: 8,
                background: activeLang === lang.code ? 'var(--purple)' : available ? 'var(--purple-bg)' : '#F3F4F6',
                color: activeLang === lang.code ? 'white' : available ? 'var(--purple)' : '#9CA3AF',
                fontSize: 13,
                fontWeight: 500,
                cursor: available ? 'pointer' : 'default',
              }}
            >
              {lang.label}
            </button>
          )
        })}
      </div>

      {loadingLang ? (
        <div className="loading">Carregando {activeLang}...</div>
      ) : exportData ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* Post */}
          <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
              <h4 style={{ fontSize: 14 }}>Texto do Post</h4>
              <CopyButton text={exportData.post_text || ''} />
            </div>
            <div style={{ whiteSpace: 'pre-wrap', fontSize: 14, lineHeight: 1.7, background: '#FAFAFA', padding: 16, borderRadius: 8 }}>
              {exportData.post_text || '—'}
            </div>
          </div>

          {/* YouTube */}
          <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
              <h4 style={{ fontSize: 14 }}>YouTube</h4>
              <CopyButton text={`${exportData.youtube_title}\n\n${exportData.youtube_tags}`} />
            </div>
            <div style={{ fontSize: 14 }}>
              <p><strong>Título:</strong> {exportData.youtube_title || '—'}</p>
              <p style={{ marginTop: 8 }}><strong>Tags:</strong> {exportData.youtube_tags || '—'}</p>
            </div>
          </div>

          {/* SRT */}
          <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
              <h4 style={{ fontSize: 14 }}>Legendas (SRT)</h4>
              <div style={{ display: 'flex', gap: 8 }}>
                <CopyButton text={exportData.srt || ''} />
                <button className="btn-secondary btn-small" onClick={downloadSrt}>Baixar .srt</button>
              </div>
            </div>
            <pre style={{ fontSize: 13, background: '#FAFAFA', padding: 16, borderRadius: 8, overflow: 'auto', maxHeight: 300 }}>
              {exportData.srt || '—'}
            </pre>
          </div>

          {/* Overlay JSON */}
          {exportData.overlay_json && (
            <div className="card">
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                <h4 style={{ fontSize: 14 }}>Legendas Overlay</h4>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {exportData.overlay_json.map((entry, i) => (
                  <div key={i} style={{ display: 'flex', gap: 12, fontSize: 14 }}>
                    <span style={{ color: 'var(--purple)', fontWeight: 600, minWidth: 50 }}>{entry.timestamp}</span>
                    <span>{entry.text}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="card" style={{ textAlign: 'center', padding: 32, color: 'var(--text-light)' }}>
          Nenhum dado disponível para este idioma. Execute as traduções primeiro.
        </div>
      )}
    </div>
  )
}
