from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.database import get_session
from app.dependencies import get_current_organizacao, get_oportunidade_dono
from app.models import Oportunidade, Usuario
from app.schemas import (
    OportunidadeCreate,
    OportunidadeResponse,
    OportunidadeUpdate,
)

router = APIRouter(prefix="/oportunidades", tags=["Oportunidades"])


@router.post(
    "/",
    response_model=OportunidadeResponse,
    status_code=status.HTTP_201_CREATED,
)
def criar_oportunidade(
    dados: OportunidadeCreate,
    session: Session = Depends(get_session),
    usuario: Usuario = Depends(get_current_organizacao),
):
    """Cria uma nova oportunidade de voluntariado (apenas organizações)."""
    oportunidade = Oportunidade(
        titulo=dados.titulo,
        descricao=dados.descricao,
        local=dados.local,
        data=dados.data,
        vagas_disponiveis=dados.vagas_disponiveis,
        organizacao_id=usuario.id,
    )
    session.add(oportunidade)
    session.commit()
    session.refresh(oportunidade)
    return oportunidade


@router.get("/", response_model=list[OportunidadeResponse])
def listar_oportunidades(session: Session = Depends(get_session)):
    """Lista todas as oportunidades cadastradas."""
    stmt = select(Oportunidade)
    oportunidades = session.exec(stmt).all()
    return oportunidades


@router.get("/{oportunidade_id}", response_model=OportunidadeResponse)
def detalhar_oportunidade(
    oportunidade_id: int,
    session: Session = Depends(get_session),
):
    """Retorna os detalhes de uma oportunidade específica."""
    oportunidade = session.get(Oportunidade, oportunidade_id)
    if not oportunidade:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Oportunidade não encontrada",
        )
    return oportunidade


@router.patch("/{oportunidade_id}", response_model=OportunidadeResponse)
def atualizar_oportunidade(
    dados: OportunidadeUpdate,
    oportunidade: Oportunidade = Depends(get_oportunidade_dono),
    session: Session = Depends(get_session),
):
    """Atualiza parcialmente uma oportunidade (apenas o dono)."""
    dados_dict = dados.model_dump(exclude_unset=True)
    for campo, valor in dados_dict.items():
        setattr(oportunidade, campo, valor)

    session.add(oportunidade)
    session.commit()
    session.refresh(oportunidade)
    return oportunidade


@router.delete("/{oportunidade_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover_oportunidade(
    oportunidade: Oportunidade = Depends(get_oportunidade_dono),
    session: Session = Depends(get_session),
):
    """Remove uma oportunidade (apenas o dono)."""
    session.delete(oportunidade)
    session.commit()
