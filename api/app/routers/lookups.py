from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Dosage, Medication

router = APIRouter(prefix="/api", tags=["lookups"])


@router.get("/medications", response_model=list[str])
def list_medications(db: Session = Depends(get_db)):
    return list(db.scalars(select(Medication.name).order_by(Medication.name)))


@router.get("/dosages", response_model=list[str])
def list_dosages(db: Session = Depends(get_db)):
    values = list(db.scalars(select(Dosage.value)))  # sort numerically by mg
    return sorted(values, key=lambda v: int("".join(c for c in v if c.isdigit()) or 0))
