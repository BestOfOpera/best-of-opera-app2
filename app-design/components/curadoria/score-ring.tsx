"use client"

function scoreColor(score: number) {
  if (score >= 80) return "#3B8C5C"
  if (score >= 60) return "#C9A84C"
  if (score >= 40) return "#D4833B"
  return "#D4483B"
}

export function ScoreRing({ score, size = 38 }: { score: number; size?: number }) {
  const r = (size - 6) / 2
  const circ = 2 * Math.PI * r
  const offset = circ - (score / 100) * circ
  const color = scoreColor(score)

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      <circle
        cx={size / 2}
        cy={size / 2}
        r={r}
        fill="white"
        stroke="#E8E0D4"
        strokeWidth={3}
      />
      <circle
        cx={size / 2}
        cy={size / 2}
        r={r}
        fill="none"
        stroke={color}
        strokeWidth={3}
        strokeDasharray={circ}
        strokeDashoffset={offset}
        strokeLinecap="round"
        transform={`rotate(-90 ${size / 2} ${size / 2})`}
      />
      <text
        x={size / 2}
        y={size / 2}
        textAnchor="middle"
        dominantBaseline="central"
        fontSize={size * 0.3}
        fontWeight={700}
        fill={color}
      >
        {score}
      </text>
    </svg>
  )
}

export function scoreColorBg(score: number) {
  if (score >= 80) return { color: "#3B8C5C", bg: "#E8F5E9" }
  if (score >= 60) return { color: "#C9A84C", bg: "#FFF8E1" }
  if (score >= 40) return { color: "#D4833B", bg: "#FFF3E0" }
  return { color: "#D4483B", bg: "#FFEBEE" }
}
