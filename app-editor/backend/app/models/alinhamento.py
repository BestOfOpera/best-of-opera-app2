"""Modelo: editor_alinhamentos — alinhamento lyrics × timestamps."""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, JSON, func

from app.database import Base


class Alinhamento(Base):
    __tablename__ = "editor_alinhamentos"

    id = Column(Integer, primary_key=True, index=True)
    edicao_id = Column(Integer, nullable=False, index=True)
    letra_id = Column(Integer)
    segmentos_completo = Column(JSON, nullable=False)
    segmentos_cortado = Column(JSON)
    confianca_media = Column(Float)
    rota = Column(String(5))
    validado = Column(Boolean, default=False)
    validado_por = Column(String(100))
    created_at = Column(DateTime, server_default=func.now())
