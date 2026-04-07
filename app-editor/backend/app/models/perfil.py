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
    sem_lyrics_default = Column(Boolean, default=False, nullable=False, server_default="false")

    # Identidade
    identity_prompt = Column(Text)
    tom_de_voz = Column(Text)
    editorial_lang = Column(String(5), default="pt")
    hashtags_fixas = Column(JSON, default=list)
    categorias_hook = Column(JSON, default=list)

    # Idiomas
    idiomas_alvo = Column(JSON, default=lambda: ["en", "pt", "es", "de", "fr", "it", "pl"])
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
    overlay_interval_secs = Column(Integer, default=6)  # intervalo entre legendas overlay

    # Video — prever dimensões futuras, só implementar 9:16 agora
    video_width = Column(Integer, default=1080)
    video_height = Column(Integer, default=1920)

    # Curadoria — metadados básicos
    escopo_conteudo = Column(Text)

    # Curadoria — dados migrados do JSON avulso (best-of-opera.json)
    curadoria_categories = Column(JSON, default=dict)    # categorias + seeds de busca
    elite_hits = Column(JSON, default=list)              # músicas mais populares
    power_names = Column(JSON, default=list)             # cantores destaque
    voice_keywords = Column(JSON, default=list)          # palavras-chave de voz
    institutional_channels = Column(JSON, default=list)  # canais institucionais
    category_specialty = Column(JSON, default=dict)      # especialidades por categoria
    scoring_weights = Column(JSON, default=dict)         # pesos do scoring V7
    curadoria_filters = Column(JSON, default=dict)       # filtros (duracao_max, etc)
    anti_spam_terms = Column(String(500), default="-karaoke -piano -tutorial -lesson -reaction -review -lyrics -chords")
    playlist_id = Column(String(100), default="")

    # Redator
    hook_categories_redator = Column(JSON, default=dict)
    identity_prompt_redator = Column(Text)
    tom_de_voz_redator = Column(Text)
    custom_post_structure = Column(Text)  # estrutura de post customizável por marca
    brand_opening_line = Column(Text)  # frase de abertura do prompt (substitui hardcoded)
    hashtag_count = Column(Integer)  # quantidade de hashtags por marca (default 4)
    logo_url = Column(String(500))
    font_name = Column(String(100))
    font_file_r2_key = Column(String(200))
    overlay_cta = Column(Text)  # Texto do CTA em PT-BR, traduzido automaticamente junto com overlay

    # Visual
    cor_primaria = Column(String(10), default="#1a1a2e")
    cor_secundaria = Column(String(10), default="#e94560")

    # R2 — prefixo para isolar storage entre marcas
    r2_prefix = Column(String(100), default="editor")

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
