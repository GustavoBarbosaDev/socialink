from enum import Enum
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field, Relationship


# Enums para os campos de status e papel
class PapelUsuario(str, Enum):
    ORGANIZACAO = "organizacao"
    VOLUNTARIO = "voluntario"


class StatusInscricao(str, Enum):
    PENDENTE = "pendente"
    APROVADO = "aprovado"
    RECUSADO = "recusado"


# Model do Usuario
class Usuario(SQLModel, table=True):
    __tablename__ = "usuarios"

    id: Optional[int] = Field(default=None, primary_key=True)
    nome: str = Field(max_length=100)
    email: str = Field(unique=True, index=True, max_length=150)
    senha_hash: str = Field(max_length=200)
    papel: PapelUsuario = Field(default=PapelUsuario.VOLUNTARIO)

    # Relacionamentos
    oportunidades: list["Oportunidade"] = Relationship(back_populates="organizacao")
    inscricoes: list["Inscricao"] = Relationship(back_populates="voluntario")


# Model da Oportunidade
class Oportunidade(SQLModel, table=True):
    __tablename__ = "oportunidades"

    id: Optional[int] = Field(default=None, primary_key=True)
    titulo: str = Field(max_length=150)
    descricao: str = Field(max_length=500)
    local: str = Field(max_length=150)
    data: datetime
    vagas_disponiveis: int = Field(ge=1)  #ge = greater than or equal (mínimo 1 vaga)
    organizacao_id: int = Field(foreign_key="usuarios.id")

    # Relacionamentos
    organizacao: Usuario = Relationship(back_populates="oportunidades")
    inscricoes: list["Inscricao"] = Relationship(back_populates="oportunidade")


# Model da Inscricao
class Inscricao(SQLModel, table=True):
    __tablename__ = "inscricoes"

    id: Optional[int] = Field(default=None, primary_key=True)
    oportunidade_id: int = Field(foreign_key="oportunidades.id")
    voluntario_id: int = Field(foreign_key="usuarios.id")
    status: StatusInscricao = Field(default=StatusInscricao.PENDENTE)
    criado_em: datetime = Field(default_factory=datetime.now)

    # Relacionamentos
    oportunidade: Oportunidade = Relationship(back_populates="inscricoes")
    voluntario: Usuario = Relationship(back_populates="inscricoes")
