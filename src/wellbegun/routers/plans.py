from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from wellbegun.database import get_db
from wellbegun.schemas.plan import (
    PlanCreate,
    PlanItemCreate,
    PlanItemOut,
    PlanItemUpdate,
    PlanOut,
    PlanUpdate,
)
from wellbegun.services import plan_service

router = APIRouter(prefix="/plans", tags=["plans"])


@router.get("/", response_model=list[PlanOut])
def list_plans(db: Session = Depends(get_db)):
    return plan_service.get_all(db)


@router.get("/{plan_id}", response_model=PlanOut)
def get_plan(plan_id: int, db: Session = Depends(get_db)):
    plan = plan_service.get_by_id(db, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan


@router.post("/", response_model=PlanOut, status_code=201)
def create_plan(data: PlanCreate, db: Session = Depends(get_db)):
    return plan_service.create(
        db,
        title=data.title,
        description=data.description,
        motivation=data.motivation,
        outcome=data.outcome,
        start_date=data.start_date,
        end_date=data.end_date,
    )


@router.put("/{plan_id}", response_model=PlanOut)
def update_plan(plan_id: int, data: PlanUpdate, db: Session = Depends(get_db)):
    updates = data.model_dump(exclude_unset=True)
    plan = plan_service.update(db, plan_id, **updates)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan


@router.delete("/{plan_id}")
def delete_plan(plan_id: int, db: Session = Depends(get_db)):
    if not plan_service.delete(db, plan_id):
        raise HTTPException(status_code=404, detail="Plan not found")
    return {"ok": True}


@router.post("/{plan_id}/activate", response_model=PlanOut)
def activate_plan(plan_id: int, db: Session = Depends(get_db)):
    plan = plan_service.activate(db, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan


@router.post("/{plan_id}/deactivate", response_model=PlanOut)
def deactivate_plan(plan_id: int, db: Session = Depends(get_db)):
    plan = plan_service.deactivate(db, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan


@router.post("/{plan_id}/archive", response_model=PlanOut)
def archive_plan(plan_id: int, db: Session = Depends(get_db)):
    plan = plan_service.archive(db, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan


# --------------- Item endpoints ---------------

@router.post("/{plan_id}/items", response_model=PlanItemOut, status_code=201)
def add_item(plan_id: int, data: PlanItemCreate, db: Session = Depends(get_db)):
    plan = plan_service.get_by_id(db, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan_service.add_item(
        db,
        plan_id=plan_id,
        activity_id=data.activity_id,
        position=data.position,
        is_done=data.is_done,
        notes=data.notes,
        header=data.header,
    )


@router.put("/items/{item_id}", response_model=PlanItemOut)
def update_item(item_id: int, data: PlanItemUpdate, db: Session = Depends(get_db)):
    updates = data.model_dump(exclude_unset=True)
    item = plan_service.update_item(db, item_id, **updates)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@router.delete("/items/{item_id}")
def remove_item(item_id: int, db: Session = Depends(get_db)):
    if not plan_service.remove_item(db, item_id):
        raise HTTPException(status_code=404, detail="Item not found")
    return {"ok": True}
