"""Modelo: editor_renders — vídeos renderizados."""
from sqlalchemy import Column, Integer, String, BigInteger, Text, DateTime, ForeignKey, func

from app.database import Base


class Render(Base):
    __tablename__ = "editor_renders"

    id = Column(Integer, primary_key=True, index=True)
    edicao_id = Column(Integer, ForeignKey("editor_edicoes.id", ondelete="CASCADE"), nullable=False, index=True)
    idioma = Column(String(10), nullable=False)
    tipo = Column(String(20), nullable=False)
    arquivo = Column(String(500))
    tamanho_bytes = Column(BigInteger)
    status = Column(String(20), default="pendente")
    erro_msg = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
