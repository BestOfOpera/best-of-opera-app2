"""Modelo: editor_seo — SEO YouTube do Redator."""
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey, func

from app.database import Base


class Seo(Base):
    __tablename__ = "editor_seo"

    id = Column(Integer, primary_key=True, index=True)
    edicao_id = Column(Integer, ForeignKey("editor_edicoes.id", ondelete="CASCADE"), nullable=False, index=True)
    idioma = Column(String(10), nullable=False)
    titulo = Column(String(300))
    descricao = Column(Text)
    tags = Column(JSON)
    category_id = Column(Integer, default=10)
    created_at = Column(DateTime, server_default=func.now())
