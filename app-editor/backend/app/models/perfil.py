"""Modelo Perfil — configuração de cada marca (multi-brand)."""
from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, JSON, func

from app.database import Base


class Perfil(Base):
    __tablename__ = "editor_perfis"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), unique=True, nullable=False)       # "Best of Opera"
    sigla = Column(String(5), nullable=False)                     # "BO"
    slug = Column(String(50), unique=True, nullable=False)        # "best-of-opera"
    ativo = Column(Boolean, default=True)

    # Identidade
    identity_prompt = Column(Text)
    tom_de_voz = Column(Text)
    editorial_lang = Column(String(5), default="pt")
    hashtags_fixas = Column(JSON, default=list)
    categorias_hook = Column(JSON, default=list)

    # Idiomas
    idiomas_alvo = Column(JSON, default=list)
    idioma_preview = Column(String(5), default="pt")

    # Estilos de legenda — JSON (mesma estrutura do ESTILOS_PADRAO)
    overlay_style = Column(JSON, default=dict)
    lyrics_style = Column(JSON, default=dict)
    traducao_style = Column(JSON, default=dict)

    # Limites de caracteres
    overlay_max_chars = Column(Integer, default=70)
    overlay_max_chars_linha = Column(Integer, default=35)
    lyrics_max_chars = Column(Integer, default=43)
    traducao_max_chars = Column(Integer, default=100)

    # Video — prever dimensões futuras, só implementar 9:16 agora
    video_width = Column(Integer, default=1080)
    video_height = Column(Integer, default=1920)

    # Curadoria
    escopo_conteudo = Column(Text)
    duracao_corte_min = Column(Integer, default=30)
    duracao_corte_max = Column(Integer, default=90)

    # Visual
    cor_primaria = Column(String(10), default="#1a1a2e")
    cor_secundaria = Column(String(10), default="#e94560")

    # R2 — prefixo para isolar storage entre marcas
    r2_prefix = Column(String(100), default="editor")

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
