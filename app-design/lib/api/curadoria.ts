import { request } from "./base"

const BASE = "/api/curadoria"

export interface ScoreReason {
  tag: string
  label: string
  points: number
}

export interface VideoScore {
  total: number
  reasons: ScoreReason[]
}

export interface Video {
  video_id: string
  url: string
  title: string
  song: string
  artist: string
  channel: string
  thumbnail: string
  duration: number
  views: number
  year: number
  hd: boolean
  category: string
  posted: boolean
  score: VideoScore
}

export interface Quota {
  total_points: number
  remaining: number
  limit: number
}

export interface Category {
  key: string
  name: string
  emoji: string
  desc: string
  last_seed: number
  total_seeds: number
}

export interface Download {
  video_id: string
  filename: string
  youtube_url: string
  downloaded_at: string
}

export interface SearchResult {
  videos: Video[]
  total_found?: number
  posted_hidden?: number
  cached?: boolean
  seed_index?: number
  total_seeds?: number
  seed_query?: string
}

export const curadoriaApi = {
  auth: (password: string) =>
    fetch(`${BASE}/auth?password=${encodeURIComponent(password)}`, { method: "POST" })
      .then(res => { if (!res.ok) throw new Error("Senha incorreta"); return res }),

  health: () => request<{ youtube_api: boolean }>(`${BASE}/health`),

  quota: () => request<Quota>(`${BASE}/quota/status`),

  categories: () => request<{ categories: Category[] }>(`${BASE}/categories`),

  searchCategory: (key: string, hidePosted = true, forceRefresh = false) =>
    request<SearchResult>(`${BASE}/category/${key}?hide_posted=${hidePosted}&force_refresh=${forceRefresh}`),

  search: (query: string, hidePosted = true) =>
    request<SearchResult>(`${BASE}/search?q=${encodeURIComponent(query)}&max_results=50&hide_posted=${hidePosted}`),

  ranking: (hidePosted = true) =>
    request<SearchResult>(`${BASE}/ranking?hide_posted=${hidePosted}`),

  playlistVideos: (hidePosted = true) =>
    request<{ videos: Video[] }>(`${BASE}/playlist/videos?hide_posted=${hidePosted}`),

  cacheStatus: () => request<{ playlist?: { count: number } }>(`${BASE}/cache/status`),

  downloadVideo: async (videoId: string, artist: string, song: string) => {
    const url = `${BASE}/download/${videoId}?artist=${encodeURIComponent(artist)}&song=${encodeURIComponent(song)}`
    const resp = await fetch(url)
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: "Download failed" }))
      throw new Error(err.detail || `HTTP ${resp.status}`)
    }
    const blob = await resp.blob()
    const cd = resp.headers.get("content-disposition")
    const fnMatch = cd && cd.match(/filename="(.+?)"/)
    const filename = fnMatch ? fnMatch[1] : `${artist} - ${song}.mp4`
    const a = document.createElement("a")
    a.href = URL.createObjectURL(blob)
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(a.href)
  },

  downloads: () => request<{ downloads: Download[] }>(`${BASE}/downloads`),

  downloadsExportUrl: () => `${BASE}/downloads/export`,
}
