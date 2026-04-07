import { request, requestFormData, API_URLS } from "./base"

function BASE() { return API_URLS.redator + "/api" }

export interface Project {
  id: number
  created_at: string
  updated_at: string
  perfil_id?: number
  perfil_nome?: string
  youtube_url: string
  artist: string
  work: string
  composer: string
  composition_year: string
  nationality: string
  nationality_flag: string
  voice_type: string
  birth_date: string
  death_date: string
  album_opera: string
  category: string
  hook: string
  hook_category: string
  highlights: string
  original_duration: string
  cut_start: string
  cut_end: string
  status: string
  overlay_json: { timestamp: string; text: string }[] | null
  post_text: string | null
  youtube_title: string | null
  youtube_tags: string | null
  overlay_approved: boolean
  post_approved: boolean
  youtube_approved: boolean
  brand_slug: string
  // RC (Reels Classics)
  research_data: Record<string, any> | null
  hooks_json: { ganchos: Array<{ texto: string; angulo: string; tipo: string; fio_narrativo?: string; rank?: number }> } | null
  selected_hook: string | null
  automation_json: Record<string, any> | null
  automation_approved: boolean
  instrument_formation: string | null
  orchestra: string | null
  conductor: string | null
  scheduled_date: string | null
  translations: Translation[]
  warnings?: string[]
  r2_folder?: string | null
}

export interface Translation {
  id: number
  project_id: number
  language: string
  overlay_json: { timestamp: string; text: string }[] | null
  post_text: string | null
  youtube_title: string | null
  youtube_tags: string | null
}

export interface DetectedMetadata {
  artist: string
  work: string
  composer: string
  composition_year: string
  nationality: string
  nationality_flag: string
  voice_type: string
  birth_date: string
  death_date: string
  album_opera: string
  confidence: string
  // RC fields (optional — only present for reels-classics)
  instrument_formation?: string
  orchestra?: string
  conductor?: string
  category?: string
}

export interface R2AvailableItem {
  folder: string
  artist: string
  work: string
  prepared_at?: string
}

export interface ExportData {
  language: string
  overlay_json: { timestamp: string; text: string }[] | null
  post_text: string | null
  youtube_title: string | null
  youtube_tags: string | null
  srt: string
}



export const redatorApi = {
  detectMetadata: (screenshot: File, youtubeUrl?: string, brand_slug?: string) => {
    const formData = new FormData()
    formData.append("file", screenshot)
    if (youtubeUrl) formData.append("youtube_url", youtubeUrl)
    if (brand_slug) formData.append("brand_slug", brand_slug)
    return requestFormData<DetectedMetadata>(`${BASE()}/projects/detect-metadata`, formData, 60000)
  },
  detectMetadataFromText: (youtubeUrl: string, title: string, description: string, brand_slug?: string) =>
    request<DetectedMetadata>(`${BASE()}/projects/detect-metadata-text`, {
      method: "POST",
      timeout: 60000,
      body: JSON.stringify({ youtube_url: youtubeUrl, title, description, brand_slug }),
    }),
  listProjects: (params?: { brand_slug?: string; search?: string; status?: string; sort_by?: string; sort_order?: string; page?: number; limit?: number }) => {
    const qs = params ? "?" + new URLSearchParams(
      Object.entries(params).filter(([, v]) => v !== undefined && v !== "").map(([k, v]) => [k, String(v)])
    ).toString() : ""
    return request<{ projects: Project[]; total: number; page: number; limit: number; total_pages: number }>(`${BASE()}/projects${qs}`)
  },
  listR2Available: (brand_slug?: string, r2_prefix?: string) => {
    const params = new URLSearchParams()
    if (brand_slug) params.append("brand_slug", brand_slug)
    if (r2_prefix) params.append("r2_prefix", r2_prefix)
    const qs = params.toString() ? `?${params.toString()}` : ""
    return request<R2AvailableItem[]>(`${BASE()}/projects/r2-available${qs}`)
  },
  deleteR2Items: (folders: string[]) =>
    request<{ deleted: string[] }>(`${BASE()}/projects/r2-available`, {
      method: "DELETE",
      body: JSON.stringify({ folders }),
    }),
  deleteProject: (id: number) =>
    request<{ ok: boolean }>(`${BASE()}/projects/${id}`, { method: "DELETE" }),
  deleteProjects: (ids: number[]) =>
    request<{ deleted: number }>(`${BASE()}/projects/bulk`, { method: "DELETE", body: JSON.stringify({ ids }) }),
  getProject: (id: number) => request<Project>(`${BASE()}/projects/${id}`),
  createProject: (data: Record<string, string>, brand_slug?: string) => {
    const body = { ...data }
    if (brand_slug) body.brand_slug = brand_slug
    return request<Project>(`${BASE()}/projects`, { method: "POST", body: JSON.stringify(body) })
  },
  updateProject: (id: number, data: Record<string, string>) =>
    request<Project>(`${BASE()}/projects/${id}`, { method: "PUT", body: JSON.stringify(data) }),

  generate: (id: number) =>
    request<Project>(`${BASE()}/projects/${id}/generate`, { method: "POST", timeout: 90000 }),
  regenerateOverlay: (id: number, customPrompt?: string) =>
    request<Project>(`${BASE()}/projects/${id}/regenerate-overlay`, {
      method: "POST",
      timeout: 90000,
      body: JSON.stringify({ custom_prompt: customPrompt || null }),
    }),
  regeneratePost: (id: number, customPrompt?: string) =>
    request<Project>(`${BASE()}/projects/${id}/regenerate-post`, {
      method: "POST",
      timeout: 90000,
      body: JSON.stringify({ custom_prompt: customPrompt || null }),
    }),
  regenerateYoutube: (id: number, customPrompt?: string) =>
    request<Project>(`${BASE()}/projects/${id}/regenerate-youtube`, {
      method: "POST",
      timeout: 90000,
      body: JSON.stringify({ custom_prompt: customPrompt || null }),
    }),

  approveOverlay: (id: number, overlayJson: { timestamp: string; text: string }[]) =>
    request<Project>(`${BASE()}/projects/${id}/approve-overlay`, {
      method: "PUT",
      body: JSON.stringify({ overlay_json: overlayJson }),
    }),
  approvePost: (id: number, postText: string) =>
    request<Project>(`${BASE()}/projects/${id}/approve-post`, {
      method: "PUT",
      body: JSON.stringify({ post_text: postText }),
    }),
  approveYoutube: (id: number, title: string, tags: string) =>
    request<Project>(`${BASE()}/projects/${id}/approve-youtube`, {
      method: "PUT",
      body: JSON.stringify({ youtube_title: title, youtube_tags: tags }),
    }),

  // RC (Reels Classics) endpoints
  generateResearchRC: (id: number) =>
    request<Record<string, any>>(`${BASE()}/projects/${id}/generate-research-rc`, { method: "POST", timeout: 180000 }),
  generateHooksRC: (id: number) =>
    request<Record<string, any>>(`${BASE()}/projects/${id}/generate-hooks-rc`, { method: "POST", timeout: 120000 }),
  selectHook: (id: number, body: { hook_index?: number; custom_hook?: string }) =>
    request<Project>(`${BASE()}/projects/${id}/select-hook`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),
  generateOverlayRC: (id: number) =>
    request<Record<string, any>>(`${BASE()}/projects/${id}/generate-overlay-rc`, { method: "POST", timeout: 120000 }),
  generatePostRC: (id: number) =>
    request<Record<string, any>>(`${BASE()}/projects/${id}/generate-post-rc`, { method: "POST", timeout: 120000 }),
  generateAutomationRC: (id: number) =>
    request<Record<string, any>>(`${BASE()}/projects/${id}/generate-automation-rc`, { method: "POST", timeout: 120000 }),
  approveAutomation: (id: number) =>
    request<Project>(`${BASE()}/projects/${id}/approve-automation`, { method: "PUT" }),

  translate: (id: number) =>
    request<Project>(`${BASE()}/projects/${id}/translate`, { method: "POST", timeout: 180000 }),
  retranslate: (id: number, lang: string) =>
    request<ExportData>(`${BASE()}/projects/${id}/retranslate/${lang}`, { method: "POST", timeout: 60000 }),
  updateTranslation: (id: number, lang: string, data: Partial<ExportData>) =>
    request<ExportData>(`${BASE()}/projects/${id}/translation/${lang}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  exportLang: (id: number, lang: string) =>
    request<ExportData>(`${BASE()}/projects/${id}/export/${lang}`),
  exportZipUrl: (id: number) => `${BASE()}/projects/${id}/export-zip`,
  exportToFolder: (id: number) =>
    request<{ path: string }>(`${BASE()}/projects/${id}/export-to-folder`, { method: "POST" }),
  saveToR2: (id: number) =>
    request<{ ok: boolean; r2_base: string }>(`${BASE()}/projects/${id}/save-to-r2`, { method: "POST", timeout: 60000 }),
  getExportConfig: () =>
    request<{ export_path: string | null }>(`${BASE()}/projects/export-config`),
  deleteProjectsByBrand: (brandSlug: string) =>
    request<{ deleted: number }>(`${BASE()}/projects/by-brand/${brandSlug}`, { method: "DELETE", timeout: 60000 }),

  // Calendar
  getCalendar: (startDate: string, endDate: string, brandSlug?: string) => {
    const params = new URLSearchParams({ start_date: startDate, end_date: endDate })
    if (brandSlug) params.append("brand_slug", brandSlug)
    return request<{ scheduled: Project[]; unscheduled: Project[] }>(
      `${BASE()}/calendar?${params.toString()}`
    )
  },
  scheduleProject: (id: number, scheduledDate: string | null) =>
    request<Project>(`${BASE()}/calendar/${id}/schedule`, {
      method: "PUT",
      body: JSON.stringify({ scheduled_date: scheduledDate }),
    }),
}
