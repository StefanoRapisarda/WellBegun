from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from log_input_panels.database import get_db
from log_input_panels.schemas.log import ActivityCreate, ActivityOut, ActivityUpdate
from log_input_panels.services import activity_service

router = APIRouter(prefix="/activities", tags=["activities"])


@router.get("/", response_model=list[ActivityOut])
def list_activities(db: Session = Depends(get_db)):
    return activity_service.get_all(db)


@router.post("/deactivate-all")
def deactivate_all_activities(db: Session = Depends(get_db)):
    count = activity_service.deactivate_all(db)
    return {"ok": True, "deactivated": count}


@router.get("/{activity_id}", response_model=ActivityOut)
def get_activity(activity_id: int, db: Session = Depends(get_db)):
    activity = activity_service.get_by_id(db, activity_id)
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    return activity


@router.post("/", response_model=ActivityOut, status_code=201)
def create_activity(data: ActivityCreate, db: Session = Depends(get_db)):
    return activity_service.create(
        db, title=data.title, description=data.description, duration=data.duration, log_id=data.log_id, status=data.status
    )


@router.put("/{activity_id}", response_model=ActivityOut)
def update_activity(activity_id: int, data: ActivityUpdate, db: Session = Depends(get_db)):
    updates = data.model_dump(exclude_unset=True)
    activity = activity_service.update(db, activity_id, **updates)
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    return activity


@router.delete("/{activity_id}")
def delete_activity(activity_id: int, db: Session = Depends(get_db)):
    if not activity_service.delete(db, activity_id):
        raise HTTPException(status_code=404, detail="Activity not found")
    return {"ok": True}


@router.post("/{activity_id}/activate", response_model=ActivityOut)
def activate_activity(activity_id: int, db: Session = Depends(get_db)):
    activity = activity_service.activate(db, activity_id)
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    return activity


@router.post("/{activity_id}/deactivate", response_model=ActivityOut)
def deactivate_activity(activity_id: int, db: Session = Depends(get_db)):
    activity = activity_service.deactivate(db, activity_id)
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    return activity


@router.post("/{activity_id}/archive", response_model=ActivityOut)
def archive_activity(activity_id: int, db: Session = Depends(get_db)):
    activity = activity_service.archive(db, activity_id)
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    return activity


@router.post("/{activity_id}/unarchive", response_model=ActivityOut)
def unarchive_activity(activity_id: int, db: Session = Depends(get_db)):
    activity = activity_service.unarchive(db, activity_id)
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    return activity
