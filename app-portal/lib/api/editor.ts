import { request, requestFormData, API_URLS } from "./base"

function BASE() { return API_URLS.editor + "/api/v1/editor" }

export interface Edicao {
  id: number
  youtube_url: string
  youtube_video_id: string
  artista: string
  musica: string
  compositor: string
  opera: string
  idioma: string
  categoria: string
  eh_instrumental: boolean
  status: string
  cut_start: string | null
  cut_end: string | null
  rota_alinhamento: string | null
  confianca_alinhamento: number | null
  duracao_corte_sec: number | null
  janela_inicio_sec: number | null
  janela_fim_sec: number | null
  letra: string | null
  letra_fonte: string | null
  notas_revisao: string | null
  arquivo_video_completo: boolean
  arquivo_audio_completo: boolean
  erro_msg: string | null
  overlays_count?: number
  posts_count?: number
  seo_count?: number
  created_at: string
  updated_at: string
}

export interface Segmento {
  start: string
  end: string
  texto_final: string
  texto_gemini?: string
  candidato_letra?: string
  flag: string
  confianca: number
}

export interface Janela {
  inicio: number
  fim: number
  duracao: number
}

export interface AlinhamentoData {
  segmentos: Segmento[]
  rota: string
  confianca_media: number
}

export interface AlinhamentoResponse {
  alinhamento: AlinhamentoData
  janela: Janela
}

export interface Render {
  id: number
  edicao_id: number
  idioma: string
  status: string
  arquivo: string | null
  tamanho_bytes: number | null
  erro_msg: string | null
  created_at: string
}

export interface RedatorProject {
  id: number
  artist: string
  work: string
  composer: string
  album_opera?: string
  category: string
  status: string
  youtube_url: string
  cut_start: string
  cut_end: string
  translations_count: number
}

export const editorApi = {
  listarEdicoes: (params?: Record<string, string>) => {
    const qs = params ? "?" + new URLSearchParams(params).toString() : ""
    return request<Edicao[]>(`${BASE()}/edicoes${qs}`)
  },
  criarEdicao: (data: Partial<Edicao>) =>
    request<Edicao>(`${BASE()}/edicoes`, { method: "POST", body: JSON.stringify(data) }),
  obterEdicao: (id: number) => request<Edicao>(`${BASE()}/edicoes/${id}`),
  atualizarEdicao: (id: number, data: Partial<Edicao>) =>
    request<Edicao>(`${BASE()}/edicoes/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  removerEdicao: (id: number) =>
    request<void>(`${BASE()}/edicoes/${id}`, { method: "DELETE" }),

  garantirVideo: (id: number) =>
    request<{ status: string }>(`${BASE()}/edicoes/${id}/garantir-video`, { method: "POST" }),
  uploadVideo: (id: number, file: File) => {
    const form = new FormData()
    form.append("file", file)
    return requestFormData<{ status: string }>(`${BASE()}/edicoes/${id}/upload-video`, form)
  },
  statusVideo: (id: number) =>
    request<{ status: string; progresso?: number }>(`${BASE()}/edicoes/${id}/video/status`),
  buscarLetra: (id: number) =>
    request<{ letra: string; fonte: string }>(`${BASE()}/edicoes/${id}/letra`, { method: "POST" }),
  aprovarLetra: (id: number, data: { letra: string }) =>
    request<Edicao>(`${BASE()}/edicoes/${id}/letra`, { method: "PUT", body: JSON.stringify(data) }),
  iniciarTranscricao: (id: number) =>
    request<{ status: string }>(`${BASE()}/edicoes/${id}/transcricao`, { method: "POST" }),
  obterAlinhamento: (id: number) =>
    request<AlinhamentoResponse>(`${BASE()}/edicoes/${id}/alinhamento`),
  validarAlinhamento: (id: number, data: { segmentos: Segmento[] }) =>
    request<Edicao>(`${BASE()}/edicoes/${id}/alinhamento`, { method: "PUT", body: JSON.stringify(data) }),
  aplicarCorte: (id: number, params?: Record<string, number>) =>
    request<Edicao>(`${BASE()}/edicoes/${id}/aplicar-corte`, { method: "POST", body: JSON.stringify(params || {}) }),
  infoCorte: (id: number) =>
    request<{ cut_start: string; cut_end: string; duracao: number }>(`${BASE()}/edicoes/${id}/corte`),
  traduzirLyrics: (id: number) =>
    request<{ traducoes: Record<string, string> }>(`${BASE()}/edicoes/${id}/traducao-lyrics`, { method: "POST" }),
  obterTraducoes: (id: number) =>
    request<{ traducoes: Record<string, string> }>(`${BASE()}/edicoes/${id}/traducao-lyrics`),
  renderizar: (id: number) =>
    request<{ status: string }>(`${BASE()}/edicoes/${id}/renderizar`, { method: "POST" }),
  renderizarPreview: (id: number) =>
    request<{ status: string }>(`${BASE()}/edicoes/${id}/renderizar-preview`, { method: "POST" }),
  aprovarPreview: (id: number, params: { aprovado: boolean; notas?: string }) =>
    request<Edicao>(`${BASE()}/edicoes/${id}/aprovar-preview`, { method: "POST", body: JSON.stringify(params) }),
  listarRenders: (id: number) =>
    request<Render[]>(`${BASE()}/edicoes/${id}/renders`),
  exportarRenders: (id: number) =>
    request<{ pasta: string; arquivos_exportados: number }>(`${BASE()}/edicoes/${id}/exportar`, { method: "POST" }),

  audioUrl: (id: number) => `${BASE()}/edicoes/${id}/audio`,
  downloadRenderUrl: (edicaoId: number, renderId: number) =>
    `${BASE()}/edicoes/${edicaoId}/renders/${renderId}/download`,

  listarProjetosRedator: () => request<RedatorProject[]>(`${BASE()}/redator/projetos`),
  importarDoRedator: (projectId: number) =>
    request<Edicao>(`${BASE()}/redator/importar/${projectId}`, { method: "POST" }),
}
