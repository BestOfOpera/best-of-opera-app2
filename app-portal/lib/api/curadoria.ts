import { request, API_URLS } from "./base"

function BASE() { return API_URLS.curadoria + "/api" }

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

export interface R2Info {
  video_id: string
  youtube_url: string
  thumbnail_url: string
  title: string
  description: string
}

export const curadoriaApi = {
  auth: (password: string) =>
    fetch(`${BASE()}/auth?password=${encodeURIComponent(password)}`, { method: "POST" })
      .then(res => { if (!res.ok) throw new Error("Senha incorreta"); return res }),

  health: () => request<{ youtube_api: boolean }>(`${BASE()}/health`),

  quota: () => request<Quota>(`${BASE()}/quota/status`),

  categories: (brand_slug?: string) => {
    const qs = brand_slug ? `?brand_slug=${brand_slug}` : ""
    return request<{ categories: Category[] }>(`${BASE()}/categories${qs}`)
  },

  searchCategory: (key: string, hidePosted = true, forceRefresh = false, brand_slug?: string) => {
    const params = new URLSearchParams({ hide_posted: hidePosted.toString(), force_refresh: forceRefresh.toString() })
    if (brand_slug) params.append("brand_slug", brand_slug)
    return request<SearchResult>(`${BASE()}/category/${key}?${params.toString()}`)
  },

  search: (query: string, hidePosted = true, brand_slug?: string) => {
    const params = new URLSearchParams({ q: query, max_results: "50", hide_posted: hidePosted.toString() })
    if (brand_slug) params.append("brand_slug", brand_slug)
    return request<SearchResult>(`${BASE()}/search?${params.toString()}`)
  },

  ranking: (hidePosted = true, brand_slug?: string) => {
    const params = new URLSearchParams({ hide_posted: hidePosted.toString() })
    if (brand_slug) params.append("brand_slug", brand_slug)
    return request<SearchResult>(`${BASE()}/ranking?${params.toString()}`)
  },

  manualVideo: (youtubeUrl: string, brand_slug?: string) => {
    const qs = brand_slug ? `?brand_slug=${brand_slug}` : ""
    return request<Video>(`${BASE()}/manual-video${qs}`, {
      method: "POST",
      body: JSON.stringify({ youtube_url: youtubeUrl }),
      headers: { "Content-Type": "application/json" }
    })
  },

  playlistVideos: (hidePosted = true, brand_slug?: string) => {
    const params = new URLSearchParams({ hide_posted: hidePosted.toString() })
    if (brand_slug) params.append("brand_slug", brand_slug)
    return request<{ videos: Video[] }>(`${BASE()}/playlist/videos?${params.toString()}`)
  },

  refreshPlaylist: (brand_slug?: string) => {
    const qs = brand_slug ? `?brand_slug=${brand_slug}` : ""
    return request<{ status: string; message: string }>(`${BASE()}/playlist/refresh${qs}`, { method: "POST" })
  },

  cacheStatus: () => request<{ playlist?: { count: number } }>(`${BASE()}/cache/status`),

  downloadVideo: async (videoId: string, artist: string, song: string, brand_slug?: string) => {
    const params = new URLSearchParams({ artist, song })
    if (brand_slug) params.append("brand_slug", brand_slug)
    const url = `${BASE()}/download/${videoId}?${params.toString()}`
    const resp = await fetch(url)
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: "Download failed" }))
      throw new Error(err.detail || `HTTP ${resp.status}`)
    }
    const r2Status = resp.headers.get("x-r2-upload") || "unknown"
    const r2Key = resp.headers.get("x-r2-key") || ""
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
    return { r2Status, r2Key, filename }
  },

  /** Download + upload R2 sem streaming pro browser. Retorna JSON. */
  prepareVideo: (videoId: string, artist: string, song: string, brand_slug?: string) => {
    const params = new URLSearchParams({ artist, song })
    if (brand_slug) params.append("brand_slug", brand_slug)
    return request<{
      status: string
      r2_key: string
      r2_base: string
      cached: boolean
      file_size_mb?: number
      message: string
    }>(`${BASE()}/prepare-video/${videoId}?${params.toString()}`, {
      method: "POST",
    })
  },

  /** Verifica se vídeo já está no R2. */
  checkR2: (artist: string, song: string, videoId = "", brand_slug?: string) => {
    const params = new URLSearchParams({ artist, song, video_id: videoId })
    if (brand_slug) params.append("brand_slug", brand_slug)
    return request<{ exists: boolean; r2_key: string; r2_base: string }>(
      `${BASE()}/r2/check?${params.toString()}`
    )
  },

  /** Upload manual de vídeo para R2 (fallback quando yt-dlp demora). */
  uploadVideo: async (videoId: string, artist: string, song: string, file: File, brand_slug?: string) => {
    const params = new URLSearchParams({ artist, song })
    if (brand_slug) params.append("brand_slug", brand_slug)
    const url = `${BASE()}/upload-video/${videoId}?${params.toString()}`
    const formData = new FormData()
    formData.append("file", file)
    const resp = await fetch(url, { method: "POST", body: formData })
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: "Upload failed" }))
      throw new Error(err.detail || `HTTP ${resp.status}`)
    }
    return resp.json() as Promise<{
      status: string
      r2_key: string
      r2_base: string
      file_size_mb: number
      message: string
    }>
  },

  downloads: (brand_slug?: string) => {
    const qs = brand_slug ? `?brand_slug=${brand_slug}` : ""
    return request<{ downloads: Download[] }>(`${BASE()}/downloads${qs}`)
  },

  downloadsExportUrl: (brand_slug?: string) => {
    const qs = brand_slug ? `?brand_slug=${brand_slug}` : ""
    return `${BASE()}/downloads/export${qs}`
  },

  r2Info: (folder: string, brand_slug?: string) => {
    const qs = brand_slug ? `&brand_slug=${brand_slug}` : ""
    return request<R2Info>(`${BASE()}/r2/info?folder=${encodeURIComponent(folder)}${qs}`)
  },
}
