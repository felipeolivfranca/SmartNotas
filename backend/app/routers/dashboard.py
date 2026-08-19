"""Endpoints de agregação para o dashboard."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..services import dashboard as svc

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/meses")
def listar_meses(db: Session = Depends(get_db)) -> list[dict]:
    """Meses que já têm nota lançada, para popular o seletor de período."""
    return svc.meses_disponiveis(db)


@router.get("/resumo")
def resumo(
    mes: str | None = Query(
        default=None,
        pattern=r"^\d{4}-\d{2}$",
        description="Período no formato AAAA-MM. Omitido = mês atual.",
    ),
    db: Session = Depends(get_db),
) -> dict:
    """Resumo do mês: total, itens somados e quebra por categoria."""
    if mes is None:
        hoje = date.today()
        ano, numero = hoje.year, hoje.month
    else:
        ano, numero = int(mes[:4]), int(mes[5:7])
        if not 1 <= numero <= 12:
            raise HTTPException(status_code=422, detail="Mês precisa estar entre 01 e 12")

    return svc.resumo(db, ano, numero)
