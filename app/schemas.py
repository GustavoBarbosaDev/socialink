from pydantic import BaseModel, EmailStr
from app.models import PapelUsuario


class UsuarioCreate(BaseModel):
    """Schema para entrada de dados no registro de usuário."""
    nome: str
    email: EmailStr
    senha: str
    papel: PapelUsuario = PapelUsuario.VOLUNTARIO


class UsuarioResponse(BaseModel):
    """Schema para resposta de dados do usuário (sem senha)."""
    id: int
    nome: str
    email: str
    papel: PapelUsuario

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    """Schema para entrada de dados no login."""
    email: EmailStr
    senha: str


class TokenResponse(BaseModel):
    """Schema para resposta do token JWT."""
    access_token: str
    token_type: str = "bearer"
