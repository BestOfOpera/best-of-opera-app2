import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { api, Project, ExportData } from '../api'
import ProjectHeader from '../components/ProjectHeader'
import CopyButton from '../components/CopyButton'

const LANGUAGES = [
  { code: 'pt', label: 'Português' },
  { code: 'en', label: 'Inglês' },
  { code: 'es', label: 'Espanhol' },
  { code: 'de', label: 'Alemão' },
  { code: 'fr', label: 'Francês' },
  { code: 'it', label: 'Italiano' },
  { code: 'pl', label: 'Polonês' },
]

export default function Export() {
  const { id } = useParams<{ id: string }>()
  const [project, setProject] = useState<Project | null>(null)
  const [activeLang, setActiveLang] = useState('pt')
  const [exportData, setExportData] = useState<ExportData | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadingLang, setLoadingLang] = useState(false)
  const [translating, setTranslating] = useState(false)
  const [retranslating, setRetranslating] = useState(false)
  const [error, setError] = useState('')
  const [editingPost, setEditingPost] = useState(false)
  const [editPostText, setEditPostText] = useState('')
  const [editingYt, setEditingYt] = useState(false)
  const [editYtTitle, setEditYtTitle] = useState('')
  const [editYtTags, setEditYtTags] = useState('')
  const [editingOverlay, setEditingOverlay] = useState(false)
  const [editOverlay, setEditOverlay] = useState<{ timestamp: string; text: string }[]>([])
  const [saving, setSaving] = useState(false)
  const [hasExportPath, setHasExportPath] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [exportSuccess, setExportSuccess] = useState('')

  const projectId = Number(id)

  useEffect(() => {
    api.getProject(projectId).then(setProject).finally(() => setLoading(false))
    api.getExportConfig().then(c => setHasExportPath(!!c.export_path)).catch(() => {})
  }, [projectId])

  const loadLang = (lang: string) => {
    setLoadingLang(true)
    setEditingPost(false)
    setEditingYt(false)
    setEditingOverlay(false)
    api.exportLang(projectId, lang)
      .then(setExportData)
      .catch(() => setExportData(null))
      .finally(() => setLoadingLang(false))
  }

  useEffect(() => { loadLang(activeLang) }, [projectId, activeLang])

  const handleTranslate = async () => {
    setTranslating(true)
    setError('')
    try {
      const p = await api.translate(projectId)
      setProject(p)
      loadLang(activeLang)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setTranslating(false)
    }
  }

  const handleRetranslate = async () => {
    setRetranslating(true)
    setError('')
    try {
      const data = await api.retranslate(projectId, activeLang)
      setExportData({ ...data, srt: exportData?.srt || '' })
      // Reload to get fresh SRT
      loadLang(activeLang)
    } catch (err: any) {
      setError('Erro ao retraduzir: ' + err.message)
    } finally {
      setRetranslating(false)
    }
  }

  const handleSavePost = async () => {
    setSaving(true)
    try {
      await api.updateTranslation(projectId, activeLang, { post_text: editPostText })
      loadLang(activeLang)
      setEditingPost(false)
    } catch (err: any) {
      setError('Erro ao salvar: ' + err.message)
    } finally {
      setSaving(false)
    }
  }

  const handleSaveYt = async () => {
    setSaving(true)
    try {
      await api.updateTranslation(projectId, activeLang, {
        youtube_title: editYtTitle,
        youtube_tags: editYtTags,
      })
      loadLang(activeLang)
      setEditingYt(false)
    } catch (err: any) {
      setError('Erro ao salvar: ' + err.message)
    } finally {
      setSaving(false)
    }
  }

  const handleSaveOverlay = async () => {
    setSaving(true)
    try {
      await api.updateTranslation(projectId, activeLang, { overlay_json: editOverlay })
      loadLang(activeLang)
      setEditingOverlay(false)
    } catch (err: any) {
      setError('Erro ao salvar: ' + err.message)
    } finally {
      setSaving(false)
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

      <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap', alignItems: 'center' }}>
        {!hasTranslations && (
          <button className="btn-primary" onClick={handleTranslate} disabled={translating}>
            {translating ? 'Traduzindo...' : 'Traduzir para 7 idiomas'}
          </button>
        )}
        {hasTranslations && (
          <button className="btn-secondary btn-small" onClick={handleTranslate} disabled={translating}>
            {translating ? 'Retraduzindo tudo...' : 'Retraduzir todos os idiomas'}
          </button>
        )}
        <a href={api.exportZipUrl(projectId)} download>
          <button className="btn-primary">Baixar ZIP</button>
        </a>
        {hasExportPath && (
          <button
            className="btn-primary"
            disabled={exporting}
            onClick={async () => {
              setExporting(true)
              setExportSuccess('')
              setError('')
              try {
                const res = await api.exportToFolder(projectId)
                setExportSuccess(`Exportado para: ${res.path}`)
              } catch (err: any) {
                setError('Erro ao exportar: ' + err.message)
              } finally {
                setExporting(false)
              }
            }}
          >
            {exporting ? 'Exportando...' : 'Exportar para Pasta'}
          </button>
        )}
      </div>
      {exportSuccess && (
        <div style={{ marginBottom: 16, padding: '8px 12px', background: '#D1FAE5', color: '#065F46', borderRadius: 8, fontSize: 13 }}>
          {exportSuccess}
        </div>
      )}

      {/* Language tabs */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 16, flexWrap: 'wrap' }}>
        {LANGUAGES.map((lang) => {
          const available = hasTranslations
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

      {/* Retranslate single language button */}
      {hasTranslations && (
        <div style={{ marginBottom: 16 }}>
          <button
            className="btn-secondary btn-small"
            onClick={handleRetranslate}
            disabled={retranslating}
          >
            {retranslating ? 'Retraduzindo...' : `Retraduzir ${LANGUAGES.find(l => l.code === activeLang)?.label || activeLang}`}
          </button>
        </div>
      )}

      {loadingLang ? (
        <div className="loading">Carregando...</div>
      ) : exportData ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* Post */}
          <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <h4 style={{ fontSize: 14 }}>Texto do Post</h4>
              <div style={{ display: 'flex', gap: 8 }}>
                {!editingPost && (
                  <button
                    className="btn-secondary btn-small"
                    onClick={() => { setEditingPost(true); setEditPostText(exportData.post_text || '') }}
                    style={{ fontSize: 12 }}
                  >
                    Editar
                  </button>
                )}
                <CopyButton text={exportData.post_text || ''} />
              </div>
            </div>
            {editingPost ? (
              <div>
                <textarea
                  value={editPostText}
                  onChange={(e) => setEditPostText(e.target.value)}
                  style={{ width: '100%', minHeight: 200, fontSize: 14, lineHeight: 1.7, padding: 16, borderRadius: 8, border: '2px solid var(--purple)' }}
                />
                <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                  <button className="btn-primary btn-small" onClick={handleSavePost} disabled={saving}>
                    {saving ? 'Salvando...' : 'Salvar'}
                  </button>
                  <button className="btn-secondary btn-small" onClick={() => setEditingPost(false)}>Cancelar</button>
                </div>
              </div>
            ) : (
              <div style={{ whiteSpace: 'pre-wrap', fontSize: 14, lineHeight: 1.7, background: '#FAFAFA', padding: 16, borderRadius: 8 }}>
                {exportData.post_text || '—'}
              </div>
            )}
          </div>

          {/* YouTube */}
          <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <h4 style={{ fontSize: 14 }}>YouTube</h4>
              <div style={{ display: 'flex', gap: 8 }}>
                {!editingYt && (
                  <button
                    className="btn-secondary btn-small"
                    onClick={() => { setEditingYt(true); setEditYtTitle(exportData.youtube_title || ''); setEditYtTags(exportData.youtube_tags || '') }}
                    style={{ fontSize: 12 }}
                  >
                    Editar
                  </button>
                )}
                <CopyButton text={`${exportData.youtube_title}\n\n${exportData.youtube_tags}`} />
              </div>
            </div>
            {editingYt ? (
              <div style={{ fontSize: 14 }}>
                <div style={{ marginBottom: 8 }}>
                  <label style={{ fontSize: 12, color: '#6B7280' }}>Título:</label>
                  <input
                    value={editYtTitle}
                    onChange={(e) => setEditYtTitle(e.target.value)}
                    style={{ width: '100%', padding: 8, borderRadius: 8, border: '2px solid var(--purple)', fontSize: 14 }}
                  />
                </div>
                <div style={{ marginBottom: 8 }}>
                  <label style={{ fontSize: 12, color: '#6B7280' }}>Tags:</label>
                  <input
                    value={editYtTags}
                    onChange={(e) => setEditYtTags(e.target.value)}
                    style={{ width: '100%', padding: 8, borderRadius: 8, border: '2px solid var(--purple)', fontSize: 14 }}
                  />
                </div>
                <div style={{ display: 'flex', gap: 8 }}>
                  <button className="btn-primary btn-small" onClick={handleSaveYt} disabled={saving}>
                    {saving ? 'Salvando...' : 'Salvar'}
                  </button>
                  <button className="btn-secondary btn-small" onClick={() => setEditingYt(false)}>Cancelar</button>
                </div>
              </div>
            ) : (
              <div style={{ fontSize: 14 }}>
                <p><strong>Título:</strong> {exportData.youtube_title || '—'}</p>
                <p style={{ marginTop: 8 }}><strong>Tags:</strong> {exportData.youtube_tags || '—'}</p>
              </div>
            )}
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
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                <h4 style={{ fontSize: 14 }}>Legendas Overlay</h4>
                {!editingOverlay && (
                  <button
                    className="btn-secondary btn-small"
                    onClick={() => { setEditingOverlay(true); setEditOverlay([...exportData.overlay_json!]) }}
                    style={{ fontSize: 12 }}
                  >
                    Editar
                  </button>
                )}
              </div>
              {editingOverlay ? (
                <div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    {editOverlay.map((entry, i) => (
                      <div key={i} style={{ display: 'flex', gap: 12, fontSize: 14, alignItems: 'center' }}>
                        <span style={{ color: 'var(--purple)', fontWeight: 600, minWidth: 50 }}>{entry.timestamp}</span>
                        <input
                          value={entry.text}
                          onChange={(e) => {
                            const updated = [...editOverlay]
                            updated[i] = { ...updated[i], text: e.target.value }
                            setEditOverlay(updated)
                          }}
                          style={{ flex: 1, padding: 6, borderRadius: 6, border: '2px solid var(--purple)', fontSize: 14 }}
                        />
                      </div>
                    ))}
                  </div>
                  <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                    <button className="btn-primary btn-small" onClick={handleSaveOverlay} disabled={saving}>
                      {saving ? 'Salvando...' : 'Salvar'}
                    </button>
                    <button className="btn-secondary btn-small" onClick={() => setEditingOverlay(false)}>Cancelar</button>
                  </div>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {exportData.overlay_json.map((entry, i) => (
                    <div key={i} style={{ display: 'flex', gap: 12, fontSize: 14 }}>
                      <span style={{ color: 'var(--purple)', fontWeight: 600, minWidth: 50 }}>{entry.timestamp}</span>
                      <span>{entry.text}</span>
                    </div>
                  ))}
                </div>
              )}
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
