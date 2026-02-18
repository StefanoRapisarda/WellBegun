from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from wellbegun.database import get_db
from wellbegun.schemas.reading_list import (
    ReadingListCreate,
    ReadingListItemCreate,
    ReadingListItemOut,
    ReadingListItemUpdate,
    ReadingListOut,
    ReadingListUpdate,
)
from wellbegun.services import reading_list_service

router = APIRouter(prefix="/reading-lists", tags=["reading-lists"])


@router.get("/", response_model=list[ReadingListOut])
def list_reading_lists(db: Session = Depends(get_db)):
    return reading_list_service.get_all(db)


@router.get("/{reading_list_id}", response_model=ReadingListOut)
def get_reading_list(reading_list_id: int, db: Session = Depends(get_db)):
    reading_list = reading_list_service.get_by_id(db, reading_list_id)
    if not reading_list:
        raise HTTPException(status_code=404, detail="Reading list not found")
    return reading_list


@router.post("/", response_model=ReadingListOut, status_code=201)
def create_reading_list(data: ReadingListCreate, db: Session = Depends(get_db)):
    return reading_list_service.create(
        db,
        title=data.title,
        description=data.description,
    )


@router.put("/{reading_list_id}", response_model=ReadingListOut)
def update_reading_list(
    reading_list_id: int, data: ReadingListUpdate, db: Session = Depends(get_db)
):
    updates = data.model_dump(exclude_unset=True)
    reading_list = reading_list_service.update(db, reading_list_id, **updates)
    if not reading_list:
        raise HTTPException(status_code=404, detail="Reading list not found")
    return reading_list


@router.delete("/{reading_list_id}")
def delete_reading_list(reading_list_id: int, db: Session = Depends(get_db)):
    if not reading_list_service.delete(db, reading_list_id):
        raise HTTPException(status_code=404, detail="Reading list not found")
    return {"ok": True}


@router.post("/{reading_list_id}/activate", response_model=ReadingListOut)
def activate_reading_list(reading_list_id: int, db: Session = Depends(get_db)):
    reading_list = reading_list_service.activate(db, reading_list_id)
    if not reading_list:
        raise HTTPException(status_code=404, detail="Reading list not found")
    return reading_list


@router.post("/{reading_list_id}/deactivate", response_model=ReadingListOut)
def deactivate_reading_list(reading_list_id: int, db: Session = Depends(get_db)):
    reading_list = reading_list_service.deactivate(db, reading_list_id)
    if not reading_list:
        raise HTTPException(status_code=404, detail="Reading list not found")
    return reading_list


# Item endpoints

@router.post("/{reading_list_id}/items", response_model=ReadingListItemOut, status_code=201)
def add_item(
    reading_list_id: int, data: ReadingListItemCreate, db: Session = Depends(get_db)
):
    reading_list = reading_list_service.get_by_id(db, reading_list_id)
    if not reading_list:
        raise HTTPException(status_code=404, detail="Reading list not found")
    return reading_list_service.add_item(
        db,
        list_id=reading_list_id,
        source_id=data.source_id,
        position=data.position,
        status=data.status,
        notes=data.notes,
    )


@router.put("/items/{item_id}", response_model=ReadingListItemOut)
def update_item(item_id: int, data: ReadingListItemUpdate, db: Session = Depends(get_db)):
    updates = data.model_dump(exclude_unset=True)
    item = reading_list_service.update_item(db, item_id, **updates)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@router.delete("/items/{item_id}")
def remove_item(item_id: int, db: Session = Depends(get_db)):
    if not reading_list_service.remove_item(db, item_id):
        raise HTTPException(status_code=404, detail="Item not found")
    return {"ok": True}
