"""Modelo: editor_traducoes_letra."""
from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, func

from app.database import Base


class TraducaoLetra(Base):
    __tablename__ = "editor_traducoes_letra"

    id = Column(Integer, primary_key=True, index=True)
    edicao_id = Column(Integer, ForeignKey("editor_edicoes.id", ondelete="CASCADE"), nullable=False, index=True)
    idioma = Column(String(10), nullable=False)
    segmentos = Column(JSON, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
