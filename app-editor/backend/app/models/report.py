"""Modelo: editor_reports — reports de bugs e qualidade."""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func

from app.database import Base


class Report(Base):
    __tablename__ = "editor_reports"

    id = Column(Integer, primary_key=True, index=True)
    # Campos originais
    edicao_id = Column(Integer, ForeignKey("editor_edicoes.id", ondelete="SET NULL"), nullable=True, index=True)
    tipo = Column(String(50), nullable=False)  # "bug", "melhoria", "sugestao", "qualidade", "outro"
    titulo = Column(String(300), nullable=False)
    descricao = Column(Text, nullable=True)
    screenshot_r2_key = Column(String(500), nullable=True)  # key R2 do screenshot (legado)
    status = Column(String(20), default="novo")  # "novo", "analise", "resolvido"
    prioridade = Column(String(20), default="media")  # "baixa", "media", "alta"
    resolvido_em = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    # Campos novos
    colaborador = Column(String(200), nullable=True)  # nome de quem reportou
    projeto_id = Column(Integer, nullable=True)  # id do projeto (redator)
    screenshots_json = Column(Text, nullable=True)  # JSON array de R2 keys
    resolucao = Column(Text, nullable=True)  # texto de resolução
    resolvido_por = Column(String(200), nullable=True)  # nome de quem resolveu
    codigo_err = Column(String(50), nullable=True)  # ex: ERR-066
