"""Modelo: editor_reports — reports de bugs e qualidade."""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func

from app.database import Base


class Report(Base):
    __tablename__ = "editor_reports"

    id = Column(Integer, primary_key=True, index=True)
    edicao_id = Column(Integer, ForeignKey("editor_edicoes.id", ondelete="SET NULL"), nullable=True, index=True)
    tipo = Column(String(50), nullable=False)  # "bug", "qualidade", "audio", "legenda", "outro"
    titulo = Column(String(300), nullable=False)
    descricao = Column(Text, nullable=True)
    screenshot_r2_key = Column(String(500), nullable=True)  # key R2 do screenshot
    status = Column(String(20), default="aberto")  # "aberto", "em_analise", "resolvido", "ignorado"
    prioridade = Column(String(20), default="media")  # "baixa", "media", "alta", "critica"
    resolvido_em = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
