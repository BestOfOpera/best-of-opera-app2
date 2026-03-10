from pydantic import BaseModel
from typing import Any


class PerfilCuradoria(BaseModel):
    """Modelo de configuração por marca. Fase 2: ler do banco por perfil_id."""
    name: str
    project_id: str
    categories: dict[str, Any]
    elite_hits: list[str]
    power_names: list[str]
    voice_keywords: list[str]
    institutional_channels: list[str]
    category_specialty: dict[str, list[str]]
    scoring_weights: dict[str, Any]
    filters: dict[str, Any]
