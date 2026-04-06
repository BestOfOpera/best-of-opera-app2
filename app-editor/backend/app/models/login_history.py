"""Modelo: editor_login_history — histórico de logins."""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func

from app.database import Base


class LoginHistory(Base):
    __tablename__ = "editor_login_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("editor_usuarios.id"), nullable=False, index=True)
    timestamp = Column(DateTime, server_default=func.now(), nullable=False)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
