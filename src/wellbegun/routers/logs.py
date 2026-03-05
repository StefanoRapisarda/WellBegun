from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from wellbegun.database import get_db
from wellbegun.schemas.log import LogCreate, LogOut, LogUpdate
from wellbegun.services import log_service

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("/", response_model=list[LogOut])
def list_logs(db: Session = Depends(get_db)):
    return log_service.get_all_logs(db)


@router.get("/active", response_model=list[LogOut])
def list_active_logs(db: Session = Depends(get_db)):
    return log_service.get_active_logs(db)


@router.get("/{log_id}", response_model=LogOut)
def get_log(log_id: int, db: Session = Depends(get_db)):
    log = log_service.get_log_by_id(db, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    return log


@router.post("/", response_model=LogOut, status_code=201)
def create_log(data: LogCreate, db: Session = Depends(get_db)):
    return log_service.create_log(db, title=data.title, content=data.content)


@router.put("/{log_id}", response_model=LogOut)
def update_log(log_id: int, data: LogUpdate, db: Session = Depends(get_db)):
    updates = data.model_dump(exclude_unset=True)
    log = log_service.update_log(db, log_id, **updates)
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    return log


@router.delete("/{log_id}")
def delete_log(log_id: int, db: Session = Depends(get_db)):
    if not log_service.delete_log(db, log_id):
        raise HTTPException(status_code=404, detail="Log not found")
    return {"ok": True}


@router.post("/{log_id}/activate", response_model=LogOut)
def activate_log(log_id: int, db: Session = Depends(get_db)):
    log = log_service.activate_log(db, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    return log


@router.post("/{log_id}/deactivate", response_model=LogOut)
def deactivate_log(log_id: int, db: Session = Depends(get_db)):
    log = log_service.deactivate_log(db, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    return log


@router.post("/{log_id}/archive", response_model=LogOut)
def archive_log(log_id: int, db: Session = Depends(get_db)):
    log = log_service.archive_log(db, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    return log


@router.post("/{log_id}/unarchive", response_model=LogOut)
def unarchive_log(log_id: int, db: Session = Depends(get_db)):
    log = log_service.unarchive_log(db, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    return log
