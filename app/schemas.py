from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from app.models import PapelUsuario, StatusInscricao


def assumir_utc(valor: datetime | None) -> datetime | None:
    """Aceita datetime sem offset (padrão do Swagger e de muitos clientes)
    e o trata como UTC.

    O SQLModel ≥ 0.0.47 recusa datetime naive na gravação — sem esta
    normalização, `POST /oportunidades` com "2026-10-15T09:00:00"
    estouraria um 500 em vez de salvar.
    """
    if valor is not None and valor.tzinfo is None:
        return valor.replace(tzinfo=timezone.utc)
    return valor


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

    model_config = ConfigDict(from_attributes=True)


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

    @field_validator("data")
    @classmethod
    def data_em_utc(cls, valor: datetime) -> datetime:
        return assumir_utc(valor)  # type: ignore[return-value]


class OportunidadeResponse(BaseModel):
    """Schema para resposta de dados da oportunidade."""
    id: int
    titulo: str
    descricao: str
    local: str
    data: datetime
    vagas_disponiveis: int
    organizacao_id: int

    model_config = ConfigDict(from_attributes=True)


class OportunidadeUpdate(BaseModel):
    """Schema para atualização parcial de oportunidade (todos campos opcionais)."""
    titulo: str | None = None
    descricao: str | None = None
    local: str | None = None
    data: datetime | None = None
    vagas_disponiveis: int | None = Field(default=None, ge=1)

    @field_validator("data")
    @classmethod
    def data_em_utc(cls, valor: datetime | None) -> datetime | None:
        return assumir_utc(valor)


class InscricaoResponse(BaseModel):
    """Schema para resposta de dados da inscrição."""
    id: int
    oportunidade_id: int
    voluntario_id: int
    status: StatusInscricao
    criado_em: datetime

    model_config = ConfigDict(from_attributes=True)


class InscricaoUpdate(BaseModel):
    """Schema para a decisão (aprovar/recusar) de uma inscrição.

    A máquina de estados só aceita transições para os estados finais:
    quem decide não pode voltar uma inscrição para 'pendente'.
    """
    status: StatusInscricao

    @field_validator("status")
    @classmethod
    def status_deve_ser_final(cls, valor: StatusInscricao) -> StatusInscricao:
        if valor == StatusInscricao.PENDENTE:
            raise ValueError(
                "Status alvo deve ser 'aprovado' ou 'recusado'"
            )
        return valor
