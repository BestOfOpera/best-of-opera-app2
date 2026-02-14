import { useState } from 'react'

interface Props {
  onRegenerate: (customPrompt?: string) => Promise<void>
  loading: boolean
}

export default function RegenerateButton({ onRegenerate, loading }: Props) {
  const [showPrompt, setShowPrompt] = useState(false)
  const [customPrompt, setCustomPrompt] = useState('')

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      <div style={{ display: 'flex', gap: 8 }}>
        <button
          className="btn-secondary btn-small"
          disabled={loading}
          onClick={() => onRegenerate()}
        >
          {loading ? 'Regenerando...' : 'Regenerar'}
        </button>
        <button
          className="btn-secondary btn-small"
          onClick={() => setShowPrompt(!showPrompt)}
          style={{ fontSize: 12 }}
        >
          {showPrompt ? 'Ocultar prompt' : 'Prompt personalizado'}
        </button>
      </div>
      {showPrompt && (
        <div style={{ display: 'flex', gap: 8 }}>
          <textarea
            value={customPrompt}
            onChange={(e) => setCustomPrompt(e.target.value)}
            placeholder="Adicione instruções personalizadas..."
            style={{ minHeight: 60, flex: 1 }}
          />
          <button
            className="btn-primary btn-small"
            disabled={loading || !customPrompt.trim()}
            onClick={() => onRegenerate(customPrompt)}
            style={{ alignSelf: 'flex-end' }}
          >
            Enviar
          </button>
        </div>
      )}
    </div>
  )
}
