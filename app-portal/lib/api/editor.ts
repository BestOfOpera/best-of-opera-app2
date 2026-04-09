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
  sem_lyrics: boolean
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
  passo_atual: number
  erro_msg: string | null
  progresso_detalhe: ProgressoDetalhe | null
  task_heartbeat: string | null
  overlays_count?: number
  posts_count?: number
  seo_count?: number
  created_at: string
  updated_at: string
  perfil_id?: number
  perfil_nome?: string
  redator_project_id?: number | null
  published_at?: string | null
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

export interface OverlaySegmento {
  text: string
  start?: string | number
  end?: string | number
  timestamp?: string | number
  type?: string
  _is_cta?: boolean
  [key: string]: unknown
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
  tipo: string
  status: string
  arquivo: string | null
  tamanho_bytes: number | null
  erro_msg: string | null
  created_at: string
}

/** Formato interno (inner) do progresso — armazenado sob uma chave de namespace. */
export interface ProgressoDetalheInner {
  etapa: "traducao" | "render" | "pacote" | string
  total?: number
  concluidos?: number
  atual?: string | null
}

/**
 * progresso_detalhe da API — pode ser:
 *  - Novo formato: { "traducao": {...}, "render": {...}, "pacote": {...} }
 *  - Formato antigo (compat): { etapa: "traducao"|"render", total, concluidos, atual }
 */
export type ProgressoDetalhe = Record<string, ProgressoDetalheInner> | ProgressoDetalheInner | null

export interface FilaStatus {
  ocupado: boolean
  edicao_id: number | null
  etapa: string | null
  progresso: ProgressoDetalhe
}

export interface PacoteStatus {
  status: "nenhum" | "gerando" | "pronto" | "erro"
  url: string | null
  erro: string | null
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
  editor_status: "em_andamento" | "concluido" | null
  editor_edicao_id: number | null
}

// --- Dashboard Interfaces ---

export interface DashboardVisaoGeral {
  resumo: {
    total: number
    em_andamento: number
    concluidos: number
    em_erro: number
    worker_status: string
  }
  projetos: (Edicao & { link_direto: string })[]
}

export interface DashboardR2Inventario {
  categorias: {
    nome: string
    arquivos: { nome: string; status: "ok" | "falta" | "erro"; tamanho?: string }[]
    concluido: boolean
  }[]
  total_arquivos: number
  total_tamanho: string
}

export interface DashboardSaude {
  semaforo: "verde" | "amarelo" | "vermelho"
  worker: {
    status: string
    progresso: number
    uptime: string
  }
  fila: {
    quantidade: number
    proxima_task: string | null
  }
  ultimo_erro: {
    edicao_id: number
    msg: string
    timestamp: string
  } | null
  sentry_url: string
}

export interface DashboardProducao {
  grafico: { data: string; sucesso: number; erro: number }[]
  metricas: {
    taxa_sucesso: string
    tempo_medio: string
    gargalo: string
  }
  etapas: { etapa: string; tempo_medio: string }[]
}

// --- Reports Interfaces ---

export interface Report {
  id: number
  colaborador: string
  titulo: string
  descricao: string
  tipo: "bug" | "melhoria" | "sugestao"
  prioridade: "alta" | "media" | "baixa"
  status: "novo" | "analise" | "resolvido"
  projeto_id?: number
  screenshots: string[]
  resolucao?: string
  resolvido_por?: string
  codigo_err?: string
  created_at: string
  perfil_id?: number
  perfil_nome?: string
}

export interface ReportResumo {
  novos: number
  em_analise: number
  resolvidos: number
}

// --- Admin / Marcas Interfaces ---
export interface Perfil {
  id: number
  nome: string
  sigla: string
  slug: string
  ativo: boolean
  sem_lyrics_default: boolean
  editorial_lang: string
  identity_prompt: string
  identity_prompt_redator: string
  tom_de_voz: string
  tom_de_voz_redator: string
  hashtags_fixas: string[]
  categorias_hook: string[]
  escopo_conteudo: string
  idiomas_alvo: string[]
  idioma_preview: string
  overlay_style: Record<string, any>
  lyrics_style: Record<string, any>
  traducao_style: Record<string, any>
  overlay_max_chars: number
  overlay_max_chars_linha: number
  lyrics_max_chars: number
  traducao_max_chars: number
  overlay_interval_secs: number
  custom_post_structure: string
  video_width: number
  video_height: number
  cor_primaria: string
  cor_secundaria: string
  r2_prefix: string
  logo_url: string
  font_name: string
  font_file_r2_key: string | null
  overlay_cta: string | null
  // Curadoria
  curadoria_categories?: Record<string, any>
  elite_hits?: any[]
  power_names?: any[]
  voice_keywords?: any[]
  institutional_channels?: any[]
  category_specialty?: Record<string, any>
  scoring_weights?: Record<string, any>
  curadoria_filters?: Record<string, any>
  anti_spam_terms?: string
  playlist_id?: string
  created_at: string
}

export interface AuthUser {
  id: number
  nome: string
  email: string
  role: string
  ativo: boolean
  must_change_password?: boolean
  ultimo_login?: string
}


export const editorApi = {
  listarEdicoes: (params?: Record<string, string>, perfil_id?: number) => {
    const p: Record<string, string> = { ...params }
    if (perfil_id) p.perfil_id = perfil_id.toString()
    const qs = Object.keys(p).length ? "?" + new URLSearchParams(p).toString() : ""
    return request<{ edicoes: Edicao[]; total: number; page: number; limit: number; total_pages: number }>(`${BASE()}/edicoes${qs}`)
  },
  criarEdicao: (data: Partial<Edicao>, perfil_id?: number) => {
    const body = { ...data }
    if (perfil_id) body.perfil_id = perfil_id
    return request<Edicao>(`${BASE()}/edicoes`, { method: "POST", body: JSON.stringify(body) })
  },
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
  uploadRenderManual: (id: number, idioma: string, file: File) => {
    const form = new FormData()
    form.append("file", file)
    return requestFormData<{ status: string; idioma: string; arquivo: string; tamanho_bytes: number }>(
      `${BASE()}/edicoes/${id}/renders/${idioma}/upload-render-manual`, form
    )
  },
  uploadOverlays: (id: number, file: File) => {
    const form = new FormData()
    form.append("file", file)
    return requestFormData<{ status: string; salvos: string[]; erros: Record<string, string>; total_segmentos: number }>(`${BASE()}/edicoes/${id}/upload-overlays`, form)
  },
  listarOverlays: (id: number) =>
    request<Record<string, { id: number; segmentos: OverlaySegmento[]; segmentos_original: OverlaySegmento[]; updated_at: string | null }>>(`${BASE()}/edicoes/${id}/overlays`),
  atualizarOverlay: (id: number, idioma: string, segmentos: OverlaySegmento[]) =>
    request<{ status: string; idioma: string; segmentos_count: number; mensagem: string }>(
      `${BASE()}/edicoes/${id}/overlays/${idioma}`,
      { method: "PATCH", body: JSON.stringify({ segmentos }) }
    ),
  statusVideo: (id: number) =>
    request<{ status: string; video_completo: boolean; audio_completo: boolean; duracao_total: number | null }>(`${BASE()}/edicoes/${id}/video/status`),
  buscarLetra: (id: number) =>
    request<{ letra: string; fonte: string }>(`${BASE()}/edicoes/${id}/letra`, { method: "POST", timeout: 90000 }),
  aprovarLetra: (id: number, data: { letra: string }) =>
    request<Edicao>(`${BASE()}/edicoes/${id}/letra`, { method: "PUT", body: JSON.stringify(data) }),
  iniciarTranscricao: (id: number) =>
    request<{ status: string }>(`${BASE()}/edicoes/${id}/transcricao`, { method: "POST" }),
  criarAlinhamentoManual: (id: number) =>
    request<{ ok: boolean; alinhamento_id: number; corte: { inicio: string | null; fim: string | null } }>(
      `${BASE()}/edicoes/${id}/alinhamento-manual`, { method: "POST" }
    ),
  obterAlinhamento: (id: number) =>
    request<AlinhamentoResponse>(`${BASE()}/edicoes/${id}/alinhamento`),
  validarAlinhamento: (id: number, data: { segmentos: Segmento[] }) =>
    request<Edicao>(`${BASE()}/edicoes/${id}/alinhamento`, { method: "PUT", body: JSON.stringify(data) }),
  aplicarCorte: (id: number, params?: Record<string, unknown>) =>
    request<Edicao>(`${BASE()}/edicoes/${id}/aplicar-corte`, { method: "POST", body: JSON.stringify(params || {}), timeout: 120000 }),
  infoCorte: (id: number) =>
    request<{ cut_start: string; cut_end: string; duracao: number }>(`${BASE()}/edicoes/${id}/corte`),
  traduzirLyrics: (id: number) =>
    request<{ traducoes: Record<string, string> }>(`${BASE()}/edicoes/${id}/traducao-lyrics`, { method: "POST", timeout: 180000 }),
  obterTraducoes: (id: number) =>
    request<{ traducoes: Record<string, string> }>(`${BASE()}/edicoes/${id}/traducao-lyrics`),
  renderizar: (id: number, opts?: { sem_legendas?: boolean }) => {
    const qs = opts?.sem_legendas ? "?sem_legendas=true" : ""
    return request<{ status: string }>(`${BASE()}/edicoes/${id}/renderizar${qs}`, { method: "POST" })
  },
  renderizarPreview: (id: number, opts?: { sem_legendas?: boolean }) => {
    const qs = opts?.sem_legendas ? "?sem_legendas=true" : ""
    return request<{ status: string }>(`${BASE()}/edicoes/${id}/renderizar-preview${qs}`, { method: "POST" })
  },
  aprovarPreview: (id: number, params: { aprovado: boolean; notas_revisao?: string }, opts?: { sem_legendas?: boolean }) => {
    const qs = opts?.sem_legendas ? "?sem_legendas=true" : ""
    return request<Edicao>(`${BASE()}/edicoes/${id}/aprovar-preview${qs}`, { method: "POST", body: JSON.stringify(params) })
  },
  uploadVideoSource: (id: number, file: File) => {
    const form = new FormData()
    form.append("file", file)
    return requestFormData<{ url: string; tamanho_bytes: number; renders_invalidados: number }>(
      `${BASE()}/edicoes/${id}/upload-video-source`,
      form,
      600_000, // 10 min timeout para vídeos grandes
    )
  },
  listarRenders: (id: number) =>
    request<Render[]>(`${BASE()}/edicoes/${id}/renders`),
  exportarRenders: (id: number) =>
    request<{ pasta: string; arquivos_exportados: number }>(`${BASE()}/edicoes/${id}/exportar`, { method: "POST", timeout: 60000 }),
  reRenderizar: (id: number, idioma: string) =>
    request<{ status: string }>(`${BASE()}/edicoes/${id}/re-renderizar/${idioma}`, { method: "POST" }),
  reTraduzir: (id: number, idioma: string) =>
    request<{ status: string }>(`${BASE()}/edicoes/${id}/re-traduzir/${idioma}`, { method: "POST" }),


  audioUrl: (id: number) => `${BASE()}/edicoes/${id}/audio`,
  downloadRenderUrl: (edicaoId: number, renderId: number) =>
    `${BASE()}/edicoes/${edicaoId}/renders/${renderId}/download`,
  pacoteUrl: (id: number) => `${BASE()}/edicoes/${id}/pacote`,
  pacoteDownloadUrl: (id: number) => `${BASE()}/edicoes/${id}/pacote/download`,
  iniciarPacote: (id: number) =>
    request<{ status: string; mensagem: string }>(`${BASE()}/edicoes/${id}/pacote`, { method: "POST", body: "{}" }),
  statusPacote: (id: number) =>
    request<PacoteStatus>(`${BASE()}/edicoes/${id}/pacote/status`),

  marcarPublicado: (id: number) =>
    request<Edicao>(`${BASE()}/edicoes/${id}/publicado`, { method: "PATCH" }),

  desbloquear: (id: number) =>
    request<{ novo_status: string; renders_concluidos: number; traducoes: number }>(
      `${BASE()}/edicoes/${id}/desbloquear`, { method: "POST" }
    ),

  limparEdicao: (id: number) =>
    request<{ status: string; mensagem: string }>(
      `${BASE()}/edicoes/${id}/limpar-edicao`, { method: "POST" }
    ),

  filaStatus: () => request<FilaStatus>(`${BASE()}/fila/status`),

  listarProjetosRedator: (perfil_id?: number) => {
    const qs = perfil_id ? `?perfil_id=${perfil_id}` : ""
    return request<RedatorProject[]>(`${BASE()}/redator/projetos${qs}`)
  },
  importarDoRedator: (projectId: number, idioma?: string, ehInstrumental?: boolean, perfil_id?: number) => {
    const params = new URLSearchParams()
    if (idioma) params.append("idioma", idioma)
    if (ehInstrumental) params.append("eh_instrumental", "true")
    if (perfil_id) params.append("perfil_id", perfil_id.toString())
    const qs = params.toString() ? `?${params.toString()}` : ""
    return request<Edicao>(`${BASE()}/redator/importar/${projectId}${qs}`, { method: "POST", timeout: 60000 })
  },

  // Dashboard API
  dashboardVisaoGeral: (perfil_id?: number) => {
    const qs = perfil_id ? `?perfil_id=${perfil_id}` : ""
    return request<DashboardVisaoGeral>(`${BASE()}/dashboard/visao-geral${qs}`)
  },
  dashboardProjeto: (id: number) => request<Edicao>(`${BASE()}/edicoes/${id}`),
  dashboardSaude: () => request<DashboardSaude>(`${BASE()}/dashboard/saude`),
  dashboardProducao: (perfilId?: number) => {
    const qs = perfilId ? `?perfil_id=${perfilId}` : ""
    return request<DashboardProducao>(`${BASE()}/dashboard/producao${qs}`)
  },

  // Reports API
  criarReport: (data: Partial<Report>, perfil_id?: number) => {
    const body = { ...data }
    if (perfil_id) body.perfil_id = perfil_id
    return request<Report>(`${BASE()}/reports`, { method: "POST", body: JSON.stringify(body) })
  },
  uploadScreenshot: (id: number, file: File) => {
    const form = new FormData()
    form.append("file", file)
    return requestFormData<{ url: string }>(`${BASE()}/reports/${id}/screenshot`, form)
  },
  listarReports: (params?: Record<string, string>, perfil_id?: number) => {
    const p = { ...params }
    if (perfil_id) p.perfil_id = perfil_id.toString()
    const qs = p ? "?" + new URLSearchParams(p).toString() : ""
    return request<Report[]>(`${BASE()}/reports${qs}`)
  },
  detalheReport: (id: number) => request<Report>(`${BASE()}/reports/${id}`),
  atualizarReport: (id: number, data: Partial<Report>) =>
    request<Report>(`${BASE()}/reports/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  resumoReports: (perfil_id?: number) => {
    const qs = perfil_id ? `?perfil_id=${perfil_id}` : ""
    return request<ReportResumo>(`${BASE()}/reports/resumo${qs}`)
  },
  deletarReport: (id: number) =>
    request<void>(`${BASE()}/reports/${id}`, { method: "DELETE" }),
  deletarReportsResolvidos: (perfil_id?: number) => {
    const qs = perfil_id ? `?perfil_id=${perfil_id}` : ""
    return request<{ deleted: number }>(`${BASE()}/reports/resolvidos${qs}`, { method: "DELETE" })
  },

  // Auth API
  login: (data: { email: string; senha: string }) =>
    request<{ access_token: string }>(`${BASE()}/auth/login`, { method: "POST", body: JSON.stringify(data) }),
  getMe: () => request<AuthUser>(`${BASE()}/auth/me`),
  listarUsuarios: () => request<AuthUser[]>(`${BASE()}/auth/usuarios`),
  registrarUsuario: (data: Partial<AuthUser> & { senha?: string }) =>
    request<AuthUser>(`${BASE()}/auth/registrar`, { method: "POST", body: JSON.stringify(data) }),
  atualizarUsuario: (id: number, data: Partial<AuthUser> & { senha?: string }) =>
    request<AuthUser>(`${BASE()}/auth/usuarios/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  alterarSenha: (senha_nova: string) =>
    request<void>(`${BASE()}/auth/alterar-senha`, { method: "POST", body: JSON.stringify({ senha_nova }) }),

  // Admin Perfis API
  listarPerfis: () => request<Perfil[]>(`${BASE()}/admin/perfis`),
  detalharPerfil: (id: number) => request<Perfil>(`${BASE()}/admin/perfis/${id}`),
  criarPerfil: (data: Partial<Perfil>) => request<Perfil>(`${BASE()}/admin/perfis`, { method: "POST", body: JSON.stringify(data) }),
  atualizarPerfil: (id: number, data: Partial<Perfil>, force = false) => request<Perfil>(`${BASE()}/admin/perfis/${id}${force ? "?force=true" : ""}`, { method: "PUT", body: JSON.stringify(data) }),
  atualizarPerfilParcial: (id: number, data: Partial<Perfil>, force = false) => request<Perfil>(`${BASE()}/admin/perfis/${id}${force ? "?force=true" : ""}`, { method: "PATCH", body: JSON.stringify(data) }),
  duplicarPerfil: (id: number) => request<Perfil>(`${BASE()}/admin/perfis/${id}/duplicar`, { method: "POST" }),
  resetarEdicoesPerfil: (id: number, force = false) =>
    request<{ deleted: number; r2_files_deleted: number }>(`${BASE()}/admin/perfis/${id}/edicoes${force ? "?force=true" : ""}`, { method: "DELETE", timeout: 120000 }),
  previewLegenda: (id: number) => request<{ status: string; url?: string }>(`${BASE()}/admin/perfis/${id}/preview-legenda`),
  uploadFonte: (id: number, file: File, force = false) => {
    const form = new FormData()
    form.append("file", file)
    return requestFormData<Perfil>(`${BASE()}/admin/perfis/${id}/upload-font${force ? "?force=true" : ""}`, form)
  },

  // Analytics API
  heartbeat: () => request<{ ok: boolean }>(`${BASE()}/auth/heartbeat`, { method: "POST" }),
  getUserLoginHistory: (userId: number, limit = 50) =>
    request<{ user_id: number; total: number; logins: Array<{ timestamp: string | null; ip: string | null; device: string }> }>(
      `${BASE()}/auth/usuarios/${userId}/logins?limit=${limit}`,
    ),
  getUserSessions: (userId: number, days = 30) =>
    request<{ user_id: number; today_minutes: number; week_minutes: number; month_minutes: number; avg_daily_minutes: number; days_active: number; by_day: Array<{ date: string; minutes: number }>; sessions: Array<{ started: string; ended: string; duration_min: number }> }>(
      `${BASE()}/auth/usuarios/${userId}/sessions?days=${days}`,
    ),
}
