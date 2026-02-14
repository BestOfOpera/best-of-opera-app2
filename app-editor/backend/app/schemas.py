"""Pydantic schemas para a API."""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


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
    duracao_total_sec: Optional[float] = None
    status: str
    passo_atual: int
    erro_msg: Optional[str] = None
    janela_inicio_sec: Optional[float] = None
    janela_fim_sec: Optional[float] = None
    duracao_corte_sec: Optional[float] = None
    rota_alinhamento: Optional[str] = None
    confianca_alinhamento: Optional[float] = None
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
