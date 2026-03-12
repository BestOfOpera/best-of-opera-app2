"""Modelo Usuario — autenticação e controle de acesso."""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, func
from app.database import Base


class Usuario(Base):
    __tablename__ = "editor_usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False)
    email = Column(String(200), unique=True, nullable=False, index=True)
    senha_hash = Column(String(500), nullable=False)
    role = Column(String(20), default="operador")  # "admin" ou "operador"
    ativo = Column(Boolean, default=True)
    must_change_password = Column(Boolean, default=True)
    ultimo_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
