"""Pydantic schemas para a API."""
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from datetime import datetime


# --- Perfil ---
class PerfilCreate(BaseModel):
    nome: str
    sigla: str
    slug: Optional[str] = None
    ativo: bool = True
    identity_prompt: Optional[str] = None
    tom_de_voz: Optional[str] = None
    editorial_lang: str = "pt"
    hashtags_fixas: Optional[List[str]] = None
    categorias_hook: Optional[List[str]] = None
    idiomas_alvo: Optional[List[str]] = None
    idioma_preview: str = "pt"
    overlay_style: Optional[Dict[str, Any]] = None
    lyrics_style: Optional[Dict[str, Any]] = None
    traducao_style: Optional[Dict[str, Any]] = None
    overlay_max_chars: int = 70
    overlay_max_chars_linha: int = 35
    lyrics_max_chars: int = 43
    traducao_max_chars: int = 100
    video_width: int = 1080
    video_height: int = 1920
    escopo_conteudo: Optional[str] = None
    duracao_corte_min: int = 30
    duracao_corte_max: int = 90
    cor_primaria: str = "#1a1a2e"
    cor_secundaria: str = "#e94560"
    r2_prefix: str = "editor"


class PerfilUpdate(BaseModel):
    nome: Optional[str] = None
    sigla: Optional[str] = None
    slug: Optional[str] = None
    ativo: Optional[bool] = None
    identity_prompt: Optional[str] = None
    tom_de_voz: Optional[str] = None
    editorial_lang: Optional[str] = None
    hashtags_fixas: Optional[List[str]] = None
    categorias_hook: Optional[List[str]] = None
    idiomas_alvo: Optional[List[str]] = None
    idioma_preview: Optional[str] = None
    overlay_style: Optional[Dict[str, Any]] = None
    lyrics_style: Optional[Dict[str, Any]] = None
    traducao_style: Optional[Dict[str, Any]] = None
    overlay_max_chars: Optional[int] = None
    overlay_max_chars_linha: Optional[int] = None
    lyrics_max_chars: Optional[int] = None
    traducao_max_chars: Optional[int] = None
    video_width: Optional[int] = None
    video_height: Optional[int] = None
    escopo_conteudo: Optional[str] = None
    duracao_corte_min: Optional[int] = None
    duracao_corte_max: Optional[int] = None
    cor_primaria: Optional[str] = None
    cor_secundaria: Optional[str] = None
    r2_prefix: Optional[str] = None


class PerfilOut(BaseModel):
    id: int
    nome: str
    sigla: str
    slug: str
    ativo: bool
    identity_prompt: Optional[str] = None
    tom_de_voz: Optional[str] = None
    editorial_lang: str
    hashtags_fixas: Optional[List[str]] = None
    categorias_hook: Optional[List[str]] = None
    idiomas_alvo: Optional[List[str]] = None
    idioma_preview: str
    overlay_style: Optional[Dict[str, Any]] = None
    lyrics_style: Optional[Dict[str, Any]] = None
    traducao_style: Optional[Dict[str, Any]] = None
    overlay_max_chars: int
    overlay_max_chars_linha: int
    lyrics_max_chars: int
    traducao_max_chars: int
    video_width: int
    video_height: int
    escopo_conteudo: Optional[str] = None
    duracao_corte_min: int
    duracao_corte_max: int
    cor_primaria: str
    cor_secundaria: str
    r2_prefix: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- Edição ---
class EdicaoCreate(BaseModel):
    youtube_url: str
    youtube_video_id: str
    artista: str
    musica: str
    compositor: Optional[str] = None
    opera: Optional[str] = None
    categoria: Optional[str] = None
    idioma: str
    eh_instrumental: bool = False
    # Overlay em JSON (lista de segmentos por idioma)
    overlays: Optional[dict] = None
    # Post/SEO colados do Redator
    posts: Optional[dict] = None
    seo: Optional[dict] = None


class EdicaoUpdate(BaseModel):
    artista: Optional[str] = None
    musica: Optional[str] = None
    compositor: Optional[str] = None
    opera: Optional[str] = None
    categoria: Optional[str] = None
    idioma: Optional[str] = None
    eh_instrumental: Optional[bool] = None
    sem_lyrics: Optional[bool] = None
    status: Optional[str] = None
    passo_atual: Optional[int] = None
    erro_msg: Optional[str] = None


class EdicaoOut(BaseModel):
    id: int
    youtube_url: str
    youtube_video_id: str
    artista: str
    musica: str
    compositor: Optional[str] = None
    opera: Optional[str] = None
    categoria: Optional[str] = None
    idioma: str
    eh_instrumental: bool
    sem_lyrics: Optional[bool] = False
    duracao_total_sec: Optional[float] = None
    status: str
    passo_atual: int
    erro_msg: Optional[str] = None
    janela_inicio_sec: Optional[float] = None
    janela_fim_sec: Optional[float] = None
    duracao_corte_sec: Optional[float] = None
    corte_original_inicio: Optional[str] = None
    corte_original_fim: Optional[str] = None
    arquivo_audio_completo: Optional[str] = None
    arquivo_video_completo: Optional[str] = None
    arquivo_video_cortado: Optional[str] = None
    rota_alinhamento: Optional[str] = None
    confianca_alinhamento: Optional[float] = None
    r2_base: Optional[str] = None
    notas_revisao: Optional[str] = None
    task_heartbeat: Optional[datetime] = None
    progresso_detalhe: Optional[Any] = None
    tentativas_requeue: int = 0
    perfil_id: Optional[int] = None
    perfil_nome: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- Letra ---
class LetraCreate(BaseModel):
    musica: str
    compositor: Optional[str] = None
    opera: Optional[str] = None
    idioma: str
    letra: str
    fonte: Optional[str] = "manual"


class LetraUpdate(BaseModel):
    letra: Optional[str] = None
    fonte: Optional[str] = None
    validado_por: Optional[str] = None


class LetraOut(BaseModel):
    id: int
    musica: str
    compositor: Optional[str] = None
    opera: Optional[str] = None
    idioma: str
    letra: str
    fonte: Optional[str] = None
    vezes_utilizada: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- Alinhamento ---
class AlinhamentoOut(BaseModel):
    id: int
    edicao_id: int
    segmentos_completo: list
    segmentos_cortado: Optional[list] = None
    confianca_media: Optional[float] = None
    rota: Optional[str] = None
    validado: bool

    class Config:
        from_attributes = True


class AlinhamentoValidar(BaseModel):
    segmentos: list
    validado_por: Optional[str] = "operador"


class LetraAprovar(BaseModel):
    letra: str
    fonte: Optional[str] = "manual"
    validado_por: Optional[str] = "operador"


# --- Report ---
class ReportCreate(BaseModel):
    edicao_id: Optional[int] = None
    projeto_id: Optional[int] = None
    colaborador: str = ""
    tipo: str  # "bug", "melhoria", "sugestao", "qualidade", "outro"
    titulo: str
    descricao: Optional[str] = None
    prioridade: Optional[str] = "media"


class ReportUpdate(BaseModel):
    status: Optional[str] = None
    prioridade: Optional[str] = None
    descricao: Optional[str] = None
    resolucao: Optional[str] = None
    resolvido_por: Optional[str] = None
    codigo_err: Optional[str] = None


class ReportOut(BaseModel):
    id: int
    colaborador: str = ""
    titulo: str
    descricao: Optional[str] = None
    tipo: str
    prioridade: str
    status: str
    projeto_id: Optional[int] = None
    screenshots: list[str] = []
    resolucao: Optional[str] = None
    resolvido_por: Optional[str] = None
    codigo_err: Optional[str] = None
    created_at: Optional[datetime] = None
