"""Modelo: editor_posts — posts do Redator."""
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, func

from app.database import Base


class Post(Base):
    __tablename__ = "editor_posts"

    id = Column(Integer, primary_key=True, index=True)
    edicao_id = Column(Integer, nullable=False, index=True)
    idioma = Column(String(10), nullable=False)
    texto = Column(Text, nullable=False)
    hashtags = Column(JSON)
    created_at = Column(DateTime, server_default=func.now())
