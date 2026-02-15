"use client"

import { cn } from "@/lib/utils"

interface ScoreRingProps { score: number; size?: number; strokeWidth?: number; className?: string }

function getScoreColor(score: number) {
  if (score >= 80) return "hsl(152, 55%, 42%)"
  if (score >= 60) return "hsl(38, 80%, 50%)"
  if (score >= 40) return "hsl(215, 70%, 55%)"
  return "hsl(0, 60%, 50%)"
}

export function ScoreRing({ score, size = 48, strokeWidth = 3, className }: ScoreRingProps) {
  const radius = (size - strokeWidth) / 2
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (score / 100) * circumference
  const color = getScoreColor(score)
  return (
    <div className={cn("relative inline-flex items-center justify-center", className)}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="hsl(var(--border))" strokeWidth={strokeWidth} />
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke={color} strokeWidth={strokeWidth} strokeDasharray={circumference} strokeDashoffset={offset} strokeLinecap="round" className="transition-all duration-700 ease-out" />
      </svg>
      <span className="absolute text-[11px] font-semibold text-foreground tabular-nums">{score}</span>
    </div>
  )
}
