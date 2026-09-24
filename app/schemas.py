from datetime import datetime
from pydantic import BaseModel, EmailStr, Field
from app.models import PapelUsuario, StatusInscricao


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


class OportunidadeCreate(BaseModel):
    """Schema para entrada de dados na criação de oportunidade."""
    titulo: str
    descricao: str
    local: str
    data: datetime
    vagas_disponiveis: int = Field(ge=1)


class OportunidadeResponse(BaseModel):
    """Schema para resposta de dados da oportunidade."""
    id: int
    titulo: str
    descricao: str
    local: str
    data: datetime
    vagas_disponiveis: int
    organizacao_id: int

    class Config:
        from_attributes = True


class OportunidadeUpdate(BaseModel):
    """Schema para atualização parcial de oportunidade (todos campos opcionais)."""
    titulo: str | None = None
    descricao: str | None = None
    local: str | None = None
    data: datetime | None = None
    vagas_disponiveis: int | None = Field(default=None, ge=1)


class InscricaoResponse(BaseModel):
    """Schema para resposta de dados da inscrição."""
    id: int
    oportunidade_id: int
    voluntario_id: int
    status: StatusInscricao
    criado_em: datetime

    class Config:
        from_attributes = True
