"""
BO CTAs — Fonte Única dos Textos de Call-to-Action
==================================================
Tabela canônica dos CTAs do overlay BO nos 7 idiomas. Consumida por:
- bo_overlay_prompt_v1.py (CTA em PT — inserido como última legenda)
- bo_translation_prompt_v1.py (CTAs em EN/ES/DE/FR/IT/PL — substituição pós-LLM)
- translate_service.py (runtime — injeção após tradução)

REGRA: este módulo é a ÚNICA fonte. Qualquer alteração aqui propaga. Jamais
duplicar valores hardcoded em outros arquivos.

Formato: tupla (linha_1, linha_2). Cada linha ≤ 38 caracteres (validado).
"""


BO_CTAS_OVERLAY: dict[str, tuple[str, str]] = {
    "pt": ("Siga, o melhor da arte vocal,", "diariamente no seu feed"),
    "en": ("Follow for the best of vocal art,", "daily on your feed"),
    "es": ("Síguenos para lo mejor del arte", "vocal, diariamente en tu feed"),
    "de": ("Folge uns für das Beste der", "Gesangskunst, täglich im Feed"),
    "fr": ("Suis-nous pour le meilleur de", "l'art vocal, chaque jour"),
    "it": ("Seguici per il meglio dell'arte", "vocale, ogni giorno nel tuo feed"),
    "pl": ("Obserwuj nas, by poznać to,", "co najlepsze w sztuce wokalnej"),
}


def get_cta_overlay(language: str) -> tuple[str, str]:
    """
    Retorna (linha_1, linha_2) do CTA do overlay para o idioma dado.
    Levanta KeyError se idioma não suportado.
    """
    if language not in BO_CTAS_OVERLAY:
        raise KeyError(
            f"Idioma '{language}' não suportado. "
            f"Idiomas disponíveis: {list(BO_CTAS_OVERLAY.keys())}"
        )
    return BO_CTAS_OVERLAY[language]


def get_cta_overlay_formatted(language: str) -> str:
    """
    Retorna CTA formatado como string única "linha_1\\nlinha_2".
    Usado para inserção direta em overlay_json como text_full do CTA.
    """
    l1, l2 = get_cta_overlay(language)
    return f"{l1}\n{l2}"


# Validação em import time — linha máxima 38c
def _validate_ctas():
    for lang, (l1, l2) in BO_CTAS_OVERLAY.items():
        if len(l1) > 38:
            raise ValueError(
                f"CTA '{lang}' linha 1 tem {len(l1)}c > 38c: {l1!r}"
            )
        if len(l2) > 38:
            raise ValueError(
                f"CTA '{lang}' linha 2 tem {len(l2)}c > 38c: {l2!r}"
            )


_validate_ctas()
