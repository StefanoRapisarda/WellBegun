from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from wellbegun.database import get_db
from wellbegun.schemas.category import (
    CategoryCreate,
    CategoryOut,
    CategoryStatusCreate,
    CategoryStatusOut,
    CategoryStatusUpdate,
    CategoryUpdate,
)
from wellbegun.services import category_service

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("/", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db)):
    return category_service.get_all(db)


@router.get("/{category_id}", response_model=CategoryOut)
def get_category(category_id: int, db: Session = Depends(get_db)):
    category = category_service.get_by_id(db, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


@router.post("/", response_model=CategoryOut, status_code=201)
def create_category(data: CategoryCreate, db: Session = Depends(get_db)):
    return category_service.create(
        db,
        slug=data.slug,
        display_name=data.display_name,
        member_entity_type=data.member_entity_type,
    )


@router.put("/{category_id}", response_model=CategoryOut)
def update_category(
    category_id: int, data: CategoryUpdate, db: Session = Depends(get_db)
):
    updates = data.model_dump(exclude_unset=True)
    category = category_service.update(db, category_id, **updates)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


@router.delete("/{category_id}")
def delete_category(category_id: int, db: Session = Depends(get_db)):
    if not category_service.delete(db, category_id):
        raise HTTPException(status_code=404, detail="Category not found")
    return {"ok": True}


# --- Status endpoints ---

@router.get("/{category_id}/statuses", response_model=list[CategoryStatusOut])
def list_statuses(category_id: int, db: Session = Depends(get_db)):
    return category_service.get_statuses(db, category_id)


@router.post("/{category_id}/statuses", response_model=CategoryStatusOut, status_code=201)
def add_status(
    category_id: int, data: CategoryStatusCreate, db: Session = Depends(get_db)
):
    category = category_service.get_by_id(db, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category_service.add_status(
        db,
        category_id=category_id,
        value=data.value,
        position=data.position,
        is_default=data.is_default,
    )


@router.put("/statuses/{status_id}", response_model=CategoryStatusOut)
def update_status(
    status_id: int, data: CategoryStatusUpdate, db: Session = Depends(get_db)
):
    updates = data.model_dump(exclude_unset=True)
    status = category_service.update_status(db, status_id, **updates)
    if not status:
        raise HTTPException(status_code=404, detail="Status not found")
    return status


@router.delete("/statuses/{status_id}")
def delete_status(status_id: int, db: Session = Depends(get_db)):
    if not category_service.delete_status(db, status_id):
        raise HTTPException(status_code=404, detail="Status not found")
    return {"ok": True}
