"""Helpers de Perfil sem dependências de autenticação.

Isolado para permitir import em testes sem precisar de python-jose.
"""
import logging
from app.models.perfil import Perfil

_logger = logging.getLogger(__name__)


def build_curadoria_config(perfil: Perfil) -> dict:
    """Monta o payload de config de curadoria no formato que a curadoria espera."""
    return {
        "name": perfil.nome,
        "project_id": perfil.slug,
        "categories": perfil.curadoria_categories or {},
        "elite_hits": perfil.elite_hits or [],
        "power_names": perfil.power_names or [],
        "voice_keywords": perfil.voice_keywords or [],
        "institutional_channels": perfil.institutional_channels or [],
        "category_specialty": perfil.category_specialty or {},
        "scoring_weights": perfil.scoring_weights or {},
        "filters": perfil.curadoria_filters or {},
        "anti_spam": perfil.anti_spam_terms or "",
        "playlist_id": perfil.playlist_id or "",
        "r2_prefix": perfil.r2_prefix or "",
    }


def build_redator_config(perfil: Perfil) -> dict:
    """Monta o payload de config do redator no formato que o app-redator espera."""
    result = {
        "brand_name": perfil.nome,
        "brand_slug": perfil.slug,
        "identity_prompt": perfil.identity_prompt or "",
        "identity_prompt_redator": perfil.identity_prompt_redator or "",
        "tom_de_voz": perfil.tom_de_voz or "",
        "tom_de_voz_redator": perfil.tom_de_voz_redator or "",
        "editorial_lang": perfil.editorial_lang or "pt",
        "hashtags_fixas": perfil.hashtags_fixas or [],
        "categorias_hook": perfil.categorias_hook or [],
        "hook_categories_redator": perfil.hook_categories_redator or {},
        "escopo_conteudo": perfil.escopo_conteudo or "",
        "overlay_max_chars": perfil.overlay_max_chars or 70,
        "overlay_max_chars_linha": perfil.overlay_max_chars_linha or 35,
        "overlay_interval_secs": perfil.overlay_interval_secs or 6,
        "custom_post_structure": perfil.custom_post_structure or "",
        "brand_opening_line": perfil.brand_opening_line or "",
        "hashtag_count": perfil.hashtag_count or 4,
        "r2_prefix": perfil.r2_prefix or "",
        "overlay_cta": perfil.overlay_cta or "",
    }
    _defaults = {
        "overlay_max_chars": 70, "overlay_max_chars_linha": 35,
        "overlay_interval_secs": 6, "hashtag_count": 4,
    }
    _used = [k for k, v in _defaults.items() if not getattr(perfil, k, None)]
    if _used:
        _logger.info(f"[PERFIL] {perfil.slug}: fallback em {', '.join(_used)}")
    return result
