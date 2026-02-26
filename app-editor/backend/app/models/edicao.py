"""Modelo principal: editor_edicoes."""
from sqlalchemy import Column, Integer, String, Float, Boolean, Text, DateTime, func
from sqlalchemy import JSON

from app.database import Base


class Edicao(Base):
    __tablename__ = "editor_edicoes"

    id = Column(Integer, primary_key=True, index=True)
    curadoria_video_id = Column(Integer, nullable=True)
    youtube_url = Column(String(500), nullable=False)
    youtube_video_id = Column(String(20), nullable=False)

    artista = Column(String(300), nullable=False)
    musica = Column(String(300), nullable=False)
    compositor = Column(String(300))
    opera = Column(String(300))
    categoria = Column(String(50))
    idioma = Column(String(10), nullable=False)
    eh_instrumental = Column(Boolean, default=False)
    duracao_total_sec = Column(Float)

    status = Column(String(30), default="aguardando")
    passo_atual = Column(Integer, default=1)
    erro_msg = Column(Text)

    janela_inicio_sec = Column(Float)
    janela_fim_sec = Column(Float)
    duracao_corte_sec = Column(Float)

    corte_original_inicio = Column(String(20))
    corte_original_fim = Column(String(20))

    arquivo_video_completo = Column(String(500))
    arquivo_video_cortado = Column(String(500))
    arquivo_audio_completo = Column(String(500))
    arquivo_video_cru = Column(String(500))

    rota_alinhamento = Column(String(5))
    confianca_alinhamento = Column(Float)

    r2_base = Column(String(500), nullable=True)  # ex: "Pavarotti - Nessun Dorma"
    redator_project_id = Column(Integer, nullable=True)
    notas_revisao = Column(Text, nullable=True)

    editado_por = Column(String(100))
    tempo_edicao_seg = Column(Integer)

    task_heartbeat = Column(DateTime, nullable=True)
    progresso_detalhe = Column(JSON, default=dict)
    tentativas_requeue = Column(Integer, default=0)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
