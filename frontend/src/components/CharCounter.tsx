export default function CharCounter({ value, max }: { value: string; max?: number }) {
  const len = value.length
  const color = max && len > max ? 'var(--danger)' : len > (max || 999) * 0.9 ? 'var(--warning)' : 'var(--text-light)'

  return (
    <span style={{ fontSize: 12, color, fontWeight: 500 }}>
      {len}{max ? ` / ${max}` : ''} chars
    </span>
  )
}
