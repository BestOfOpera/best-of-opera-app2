"use client"

import type { Video } from "@/lib/api/curadoria"
import { ScoreRing } from "./score-ring"
import { Badge } from "@/components/ui/badge"

function formatViews(n: number) {
  if (n >= 1e6) return (n / 1e6).toFixed(1) + "M"
  if (n >= 1e3) return Math.round(n / 1e3) + "K"
  return String(n)
}

function formatDuration(s: number) {
  if (!s) return "--"
  const m = Math.floor(s / 60)
  const sec = Math.floor(s % 60)
  return `${m}:${String(sec).padStart(2, "0")}`
}

const TAG_COLORS: Record<string, string> = {
  elite_hit: "bg-green-100 text-green-700",
  power_name: "bg-purple-100 text-purple-700",
  specialty: "bg-blue-100 text-blue-700",
  voice: "bg-cyan-100 text-cyan-700",
  institutional: "bg-amber-100 text-amber-700",
  quality: "bg-teal-100 text-teal-700",
  views: "bg-orange-100 text-orange-700",
}

export function VideoCard({ video, onClick }: { video: Video; onClick: () => void }) {
  const score = video.score?.total || 0
  const reasons = video.score?.reasons || []

  return (
    <div
      onClick={onClick}
      className="bg-white rounded-xl border border-[#E8E0D4] overflow-hidden cursor-pointer hover:shadow-lg transition group relative"
    >
      {/* Thumbnail */}
      <div className="relative h-[130px] bg-[#FDF6EE] overflow-hidden">
        {video.thumbnail ? (
          <img
            src={video.thumbnail}
            alt={video.title}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-4xl">🎭</div>
        )}
        {/* Duration badge */}
        <span className="absolute bottom-1 right-1 bg-black/70 text-white text-[10px] px-1.5 py-0.5 rounded font-mono">
          {formatDuration(video.duration)}
        </span>
        {/* Posted overlay */}
        {video.posted && (
          <div className="absolute inset-0 bg-black/30 flex items-center justify-center">
            <Badge variant="secondary" className="bg-white/90 text-xs">Posted</Badge>
          </div>
        )}
        {/* Score ring */}
        <div className="absolute top-1.5 right-1.5">
          <ScoreRing score={score} size={38} />
        </div>
      </div>

      {/* Info */}
      <div className="p-3">
        <div className="font-semibold text-sm text-[#2D2A26] truncate">{video.artist || "Unknown"}</div>
        <div className="text-xs text-[#8B8680] truncate mt-0.5">{video.song || video.title}</div>
        <div className="flex items-center gap-2 mt-1.5 text-[10px] text-[#B5AFA8]">
          <span>{formatViews(video.views)} views</span>
          {video.year > 0 && <span>· {video.year}</span>}
          {video.hd && <span className="text-[#3B6DD4] font-bold">HD</span>}
        </div>
        {/* Reason pills */}
        {reasons.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-2">
            {reasons.slice(0, 4).map((r, i) => (
              <span
                key={i}
                className={`text-[9px] px-1.5 py-0.5 rounded-full font-medium ${TAG_COLORS[r.tag] || "bg-gray-100 text-gray-600"}`}
              >
                {r.label.length > 18 ? r.label.slice(0, 18) + "..." : r.label}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
