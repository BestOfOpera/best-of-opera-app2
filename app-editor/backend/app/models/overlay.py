"""Modelo: editor_overlays — overlays do Redator."""
from sqlalchemy import Column, Integer, String, DateTime, JSON, func

from app.database import Base


class Overlay(Base):
    __tablename__ = "editor_overlays"

    id = Column(Integer, primary_key=True, index=True)
    edicao_id = Column(Integer, nullable=False, index=True)
    idioma = Column(String(10), nullable=False)
    segmentos_original = Column(JSON, nullable=False)
    segmentos_reindexado = Column(JSON)
    created_at = Column(DateTime, server_default=func.now())
