from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from log_input_panels.database import get_db
from log_input_panels.schemas.learning_track import (
    LearningGoalCreate,
    LearningGoalOut,
    LearningGoalUpdate,
    LearningTrackCreate,
    LearningTrackItemCreate,
    LearningTrackItemOut,
    LearningTrackItemUpdate,
    LearningTrackOut,
    LearningTrackUpdate,
)
from log_input_panels.services import learning_track_service

router = APIRouter(prefix="/learning-tracks", tags=["learning-tracks"])


@router.get("/", response_model=list[LearningTrackOut])
def list_learning_tracks(db: Session = Depends(get_db)):
    return learning_track_service.get_all(db)


@router.get("/{learning_track_id}", response_model=LearningTrackOut)
def get_learning_track(learning_track_id: int, db: Session = Depends(get_db)):
    learning_track = learning_track_service.get_by_id(db, learning_track_id)
    if not learning_track:
        raise HTTPException(status_code=404, detail="Learning track not found")
    return learning_track


@router.post("/", response_model=LearningTrackOut, status_code=201)
def create_learning_track(data: LearningTrackCreate, db: Session = Depends(get_db)):
    return learning_track_service.create(
        db,
        title=data.title,
        description=data.description,
    )


@router.put("/{learning_track_id}", response_model=LearningTrackOut)
def update_learning_track(
    learning_track_id: int, data: LearningTrackUpdate, db: Session = Depends(get_db)
):
    updates = data.model_dump(exclude_unset=True)
    learning_track = learning_track_service.update(db, learning_track_id, **updates)
    if not learning_track:
        raise HTTPException(status_code=404, detail="Learning track not found")
    return learning_track


@router.delete("/{learning_track_id}")
def delete_learning_track(learning_track_id: int, db: Session = Depends(get_db)):
    if not learning_track_service.delete(db, learning_track_id):
        raise HTTPException(status_code=404, detail="Learning track not found")
    return {"ok": True}


@router.post("/{learning_track_id}/activate", response_model=LearningTrackOut)
def activate_learning_track(learning_track_id: int, db: Session = Depends(get_db)):
    learning_track = learning_track_service.activate(db, learning_track_id)
    if not learning_track:
        raise HTTPException(status_code=404, detail="Learning track not found")
    return learning_track


@router.post("/{learning_track_id}/deactivate", response_model=LearningTrackOut)
def deactivate_learning_track(learning_track_id: int, db: Session = Depends(get_db)):
    learning_track = learning_track_service.deactivate(db, learning_track_id)
    if not learning_track:
        raise HTTPException(status_code=404, detail="Learning track not found")
    return learning_track


# Item endpoints

@router.post("/{learning_track_id}/items", response_model=LearningTrackItemOut, status_code=201)
def add_item(
    learning_track_id: int, data: LearningTrackItemCreate, db: Session = Depends(get_db)
):
    learning_track = learning_track_service.get_by_id(db, learning_track_id)
    if not learning_track:
        raise HTTPException(status_code=404, detail="Learning track not found")
    return learning_track_service.add_item(
        db,
        track_id=learning_track_id,
        source_id=data.source_id,
        position=data.position,
        status=data.status,
        notes=data.notes,
    )


@router.put("/items/{item_id}", response_model=LearningTrackItemOut)
def update_item(item_id: int, data: LearningTrackItemUpdate, db: Session = Depends(get_db)):
    updates = data.model_dump(exclude_unset=True)
    item = learning_track_service.update_item(db, item_id, **updates)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@router.delete("/items/{item_id}")
def remove_item(item_id: int, db: Session = Depends(get_db)):
    if not learning_track_service.remove_item(db, item_id):
        raise HTTPException(status_code=404, detail="Item not found")
    return {"ok": True}


# Goal endpoints

@router.post("/{learning_track_id}/goals", response_model=LearningGoalOut, status_code=201)
def add_goal(
    learning_track_id: int, data: LearningGoalCreate, db: Session = Depends(get_db)
):
    learning_track = learning_track_service.get_by_id(db, learning_track_id)
    if not learning_track:
        raise HTTPException(status_code=404, detail="Learning track not found")
    return learning_track_service.add_goal(
        db,
        track_id=learning_track_id,
        description=data.description,
    )


@router.put("/goals/{goal_id}", response_model=LearningGoalOut)
def update_goal(goal_id: int, data: LearningGoalUpdate, db: Session = Depends(get_db)):
    updates = data.model_dump(exclude_unset=True)
    goal = learning_track_service.update_goal(db, goal_id, **updates)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return goal


@router.post("/goals/{goal_id}/toggle", response_model=LearningGoalOut)
def toggle_goal(goal_id: int, db: Session = Depends(get_db)):
    goal = learning_track_service.toggle_goal(db, goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return goal


@router.delete("/goals/{goal_id}")
def remove_goal(goal_id: int, db: Session = Depends(get_db)):
    if not learning_track_service.remove_goal(db, goal_id):
        raise HTTPException(status_code=404, detail="Goal not found")
    return {"ok": True}
