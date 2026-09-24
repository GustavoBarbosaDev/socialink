from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.database import get_session
from app.dependencies import get_current_voluntario, get_oportunidade
from app.models import Inscricao, Oportunidade, Usuario
from app.schemas import InscricaoResponse

router = APIRouter(tags=["Inscrições"])


@router.post(
    "/oportunidades/{oportunidade_id}/inscricoes",
    response_model=InscricaoResponse,
    status_code=status.HTTP_201_CREATED,
)
def inscrever_voluntario(
    oportunidade_id: int,
    usuario: Usuario = Depends(get_current_voluntario),
    oportunidade: Oportunidade = Depends(get_oportunidade),
    session: Session = Depends(get_session),
):
    """Inscreve o voluntário autenticado em uma oportunidade (apenas voluntários).

    Regra de negócio: um voluntário só pode se inscrever uma vez na mesma
    oportunidade — duplicidade retorna 409.
    """
    stmt = select(Inscricao).where(
        Inscricao.oportunidade_id == oportunidade_id,
        Inscricao.voluntario_id == usuario.id,
    )
    if session.exec(stmt).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Voluntário já inscrito nesta oportunidade",
        )

    inscricao = Inscricao(oportunidade_id=oportunidade_id, voluntario_id=usuario.id)
    session.add(inscricao)
    session.commit()
    session.refresh(inscricao)
    return inscricao


@router.get("/voluntario/me/inscricoes", response_model=list[InscricaoResponse])
def listar_minhas_inscricoes(
    usuario: Usuario = Depends(get_current_voluntario),
    session: Session = Depends(get_session),
):
    """Lista todas as inscrições do voluntário autenticado."""
    stmt = select(Inscricao).where(Inscricao.voluntario_id == usuario.id)
    return session.exec(stmt).all()
