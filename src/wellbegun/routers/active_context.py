from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from wellbegun.database import get_db
from wellbegun.schemas.active_context import ActiveContextOut
from wellbegun.services.active_context_service import get_active_context

router = APIRouter(tags=["active-context"])


@router.get("/active-context", response_model=ActiveContextOut)
def active_context(db: Session = Depends(get_db)):
    return get_active_context(db)
