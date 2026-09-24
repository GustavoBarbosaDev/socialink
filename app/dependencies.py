from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlmodel import Session, select

from app.config import get_settings
from app.database import get_session
from app.models import Oportunidade, PapelUsuario, Usuario

settings = get_settings()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_session),
) -> Usuario:
    """Decodifica o token JWT e retorna o usuário autenticado."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    stmt = select(Usuario).where(Usuario.email == email)
    usuario = session.exec(stmt).first()

    if usuario is None:
        raise credentials_exception

    return usuario


def get_current_organizacao(
    usuario: Usuario = Depends(get_current_user),
) -> Usuario:
    """Garante que o usuário autenticado tenha papel 'organizacao'."""
    if usuario.papel != PapelUsuario.ORGANIZACAO:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas organizações podem executar esta ação",
        )
    return usuario


def get_current_voluntario(
    usuario: Usuario = Depends(get_current_user),
) -> Usuario:
    """Garante que o usuário autenticado tenha papel 'voluntario'."""
    if usuario.papel != PapelUsuario.VOLUNTARIO:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas voluntários podem executar esta ação",
        )
    return usuario


def get_oportunidade(
    oportunidade_id: int,
    session: Session = Depends(get_session),
) -> Oportunidade:
    """Carrega a oportunidade do path ou retorna 404 se não existir."""
    oportunidade = session.get(Oportunidade, oportunidade_id)
    if not oportunidade:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Oportunidade não encontrada",
        )
    return oportunidade


def get_oportunidade_dono(
    usuario: Usuario = Depends(get_current_user),
    oportunidade: Oportunidade = Depends(get_oportunidade),
) -> Oportunidade:
    """Carrega a oportunidade e garante que o usuário autenticado é o dono.

    Ordem das verificações:
    1. 401 — token ausente/inválido (get_current_user);
    2. 404 — oportunidade não existe (get_oportunidade);
    3. 403 — oportunidade existe, mas não pertence ao usuário.
    """
    if oportunidade.organizacao_id != usuario.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sem permissão para alterar esta oportunidade",
        )

    return oportunidade
