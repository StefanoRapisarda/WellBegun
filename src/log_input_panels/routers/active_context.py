from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from log_input_panels.database import get_db
from log_input_panels.schemas.active_context import ActiveContextOut
from log_input_panels.services.active_context_service import get_active_context

router = APIRouter(tags=["active-context"])


@router.get("/active-context", response_model=ActiveContextOut)
def active_context(db: Session = Depends(get_db)):
    return get_active_context(db)
