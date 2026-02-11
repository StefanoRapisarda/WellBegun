from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from log_input_panels.database import get_db
from log_input_panels.schemas.actor import ActorCreate, ActorOut, ActorUpdate
from log_input_panels.services import actor_service

router = APIRouter(prefix="/actors", tags=["actors"])


@router.get("/", response_model=list[ActorOut])
def list_actors(db: Session = Depends(get_db)):
    return actor_service.get_all(db)


@router.get("/{actor_id}", response_model=ActorOut)
def get_actor(actor_id: int, db: Session = Depends(get_db)):
    actor = actor_service.get_by_id(db, actor_id)
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
    return actor


@router.post("/", response_model=ActorOut, status_code=201)
def create_actor(data: ActorCreate, db: Session = Depends(get_db)):
    return actor_service.create(
        db,
        full_name=data.full_name,
        role=data.role,
        affiliation=data.affiliation,
        expertise=data.expertise,
        notes=data.notes,
        email=data.email,
        url=data.url,
    )


@router.put("/{actor_id}", response_model=ActorOut)
def update_actor(actor_id: int, data: ActorUpdate, db: Session = Depends(get_db)):
    updates = data.model_dump(exclude_unset=True)
    actor = actor_service.update(db, actor_id, **updates)
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
    return actor


@router.delete("/{actor_id}")
def delete_actor(actor_id: int, db: Session = Depends(get_db)):
    if not actor_service.delete(db, actor_id):
        raise HTTPException(status_code=404, detail="Actor not found")
    return {"ok": True}


@router.post("/{actor_id}/activate", response_model=ActorOut)
def activate_actor(actor_id: int, db: Session = Depends(get_db)):
    actor = actor_service.activate(db, actor_id)
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
    return actor


@router.post("/{actor_id}/deactivate", response_model=ActorOut)
def deactivate_actor(actor_id: int, db: Session = Depends(get_db)):
    actor = actor_service.deactivate(db, actor_id)
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
    return actor


@router.post("/{actor_id}/archive", response_model=ActorOut)
def archive_actor(actor_id: int, db: Session = Depends(get_db)):
    actor = actor_service.archive(db, actor_id)
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
    return actor


@router.post("/{actor_id}/unarchive", response_model=ActorOut)
def unarchive_actor(actor_id: int, db: Session = Depends(get_db)):
    actor = actor_service.unarchive(db, actor_id)
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
    return actor
