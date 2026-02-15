const BASE = '/api';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail || 'Request failed');
  }
  return res.json();
}

export interface Project {
  id: number;
  created_at: string;
  updated_at: string;
  youtube_url: string;
  artist: string;
  work: string;
  composer: string;
  composition_year: string;
  nationality: string;
  nationality_flag: string;
  voice_type: string;
  birth_date: string;
  death_date: string;
  album_opera: string;
  category: string;
  hook: string;
  hook_category: string;
  highlights: string;
  original_duration: string;
  cut_start: string;
  cut_end: string;
  status: string;
  overlay_json: { timestamp: string; text: string }[] | null;
  post_text: string | null;
  youtube_title: string | null;
  youtube_tags: string | null;
  overlay_approved: boolean;
  post_approved: boolean;
  youtube_approved: boolean;
  translations: Translation[];
}

export interface Translation {
  id: number;
  project_id: number;
  language: string;
  overlay_json: { timestamp: string; text: string }[] | null;
  post_text: string | null;
  youtube_title: string | null;
  youtube_tags: string | null;
}

export interface DetectedMetadata {
  artist: string;
  work: string;
  composer: string;
  composition_year: string;
  nationality: string;
  nationality_flag: string;
  voice_type: string;
  birth_date: string;
  death_date: string;
  album_opera: string;
  confidence: string;
}

export interface ExportData {
  language: string;
  overlay_json: { timestamp: string; text: string }[] | null;
  post_text: string | null;
  youtube_title: string | null;
  youtube_tags: string | null;
  srt: string;
}

export const api = {
  detectMetadata: async (screenshot: File, youtubeUrl: string): Promise<DetectedMetadata> => {
    const formData = new FormData();
    formData.append('screenshot', screenshot);
    formData.append('youtube_url', youtubeUrl);
    const res = await fetch(`${BASE}/projects/detect-metadata`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(body.detail || 'Detection failed');
    }
    return res.json();
  },
  listProjects: () => request<Project[]>('/projects'),
  getProject: (id: number) => request<Project>(`/projects/${id}`),
  createProject: (data: Record<string, string>) =>
    request<Project>('/projects', { method: 'POST', body: JSON.stringify(data) }),
  updateProject: (id: number, data: Record<string, string>) =>
    request<Project>(`/projects/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  generate: (id: number) =>
    request<Project>(`/projects/${id}/generate`, { method: 'POST' }),
  regenerateOverlay: (id: number, customPrompt?: string) =>
    request<Project>(`/projects/${id}/regenerate-overlay`, {
      method: 'POST',
      body: JSON.stringify({ custom_prompt: customPrompt || null }),
    }),
  regeneratePost: (id: number, customPrompt?: string) =>
    request<Project>(`/projects/${id}/regenerate-post`, {
      method: 'POST',
      body: JSON.stringify({ custom_prompt: customPrompt || null }),
    }),
  regenerateYoutube: (id: number, customPrompt?: string) =>
    request<Project>(`/projects/${id}/regenerate-youtube`, {
      method: 'POST',
      body: JSON.stringify({ custom_prompt: customPrompt || null }),
    }),

  approveOverlay: (id: number, overlayJson: { timestamp: string; text: string }[]) =>
    request<Project>(`/projects/${id}/approve-overlay`, {
      method: 'PUT',
      body: JSON.stringify({ overlay_json: overlayJson }),
    }),
  approvePost: (id: number, postText: string) =>
    request<Project>(`/projects/${id}/approve-post`, {
      method: 'PUT',
      body: JSON.stringify({ post_text: postText }),
    }),
  approveYoutube: (id: number, title: string, tags: string) =>
    request<Project>(`/projects/${id}/approve-youtube`, {
      method: 'PUT',
      body: JSON.stringify({ youtube_title: title, youtube_tags: tags }),
    }),

  translate: (id: number) =>
    request<Project>(`/projects/${id}/translate`, { method: 'POST' }),
  retranslate: (id: number, lang: string) =>
    request<ExportData>(`/projects/${id}/retranslate/${lang}`, { method: 'POST' }),
  updateTranslation: (id: number, lang: string, data: Partial<ExportData>) =>
    request<ExportData>(`/projects/${id}/translation/${lang}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  exportLang: (id: number, lang: string) =>
    request<ExportData>(`/projects/${id}/export/${lang}`),
  exportZipUrl: (id: number) => `${BASE}/projects/${id}/export-zip`,
  exportToFolder: (id: number) =>
    request<{ path: string }>(`/projects/${id}/export-to-folder`, { method: 'POST' }),
  getExportConfig: () =>
    request<{ export_path: string | null }>('/projects/export-config'),
};
