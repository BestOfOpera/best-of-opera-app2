"""Modelo: editor_letras — banco de letras reutilizável."""
from sqlalchemy import Column, Integer, String, Text, DateTime, func

from app.database import Base


class Letra(Base):
    __tablename__ = "editor_letras"

    id = Column(Integer, primary_key=True, index=True)
    musica = Column(String(300), nullable=False)
    compositor = Column(String(300))
    opera = Column(String(300))
    idioma = Column(String(10), nullable=False)
    letra = Column(Text, nullable=False)
    fonte = Column(String(50))
    validado_por = Column(String(100))
    validado_em = Column(DateTime)
    vezes_utilizada = Column(Integer, default=1)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
