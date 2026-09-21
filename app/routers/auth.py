from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError, jwt
from sqlmodel import Session, select
from passlib.context import CryptContext

from app.config import get_settings
from app.database import get_session
from app.models import Usuario
from app.schemas import UsuarioCreate, UsuarioResponse, LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["Autenticação"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

settings = get_settings()


def get_password_hash(password: str) -> str:
    """Gera o hash da senha usando bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica se a senha plain confere com o hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict) -> str:
    """Cria um token JWT com os dados fornecidos."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


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


@router.post("/login", response_model=TokenResponse)
def login(dados: LoginRequest, session: Session = Depends(get_session)):
    """Realiza login e retorna um token JWT."""
    # Buscar usuário pelo email
    stmt = select(Usuario).where(Usuario.email == dados.email)
    usuario = session.exec(stmt).first()

    # Verificar se o usuário existe e se a senha está correta
    if not usuario or not verify_password(dados.senha, usuario.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Criar token JWT
    access_token = create_access_token(data={"sub": usuario.email, "papel": usuario.papel})

    return TokenResponse(access_token=access_token)
