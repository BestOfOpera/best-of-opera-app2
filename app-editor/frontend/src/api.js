import axios from 'axios'

const baseURL = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/api/v1/editor`
  : '/api/v1/editor'

const api = axios.create({ baseURL })

export const editorApi = {
  // Edições
  listarEdicoes: (params) => api.get('/edicoes', { params }).then(r => r.data),
  criarEdicao: (data) => api.post('/edicoes', data).then(r => r.data),
  obterEdicao: (id) => api.get(`/edicoes/${id}`).then(r => r.data),
  atualizarEdicao: (id, data) => api.patch(`/edicoes/${id}`, data).then(r => r.data),
  removerEdicao: (id) => api.delete(`/edicoes/${id}`).then(r => r.data),

  // Pipeline
  garantirVideo: (id) => api.post(`/edicoes/${id}/garantir-video`).then(r => r.data),
  statusVideo: (id) => api.get(`/edicoes/${id}/video/status`).then(r => r.data),
  buscarLetra: (id) => api.post(`/edicoes/${id}/letra`).then(r => r.data),
  aprovarLetra: (id, data) => api.put(`/edicoes/${id}/letra`, data).then(r => r.data),
  iniciarTranscricao: (id) => api.post(`/edicoes/${id}/transcricao`).then(r => r.data),
  obterAlinhamento: (id) => api.get(`/edicoes/${id}/alinhamento`).then(r => r.data),
  validarAlinhamento: (id, data) => api.put(`/edicoes/${id}/alinhamento`, data).then(r => r.data),
  aplicarCorte: (id) => api.post(`/edicoes/${id}/aplicar-corte`).then(r => r.data),
  infoCorte: (id) => api.get(`/edicoes/${id}/corte`).then(r => r.data),
  traduzirLyrics: (id) => api.post(`/edicoes/${id}/traducao-lyrics`).then(r => r.data),
  obterTraducoes: (id) => api.get(`/edicoes/${id}/traducao-lyrics`).then(r => r.data),
  renderizar: (id) => api.post(`/edicoes/${id}/renderizar`).then(r => r.data),
  listarRenders: (id) => api.get(`/edicoes/${id}/renders`).then(r => r.data),

  // Importar do Redator
  listarProjetosRedator: () => api.get('/redator/projetos').then(r => r.data),
  importarDoRedator: (projectId) => api.post(`/redator/importar/${projectId}`).then(r => r.data),
}
