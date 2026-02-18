from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from log_input_panels.database import get_db
from log_input_panels.schemas.source import SourceCreate, SourceOut, SourceUpdate
from log_input_panels.services import source_service

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("/", response_model=list[SourceOut])
def list_sources(db: Session = Depends(get_db)):
    return source_service.get_all(db)


@router.get("/{source_id}", response_model=SourceOut)
def get_source(source_id: int, db: Session = Depends(get_db)):
    source = source_service.get_by_id(db, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return source


@router.post("/", response_model=SourceOut, status_code=201)
def create_source(data: SourceCreate, db: Session = Depends(get_db)):
    return source_service.create(
        db,
        title=data.title,
        description=data.description,
        author=data.author,
        content_url=data.content_url,
        source_type=data.source_type,
    )


@router.put("/{source_id}", response_model=SourceOut)
def update_source(source_id: int, data: SourceUpdate, db: Session = Depends(get_db)):
    updates = data.model_dump(exclude_unset=True)
    source = source_service.update(db, source_id, **updates)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return source


@router.delete("/{source_id}")
def delete_source(source_id: int, db: Session = Depends(get_db)):
    if not source_service.delete(db, source_id):
        raise HTTPException(status_code=404, detail="Source not found")
    return {"ok": True}


@router.post("/{source_id}/activate", response_model=SourceOut)
def activate_source(source_id: int, db: Session = Depends(get_db)):
    source = source_service.activate(db, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return source


@router.post("/{source_id}/deactivate", response_model=SourceOut)
def deactivate_source(source_id: int, db: Session = Depends(get_db)):
    source = source_service.deactivate(db, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return source


@router.post("/{source_id}/archive", response_model=SourceOut)
def archive_source(source_id: int, db: Session = Depends(get_db)):
    source = source_service.archive(db, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return source


@router.post("/{source_id}/unarchive", response_model=SourceOut)
def unarchive_source(source_id: int, db: Session = Depends(get_db)):
    source = source_service.unarchive(db, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return source
