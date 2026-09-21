from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from passlib.context import CryptContext

from app.database import get_session
from app.models import Usuario
from app.schemas import UsuarioCreate, UsuarioResponse

router = APIRouter(prefix="/auth", tags=["Autenticação"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    """Gera o hash da senha usando bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica se a senha plain confere com o hash."""
    return pwd_context.verify(plain_password, hashed_password)


@router.post("/registrar", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED)
def registrar(usuario: UsuarioCreate, session: Session = Depends(get_session)):
    """Registra um novo usuário no sistema."""
    # Verificar se o email já está cadastrado
    stmt = select(Usuario).where(Usuario.email == usuario.email)
    result = session.exec(stmt).first()

    if result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email já cadastrado"
        )

    # Criar hash da senha
    senha_hash = get_password_hash(usuario.senha)

    # Criar novo usuário
    novo_usuario = Usuario(
        nome=usuario.nome,
        email=usuario.email,
        senha_hash=senha_hash,
        papel=usuario.papel
    )

    session.add(novo_usuario)
    session.commit()
    session.refresh(novo_usuario)

    return novo_usuario
