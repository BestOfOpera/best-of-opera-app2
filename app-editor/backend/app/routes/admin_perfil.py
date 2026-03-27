"""Admin CRUD de Perfis de Marca — Best of Opera Editor."""
import json
import logging
import os
import re
import tempfile
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.auth import require_admin
from app.models.perfil import Perfil
from app.models.edicao import Edicao
from app.models.report import Report
from app.services.perfil_service import build_curadoria_config, build_redator_config
from shared.storage_service import storage

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/editor/admin/perfis",
    tags=["admin-perfis"],
    dependencies=[Depends(require_admin)],
)

# -- Defaults ------------------------------------------------------------------

IDIOMAS_PADRAO = ["en", "pt", "es", "de", "fr", "it", "pl"]

ESTILOS_PADRAO = {
    "overlay": {
        "fontname": "TeX Gyre Schola", "fontsize": 44,
        "primarycolor": "#FFFFFF", "outlinecolor": "#000000",
        "outline": 0, "shadow": 0, "alignment": 2, "marginv": 1296,
        "bold": True, "italic": True,
    },
    "lyrics": {
        "fontname": "TeX Gyre Schola", "fontsize": 40,
        "primarycolor": "#E4F042", "outlinecolor": "#000000",
        "outline": 0, "shadow": 0, "alignment": 2, "marginv": 573,
        "bold": True, "italic": True,
    },
    "traducao": {
        "fontname": "TeX Gyre Schola", "fontsize": 40,
        "primarycolor": "#FFFFFF", "outlinecolor": "#000000",
        "outline": 0, "shadow": 0, "alignment": 8, "marginv": 1353,
        "bold": True, "italic": True,
    },
}


def _slugify(texto: str) -> str:
    """Converte texto para slug URL-safe."""
    slug = texto.lower().strip()
    slug = re.sub(r"[àáâãäå]", "a", slug)
    slug = re.sub(r"[èéêë]", "e", slug)
    slug = re.sub(r"[ìíîï]", "i", slug)
    slug = re.sub(r"[òóôõö]", "o", slug)
    slug = re.sub(r"[ùúûü]", "u", slug)
    slug = re.sub(r"[ç]", "c", slug)
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug


def _hex_valido(cor: str) -> bool:
    return bool(re.match(r"^#[0-9A-Fa-f]{6}$", cor))


def _idiomas_validos(idiomas: List[str]) -> bool:
    return all(len(i) == 2 and i.isalpha() for i in idiomas)


# -- Schemas inline ------------------------------------------------------------

class PerfilListItem(BaseModel):
    id: int
    nome: str
    sigla: str
    slug: str
    ativo: bool
    sem_lyrics_default: bool = False
    idiomas_alvo: Optional[List[str]] = None
    cor_primaria: str
    cor_secundaria: str
    r2_prefix: str = ""
    created_at: Optional[Any] = None
    total_edicoes: int = 0

    class Config:
        from_attributes = True


class PerfilStats(BaseModel):
    total_edicoes: int
    concluidas: int
    em_andamento: int
    em_erro: int


class PerfilDetalheOut(BaseModel):
    id: int
    nome: str
    sigla: str
    slug: str
    ativo: bool
    sem_lyrics_default: bool = False
    identity_prompt: Optional[str] = None
    tom_de_voz: Optional[str] = None
    editorial_lang: str
    hashtags_fixas: Optional[List[str]] = None
    categorias_hook: Optional[List[str]] = None
    idiomas_alvo: Optional[List[str]] = None
    idioma_preview: str
    overlay_style: Optional[Dict[str, Any]] = None
    lyrics_style: Optional[Dict[str, Any]] = None
    traducao_style: Optional[Dict[str, Any]] = None
    overlay_max_chars: int
    overlay_max_chars_linha: int
    lyrics_max_chars: int
    traducao_max_chars: int
    overlay_interval_secs: Optional[int] = 6
    video_width: int
    video_height: int
    escopo_conteudo: Optional[str] = None
    cor_primaria: str
    cor_secundaria: str
    r2_prefix: str
    hook_categories_redator: Optional[Dict[str, Any]] = None
    identity_prompt_redator: Optional[str] = None
    tom_de_voz_redator: Optional[str] = None
    custom_post_structure: Optional[str] = None
    brand_opening_line: Optional[str] = None
    hashtag_count: Optional[int] = None
    logo_url: Optional[str] = None
    font_name: Optional[str] = None
    font_file_r2_key: Optional[str] = None
    # Curadoria
    curadoria_categories: Optional[Dict[str, Any]] = None
    elite_hits: Optional[List[Any]] = None
    power_names: Optional[List[Any]] = None
    voice_keywords: Optional[List[Any]] = None
    institutional_channels: Optional[List[Any]] = None
    category_specialty: Optional[Dict[str, Any]] = None
    scoring_weights: Optional[Dict[str, Any]] = None
    curadoria_filters: Optional[Dict[str, Any]] = None
    anti_spam_terms: Optional[str] = None
    playlist_id: Optional[str] = None
    created_at: Optional[Any] = None
    updated_at: Optional[Any] = None
    stats: Optional[PerfilStats] = None

    class Config:
        from_attributes = True


class PerfilPreviewLegenda(BaseModel):
    overlay_style: Optional[Dict[str, Any]] = None
    lyrics_style: Optional[Dict[str, Any]] = None
    traducao_style: Optional[Dict[str, Any]] = None
    overlay_max_chars: int
    overlay_max_chars_linha: int
    lyrics_max_chars: int
    traducao_max_chars: int
    video_width: int
    video_height: int


# -- Helpers -------------------------------------------------------------------

def _get_stats(perfil_id: int, db: Session) -> PerfilStats:
    total = db.query(func.count(Edicao.id)).filter(Edicao.perfil_id == perfil_id).scalar() or 0
    concluidas = db.query(func.count(Edicao.id)).filter(
        Edicao.perfil_id == perfil_id, Edicao.status == "concluido"
    ).scalar() or 0
    em_erro = db.query(func.count(Edicao.id)).filter(
        Edicao.perfil_id == perfil_id, Edicao.status == "erro"
    ).scalar() or 0
    em_andamento = total - concluidas - em_erro
    return PerfilStats(
        total_edicoes=total, concluidas=concluidas,
        em_andamento=em_andamento, em_erro=em_erro,
    )


CAMPOS_OBRIGATORIOS_MARCA = ["identity_prompt_redator", "tom_de_voz_redator", "escopo_conteudo"]


def _validar_campos_marca(dados: dict) -> list:
    """Valida campos obrigatórios de marca. Retorna lista de warnings."""
    faltando = [c for c in CAMPOS_OBRIGATORIOS_MARCA if not (dados.get(c) or "").strip()]
    if faltando:
        raise HTTPException(
            422,
            detail=f"Campos obrigatórios não preenchidos: {', '.join(faltando)}"
        )
    warnings = []
    if not (dados.get("custom_post_structure") or "").strip():
        warnings.append("custom_post_structure não definido — posts usarão estrutura genérica")
    return warnings


def _validar_campos(data: dict) -> None:
    if "cor_primaria" in data and data["cor_primaria"] and not _hex_valido(data["cor_primaria"]):
        raise HTTPException(status_code=422, detail="cor_primaria deve ser hex #RRGGBB")
    if "cor_secundaria" in data and data["cor_secundaria"] and not _hex_valido(data["cor_secundaria"]):
        raise HTTPException(status_code=422, detail="cor_secundaria deve ser hex #RRGGBB")
    if "idiomas_alvo" in data and data["idiomas_alvo"] and not _idiomas_validos(data["idiomas_alvo"]):
        raise HTTPException(status_code=422, detail="idiomas_alvo deve conter codigos de 2 letras")


def _protegido(perfil: Perfil, force: bool = False) -> None:
    if perfil.sigla == "BO" and not force:
        raise HTTPException(
            status_code=403,
            detail="Perfil 'Best of Opera' (BO) e protegido. Use ?force=true para confirmar a alteracao.",
        )


# -- Rotas ---------------------------------------------------------------------

@router.get("/", response_model=List[PerfilListItem])
def listar_perfis(db: Session = Depends(get_db)):
    """Lista todos os perfis ordenados por nome, com contagem de edicoes."""
    perfis = db.query(Perfil).order_by(Perfil.nome).all()
    resultado = []
    for p in perfis:
        total = db.query(func.count(Edicao.id)).filter(Edicao.perfil_id == p.id).scalar() or 0
        item = PerfilListItem(
            id=p.id, nome=p.nome, sigla=p.sigla, slug=p.slug, ativo=p.ativo,
            sem_lyrics_default=p.sem_lyrics_default,
            idiomas_alvo=p.idiomas_alvo, cor_primaria=p.cor_primaria,
            cor_secundaria=p.cor_secundaria, r2_prefix=p.r2_prefix or "",
            created_at=p.created_at, total_edicoes=total,
        )
        resultado.append(item)
    return resultado


@router.get("/template-bo", response_model=PerfilDetalheOut)
def template_bo(db: Session = Depends(get_db)):
    """Retorna todos os valores do perfil BO como template para pré-preencher nova marca."""
    perfil = db.query(Perfil).filter(Perfil.sigla == "BO").first()
    if not perfil:
        raise HTTPException(status_code=404, detail="Perfil BO nao encontrado")

    stats = _get_stats(perfil.id, db)
    dados = {c.name: getattr(perfil, c.name) for c in perfil.__table__.columns}
    dados["stats"] = stats
    return PerfilDetalheOut(**dados)


@router.post("/{perfil_id}/upload-font", response_model=PerfilDetalheOut)
def upload_font(perfil_id: int, file: UploadFile = File(...), db: Session = Depends(get_db), force: bool = False):
    """Faz upload de fonte .ttf/.otf para o R2 e atualiza font_name e font_file_r2_key do perfil."""
    from app.services.font_service import extract_font_family, upload_font_to_r2

    perfil = db.query(Perfil).filter(Perfil.id == perfil_id).first()
    if not perfil:
        raise HTTPException(status_code=404, detail="Perfil nao encontrado")

    _protegido(perfil, force=force)

    # Validar extensão
    filename = file.filename or ""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in (".ttf", ".otf"):
        raise HTTPException(status_code=422, detail="Apenas arquivos .ttf e .otf sao aceitos")

    # Ler e verificar tamanho (max 10MB)
    content = file.file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=422, detail="Arquivo de fonte excede o limite de 10MB")

    # Salvar em tmp, extrair family name, fazer upload
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        family_name = extract_font_family(tmp_path)
        r2_key = upload_font_to_r2(tmp_path, perfil.slug, filename)
    finally:
        os.unlink(tmp_path)

    perfil.font_name = family_name
    perfil.font_file_r2_key = r2_key

    # Propagar fontname para os 3 estilos de legenda (overlay, lyrics, tradução)
    # Nota: Column(JSON) sem MutableDict não rastreia mutação in-place — criar novo dict
    for attr in ("overlay_style", "lyrics_style", "traducao_style"):
        style_dict = getattr(perfil, attr, None)
        if style_dict and isinstance(style_dict, dict):
            setattr(perfil, attr, {**style_dict, "fontname": family_name})

    db.commit()
    db.refresh(perfil)

    logger.info(f"[admin-perfis] Fonte carregada: perfil={perfil.slug} family={family_name} key={r2_key}")
    stats = _get_stats(perfil_id, db)
    dados = {c.name: getattr(perfil, c.name) for c in perfil.__table__.columns}
    dados["stats"] = stats
    return PerfilDetalheOut(**dados)


@router.get("/{perfil_id}", response_model=PerfilDetalheOut)
def detalhar_perfil(perfil_id: int, db: Session = Depends(get_db)):
    """Detalhe completo de um perfil + stats."""
    perfil = db.query(Perfil).filter(Perfil.id == perfil_id).first()
    if not perfil:
        raise HTTPException(status_code=404, detail="Perfil nao encontrado")

    stats = _get_stats(perfil_id, db)
    dados = {c.name: getattr(perfil, c.name) for c in perfil.__table__.columns}
    dados["stats"] = stats
    return PerfilDetalheOut(**dados)


@router.post("/", response_model=PerfilDetalheOut, status_code=201)
def criar_perfil(body: dict, db: Session = Depends(get_db)):
    """Cria novo perfil. Slug gerado automaticamente se nao fornecido."""
    # Slug auto
    if not body.get("slug") and body.get("nome"):
        body["slug"] = _slugify(body["nome"])

    # Default idiomas_alvo
    if not body.get("idiomas_alvo"):
        body["idiomas_alvo"] = IDIOMAS_PADRAO[:]

    _validar_campos(body)
    marca_warnings = _validar_campos_marca(body)

    # Verificar unicidade
    for campo in ["nome", "sigla", "slug"]:
        if campo in body:
            existe = db.query(Perfil).filter(getattr(Perfil, campo) == body[campo]).first()
            if existe:
                raise HTTPException(status_code=409, detail=f"'{campo}' ja existe: {body[campo]}")

    # Defaults de estilo
    for track, chave in [("overlay_style", "overlay"), ("lyrics_style", "lyrics"), ("traducao_style", "traducao")]:
        if not body.get(track):
            body[track] = ESTILOS_PADRAO[chave]

    perfil = Perfil(**body)
    db.add(perfil)
    db.commit()
    db.refresh(perfil)

    logger.info(f"[admin-perfis] Perfil criado: {perfil.nome} (sigla={perfil.sigla})")
    stats = _get_stats(perfil.id, db)
    dados = {c.name: getattr(perfil, c.name) for c in perfil.__table__.columns}
    dados["stats"] = stats
    result = PerfilDetalheOut(**dados).model_dump()
    result["warnings"] = marca_warnings
    return result


@router.put("/{perfil_id}", response_model=PerfilDetalheOut)
def atualizar_perfil(perfil_id: int, body: dict, db: Session = Depends(get_db), force: bool = False):
    """Atualizacao completa do perfil."""
    perfil = db.query(Perfil).filter(Perfil.id == perfil_id).first()
    if not perfil:
        raise HTTPException(status_code=404, detail="Perfil nao encontrado")

    _protegido(perfil, force=force)
    _validar_campos(body)
    marca_warnings = _validar_campos_marca(body)

    for campo, valor in body.items():
        if hasattr(perfil, campo) and campo not in ("id", "created_at"):
            setattr(perfil, campo, valor)

    db.commit()
    db.refresh(perfil)

    stats = _get_stats(perfil_id, db)
    dados = {c.name: getattr(perfil, c.name) for c in perfil.__table__.columns}
    dados["stats"] = stats
    result = PerfilDetalheOut(**dados).model_dump()
    result["warnings"] = marca_warnings
    return result


@router.patch("/{perfil_id}", response_model=PerfilDetalheOut)
def atualizar_perfil_parcial(perfil_id: int, body: dict, db: Session = Depends(get_db), force: bool = False):
    """Atualizacao parcial do perfil."""
    perfil = db.query(Perfil).filter(Perfil.id == perfil_id).first()
    if not perfil:
        raise HTTPException(status_code=404, detail="Perfil nao encontrado")

    _protegido(perfil, force=force)
    _validar_campos(body)

    for campo, valor in body.items():
        if hasattr(perfil, campo) and campo not in ("id", "created_at"):
            setattr(perfil, campo, valor)

    db.commit()
    db.refresh(perfil)

    stats = _get_stats(perfil_id, db)
    dados = {c.name: getattr(perfil, c.name) for c in perfil.__table__.columns}
    dados["stats"] = stats
    return PerfilDetalheOut(**dados)


@router.post("/{perfil_id}/duplicar", response_model=PerfilDetalheOut, status_code=201)
def duplicar_perfil(perfil_id: int, db: Session = Depends(get_db)):
    """Duplica perfil como base para nova marca."""
    original = db.query(Perfil).filter(Perfil.id == perfil_id).first()
    if not original:
        raise HTTPException(status_code=404, detail="Perfil nao encontrado")

    novo_nome = f"{original.nome} (copia)"
    nova_sigla = f"{original.sigla}2"
    novo_slug = f"{original.slug}-copia"
    novo_r2 = f"{original.r2_prefix}-copia"

    # Garantir unicidade do slug/sigla
    sufixo = 1
    while db.query(Perfil).filter(Perfil.slug == novo_slug).first():
        sufixo += 1
        novo_slug = f"{original.slug}-copia{sufixo}"

    copia = Perfil(
        nome=novo_nome,
        sigla=nova_sigla,
        slug=novo_slug,
        ativo=original.ativo,
        identity_prompt=original.identity_prompt,
        tom_de_voz=original.tom_de_voz,
        editorial_lang=original.editorial_lang,
        hashtags_fixas=original.hashtags_fixas,
        categorias_hook=original.categorias_hook,
        idiomas_alvo=original.idiomas_alvo,
        idioma_preview=original.idioma_preview,
        overlay_style=original.overlay_style,
        lyrics_style=original.lyrics_style,
        traducao_style=original.traducao_style,
        overlay_max_chars=original.overlay_max_chars,
        overlay_max_chars_linha=original.overlay_max_chars_linha,
        lyrics_max_chars=original.lyrics_max_chars,
        traducao_max_chars=original.traducao_max_chars,
        overlay_interval_secs=original.overlay_interval_secs,
        video_width=original.video_width,
        video_height=original.video_height,
        escopo_conteudo=original.escopo_conteudo,
        cor_primaria=original.cor_primaria,
        cor_secundaria=original.cor_secundaria,
        r2_prefix=novo_r2,
        # Curadoria — copiar configurações da marca base
        curadoria_categories=original.curadoria_categories,
        elite_hits=original.elite_hits,
        power_names=original.power_names,
        voice_keywords=original.voice_keywords,
        institutional_channels=original.institutional_channels,
        category_specialty=original.category_specialty,
        scoring_weights=original.scoring_weights,
        curadoria_filters=original.curadoria_filters,
        anti_spam_terms=original.anti_spam_terms,
        playlist_id="",  # nova marca começa sem playlist própria
        # Redator
        hook_categories_redator=original.hook_categories_redator,
        identity_prompt_redator=original.identity_prompt_redator,
        tom_de_voz_redator=original.tom_de_voz_redator,
        custom_post_structure=original.custom_post_structure,
        brand_opening_line=original.brand_opening_line,
        hashtag_count=original.hashtag_count,
        logo_url=original.logo_url,
        font_name=original.font_name,
        font_file_r2_key=None,  # nova marca começa sem fonte carregada
    )
    db.add(copia)
    db.commit()
    db.refresh(copia)

    logger.info(f"[admin-perfis] Perfil duplicado: {original.nome} -> {copia.nome}")
    stats = _get_stats(copia.id, db)
    dados = {c.name: getattr(copia, c.name) for c in copia.__table__.columns}
    dados["stats"] = stats
    return PerfilDetalheOut(**dados)


@router.get("/{perfil_id}/preview-legenda", response_model=PerfilPreviewLegenda)
def preview_legenda(perfil_id: int, db: Session = Depends(get_db)):
    """Retorna estilos de legenda do perfil para preview visual."""
    perfil = db.query(Perfil).filter(Perfil.id == perfil_id).first()
    if not perfil:
        raise HTTPException(status_code=404, detail="Perfil nao encontrado")

    return PerfilPreviewLegenda(
        overlay_style=perfil.overlay_style,
        lyrics_style=perfil.lyrics_style,
        traducao_style=perfil.traducao_style,
        overlay_max_chars=perfil.overlay_max_chars,
        overlay_max_chars_linha=perfil.overlay_max_chars_linha,
        lyrics_max_chars=perfil.lyrics_max_chars,
        traducao_max_chars=perfil.traducao_max_chars,
        video_width=perfil.video_width,
        video_height=perfil.video_height,
    )


@router.get("/{perfil_id}/curadoria-config")
def curadoria_config_admin(perfil_id: int, db: Session = Depends(get_db)):
    """Retorna somente os campos de curadoria do perfil (uso admin)."""
    perfil = db.query(Perfil).filter(Perfil.id == perfil_id).first()
    if not perfil:
        raise HTTPException(status_code=404, detail="Perfil nao encontrado")

    return build_curadoria_config(perfil)


@router.delete("/{perfil_id}/edicoes")
def resetar_edicoes_perfil(perfil_id: int, db: Session = Depends(get_db), force: bool = False):
    """Deleta TODAS as edições de um perfil + arquivos R2. Irreversível."""
    perfil = db.query(Perfil).filter(Perfil.id == perfil_id).first()
    if not perfil:
        raise HTTPException(status_code=404, detail="Perfil nao encontrado")

    _protegido(perfil, force=force)

    edicoes = db.query(Edicao).filter(Edicao.perfil_id == perfil_id).all()
    if not edicoes:
        return {"deleted": 0, "r2_files_deleted": 0}

    r2_deleted = 0

    # Limpar screenshots de reports vinculados antes do cascade SET NULL
    edicao_ids = [e.id for e in edicoes]
    reports = db.query(Report).filter(Report.edicao_id.in_(edicao_ids)).all()
    for report in reports:
        keys: list[str] = json.loads(report.screenshots_json or "[]")
        for key in keys:
            try:
                storage.delete(key)
                r2_deleted += 1
            except Exception:
                pass
        report.screenshots_json = "[]"

    # Limpar arquivos R2 de cada edição
    for edicao in edicoes:
        if edicao.r2_base and perfil.r2_prefix:
            prefix = f"{perfil.r2_prefix}/{edicao.r2_base}"
            try:
                files = storage.list_files(prefix)
                for key in files:
                    try:
                        storage.delete(key)
                        r2_deleted += 1
                    except Exception:
                        pass
            except Exception:
                logger.warning(f"Erro listando R2 prefix={prefix}")

    # Deletar edições (CASCADE limpa overlays, posts, seo, renders, alinhamentos, traduções)
    count = len(edicoes)
    for edicao in edicoes:
        db.delete(edicao)

    db.commit()
    logger.info(f"[admin-perfis] Reset perfil={perfil.slug}: {count} edicoes deletadas, {r2_deleted} arquivos R2 removidos")
    return {"deleted": count, "r2_files_deleted": r2_deleted}


# -- Router interno (sem auth) ------------------------------------------------

router_internal = APIRouter(
    prefix="/api/internal",
    tags=["internal"],
)


@router_internal.get("/perfil/{slug}/curadoria-config")
def curadoria_config_interno(slug: str, db: Session = Depends(get_db)):
    """Endpoint interno: curadoria busca config da marca aqui. Sem autenticação.

    Retorna os campos de curadoria no formato que app-curadoria/backend/config.py espera.
    """
    perfil = db.query(Perfil).filter(Perfil.slug == slug).first()
    if not perfil:
        raise HTTPException(status_code=404, detail=f"Perfil nao encontrado: {slug}")

    logger.info(f"[internal] curadoria-config solicitada: slug={slug}")
    return build_curadoria_config(perfil)


@router_internal.get("/perfil/{slug}/redator-config")
def redator_config_interno(slug: str, db: Session = Depends(get_db)):
    """Endpoint interno: redator busca config da marca aqui. Sem autenticação."""
    perfil = db.query(Perfil).filter(Perfil.slug == slug).first()
    if not perfil:
        raise HTTPException(status_code=404, detail=f"Perfil não encontrado: {slug}")

    return build_redator_config(perfil)
