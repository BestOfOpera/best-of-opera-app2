"""Rotas de autenticação — login, registro e gerenciamento de usuários."""
import logging
from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from passlib.context import CryptContext
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.auth import criar_token, get_current_user, require_admin
from app.models.usuario import Usuario
from app.models.login_history import LoginHistory
from app.models.user_session import UserSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/editor/auth", tags=["auth"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _hash_senha(senha: str) -> str:
    return pwd_context.hash(senha)


def _verificar_senha(senha: str, hash_: str) -> bool:
    return pwd_context.verify(senha, hash_)


# ── Schemas inline ───────────────────────────────────────────────────────────

from pydantic import BaseModel
from typing import Optional


class LoginRequest(BaseModel):
    email: str
    senha: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    email: str
    nome: str
    role: str
    must_change_password: bool = False


class UsuarioCreate(BaseModel):
    nome: str
    email: str
    senha: str = "arias2026"
    role: str = "operador"


class UsuarioOut(BaseModel):
    id: int
    nome: str
    email: str
    role: str
    ativo: bool
    must_change_password: bool = False
    ultimo_login: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UsuarioUpdate(BaseModel):
    nome: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    ativo: Optional[bool] = None
    senha: Optional[str] = None


class AlterarSenhaRequest(BaseModel):
    senha_nova: str


# ── Rotas ────────────────────────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)):
    """Email + senha → retorna JWT token."""
    usuario = db.query(Usuario).filter(
        func.lower(Usuario.email) == body.email.lower(),
        Usuario.ativo == True,
    ).first()
    if not usuario or not _verificar_senha(body.senha, usuario.senha_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")

    usuario.ultimo_login = datetime.utcnow()
    login_record = LoginHistory(
        user_id=usuario.id,
        ip_address=request.client.host if request.client else None,
        user_agent=(request.headers.get("user-agent") or "")[:500],
    )
    db.add(login_record)
    db.commit()

    token = criar_token({
        "user_id": usuario.id,
        "email": usuario.email,
        "nome": usuario.nome,
        "role": usuario.role,
    })
    return TokenResponse(
        access_token=token,
        user_id=usuario.id,
        email=usuario.email,
        nome=usuario.nome,
        role=usuario.role,
        must_change_password=bool(usuario.must_change_password),
    )


@router.post("/registrar", response_model=UsuarioOut, status_code=status.HTTP_201_CREATED)
def registrar(body: UsuarioCreate, db: Session = Depends(get_db), _: Usuario = Depends(require_admin)):
    """Criar novo usuário (somente admins). Senha padrão: arias2026."""
    existente = db.query(Usuario).filter(
        func.lower(Usuario.email) == body.email.lower()
    ).first()
    if existente:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email já cadastrado")

    novo = Usuario(
        nome=body.nome,
        email=body.email,
        senha_hash=_hash_senha(body.senha),
        role=body.role,
        must_change_password=True,
    )
    db.add(novo)
    db.commit()
    db.refresh(novo)
    logger.info(f"[auth] Novo usuário criado: {novo.email} (role={novo.role})")
    return novo


@router.get("/me", response_model=UsuarioOut)
def me(current_user: Usuario = Depends(get_current_user)):
    """Retorna dados do usuário logado."""
    return current_user


@router.post("/alterar-senha", status_code=status.HTTP_204_NO_CONTENT)
def alterar_senha(
    body: AlterarSenhaRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Permite que o usuário logado troque a própria senha."""
    if len(body.senha_nova) < 6:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Senha deve ter pelo menos 6 caracteres")
    current_user.senha_hash = _hash_senha(body.senha_nova)
    current_user.must_change_password = False
    db.commit()


@router.patch("/usuarios/{usuario_id}", response_model=UsuarioOut)
def atualizar_usuario(
    usuario_id: int,
    body: UsuarioUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin),
):
    """Atualizar usuário (admin only). Não permite mudar próprio role."""
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")

    if body.role is not None and usuario_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não é possível alterar o próprio role")

    updates = body.model_dump(exclude_unset=True)
    nova_senha = updates.pop("senha", None)
    for campo, valor in updates.items():
        setattr(usuario, campo, valor)
    if nova_senha:
        usuario.senha_hash = _hash_senha(nova_senha)
        usuario.must_change_password = True  # força troca na próxima entrada

    db.commit()
    db.refresh(usuario)
    return usuario


@router.get("/usuarios", response_model=List[UsuarioOut])
def listar_usuarios(db: Session = Depends(get_db), _: Usuario = Depends(require_admin)):
    """Listar todos os usuários (admin only)."""
    return db.query(Usuario).order_by(Usuario.nome).all()


# ── Analytics ───────────────────────────────────────────────────────────────


@router.post("/heartbeat")
def heartbeat(
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Heartbeat para tracking de tempo ativo. Chamado pelo frontend a cada 5 min."""
    now = datetime.utcnow()
    ten_min_ago = now - timedelta(minutes=10)

    session = db.query(UserSession).filter(
        UserSession.user_id == current_user.id,
        UserSession.last_seen_at >= ten_min_ago,
    ).first()

    if session:
        session.last_seen_at = now
        session.duration_minutes = int((now - session.started_at).total_seconds() / 60)
    else:
        session = UserSession(
            user_id=current_user.id,
            started_at=now,
            last_seen_at=now,
            duration_minutes=0,
        )
        db.add(session)

    db.commit()
    return {"ok": True}


@router.get("/usuarios/{user_id}/logins")
def get_login_history(
    user_id: int,
    limit: int = 50,
    current_user: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Histórico de logins de um usuário. Requer admin."""
    total = db.query(LoginHistory).filter(LoginHistory.user_id == user_id).count()
    logins = (
        db.query(LoginHistory)
        .filter(LoginHistory.user_id == user_id)
        .order_by(LoginHistory.timestamp.desc())
        .limit(limit)
        .all()
    )

    def parse_device(ua: str) -> str:
        if not ua:
            return "Desconhecido"
        ua_lower = ua.lower()
        browser = (
            "Chrome" if "chrome" in ua_lower
            else "Safari" if "safari" in ua_lower
            else "Firefox" if "firefox" in ua_lower
            else "Outro"
        )
        device = (
            "iPad" if "ipad" in ua_lower
            else "iPhone" if "iphone" in ua_lower
            else "Android" if "android" in ua_lower
            else "Mac" if "macintosh" in ua_lower
            else "Windows" if "windows" in ua_lower
            else "Linux" if "linux" in ua_lower
            else ""
        )
        return f"{browser} / {device}" if device else browser

    return {
        "user_id": user_id,
        "total": total,
        "logins": [
            {
                "timestamp": l.timestamp.isoformat() if l.timestamp else None,
                "ip": l.ip_address,
                "device": parse_device(l.user_agent or ""),
            }
            for l in logins
        ],
    }


@router.get("/usuarios/{user_id}/sessions")
def get_user_sessions(
    user_id: int,
    days: int = 30,
    current_user: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Sessões e tempo ativo de um usuário. Requer admin."""
    since = datetime.utcnow() - timedelta(days=days)
    sessions = (
        db.query(UserSession)
        .filter(UserSession.user_id == user_id, UserSession.started_at >= since)
        .order_by(UserSession.started_at.desc())
        .all()
    )

    by_day: dict[str, int] = {}
    for s in sessions:
        day = s.started_at.strftime("%Y-%m-%d")
        by_day.setdefault(day, 0)
        by_day[day] += s.duration_minutes or 0

    total_minutes = sum(by_day.values())
    days_active = max(len(by_day), 1)

    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    today_minutes = by_day.get(today_str, 0)

    now = datetime.utcnow()
    week_start = (now - timedelta(days=now.weekday())).strftime("%Y-%m-%d")
    week_minutes = sum(v for k, v in by_day.items() if k >= week_start)

    return {
        "user_id": user_id,
        "today_minutes": today_minutes,
        "week_minutes": week_minutes,
        "month_minutes": total_minutes,
        "avg_daily_minutes": total_minutes // days_active,
        "days_active": days_active,
        "by_day": [{"date": k, "minutes": v} for k, v in sorted(by_day.items(), reverse=True)],
        "sessions": [
            {
                "started": s.started_at.isoformat(),
                "ended": s.last_seen_at.isoformat(),
                "duration_min": s.duration_minutes or 0,
            }
            for s in sessions[:50]
        ],
    }
