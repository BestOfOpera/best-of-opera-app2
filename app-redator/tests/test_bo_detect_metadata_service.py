"""Tests para bo_detect_metadata_service — validate_enums + dim_3 consistência."""
from __future__ import annotations

import pytest

from backend.services.bo.bo_detect_metadata_service import (
    DetectMetadataError,
    _verify_model_columns_exist,
    validate_enums,
)
from backend.services.bo.prompts.bo_detect_metadata_prompt_v1 import (
    DIMENSAO_1_FORMACAO,
    DIMENSAO_2_TIPO_VOCAL,
    DIMENSAO_3_PAIS,
    DIMENSAO_3_SUBCATEGORIAS,
)


def test_valida_enum_dim_1_aceita_valido():
    """Cada item de DIMENSAO_1_FORMACAO deve passar validação."""
    for valor in DIMENSAO_1_FORMACAO:
        validate_enums({"classificacao": {"dimensao_1_formacao": valor}})


def test_valida_enum_dim_1_rejeita_invalido():
    with pytest.raises(DetectMetadataError, match="dim_1 enum inválido"):
        validate_enums({"classificacao": {"dimensao_1_formacao": "valor_inventado"}})


def test_valida_enum_dim_2_aceita_nao_aplicavel():
    """V-I-23: 'nao_aplicavel' deve ser aceito para Dimensão 2 (peça instrumental)."""
    assert "nao_aplicavel" in DIMENSAO_2_TIPO_VOCAL  # garantia da listagem
    validate_enums({"classificacao": {"dimensao_2_tipo_vocal": "nao_aplicavel"}})


def test_valida_enum_dim_2_aceita_soprano():
    assert "soprano" in DIMENSAO_2_TIPO_VOCAL
    validate_enums({"classificacao": {"dimensao_2_tipo_vocal": "soprano"}})


def test_valida_enum_dim_2_rejeita_invalido():
    with pytest.raises(DetectMetadataError, match="dim_2 enum inválido"):
        validate_enums({"classificacao": {"dimensao_2_tipo_vocal": "voz_inventada"}})


def test_subcategoria_dim_3_consistente_com_pai():
    """dim_3_sub deve estar em DIMENSAO_3_SUBCATEGORIAS[dim_3_pai]."""
    pai = next(iter(DIMENSAO_3_PAIS))  # primeiro pai
    subs = DIMENSAO_3_SUBCATEGORIAS.get(pai, [])
    if subs:
        validate_enums({
            "classificacao": {
                "dimensao_3_pai": pai,
                "dimensao_3_sub": subs[0],
            }
        })


def test_subcategoria_dim_3_inconsistente_com_pai_levanta():
    """sub_X com pai_Y onde sub_X não é filha de pai_Y → erro."""
    pais = list(DIMENSAO_3_PAIS)
    if len(pais) >= 2:
        pai_a = pais[0]
        # Pega sub de outro pai
        sub_de_outro_pai = None
        for p in pais[1:]:
            for s in DIMENSAO_3_SUBCATEGORIAS.get(p, []):
                # Garante que essa sub não é também filha de pai_a
                if s not in DIMENSAO_3_SUBCATEGORIAS.get(pai_a, []):
                    sub_de_outro_pai = s
                    break
            if sub_de_outro_pai:
                break

        if sub_de_outro_pai:
            with pytest.raises(DetectMetadataError, match="dim_3_sub"):
                validate_enums({
                    "classificacao": {
                        "dimensao_3_pai": pai_a,
                        "dimensao_3_sub": sub_de_outro_pai,
                    }
                })


def test_validate_enums_aceita_classificacao_parcial():
    """Campos None/ausentes devem ser tolerados."""
    validate_enums({"classificacao": {"dimensao_1_formacao": DIMENSAO_1_FORMACAO[0]}})
    validate_enums({"classificacao": {}})


def test_validate_enums_rejeita_classificacao_nao_dict():
    with pytest.raises(DetectMetadataError, match="classificacao.tipo"):
        validate_enums({"classificacao": "string"})


def test_smoke_5_colunas_dim_existem_no_model():
    """Sanity check anti-typo: 5 colunas dim_*_detectada existem no Project."""
    _verify_model_columns_exist()  # levanta AssertionError se faltar
