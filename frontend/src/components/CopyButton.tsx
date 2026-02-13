import { useState } from 'react'

export default function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    await navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <button className="btn-secondary btn-small" onClick={handleCopy}>
      {copied ? 'Copied!' : 'Copy'}
    </button>
  )
}
