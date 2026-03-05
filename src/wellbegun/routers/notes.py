from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from wellbegun.database import get_db
from wellbegun.schemas.note import NoteCreate, NoteOut, NoteUpdate
from wellbegun.services import note_service

router = APIRouter(prefix="/notes", tags=["notes"])


@router.get("/", response_model=list[NoteOut])
def list_notes(db: Session = Depends(get_db)):
    return note_service.get_all(db)


@router.get("/{note_id}", response_model=NoteOut)
def get_note(note_id: int, db: Session = Depends(get_db)):
    note = note_service.get_by_id(db, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


@router.post("/", response_model=NoteOut, status_code=201)
def create_note(data: NoteCreate, db: Session = Depends(get_db)):
    return note_service.create(db, title=data.title, content=data.content)


@router.put("/{note_id}", response_model=NoteOut)
def update_note(note_id: int, data: NoteUpdate, db: Session = Depends(get_db)):
    updates = data.model_dump(exclude_unset=True)
    note = note_service.update(db, note_id, **updates)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


@router.delete("/{note_id}")
def delete_note(note_id: int, db: Session = Depends(get_db)):
    if not note_service.delete(db, note_id):
        raise HTTPException(status_code=404, detail="Note not found")
    return {"ok": True}


@router.post("/{note_id}/activate", response_model=NoteOut)
def activate_note(note_id: int, db: Session = Depends(get_db)):
    note = note_service.activate(db, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


@router.post("/{note_id}/deactivate", response_model=NoteOut)
def deactivate_note(note_id: int, db: Session = Depends(get_db)):
    note = note_service.deactivate(db, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


@router.post("/{note_id}/archive", response_model=NoteOut)
def archive_note(note_id: int, db: Session = Depends(get_db)):
    note = note_service.archive(db, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


@router.post("/{note_id}/unarchive", response_model=NoteOut)
def unarchive_note(note_id: int, db: Session = Depends(get_db)):
    note = note_service.unarchive(db, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note
