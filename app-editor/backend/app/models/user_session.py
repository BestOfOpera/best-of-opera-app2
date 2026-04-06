"""Modelo: editor_user_sessions — sessões de uso para tracking de tempo ativo."""
from sqlalchemy import Column, Integer, DateTime, ForeignKey, func

from app.database import Base


class UserSession(Base):
    __tablename__ = "editor_user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("editor_usuarios.id"), nullable=False, index=True)
    started_at = Column(DateTime, nullable=False, server_default=func.now())
    last_seen_at = Column(DateTime, nullable=False, server_default=func.now())
    duration_minutes = Column(Integer, default=0)
