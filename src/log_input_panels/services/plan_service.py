from sqlalchemy.orm import Session, joinedload

from log_input_panels.models.plan import Plan, PlanItem
from log_input_panels.services.graph_cleanup import delete_entity_graph_data
from log_input_panels.services.tag_service import (
    create_entity_tag,
    delete_entity_tag,
    update_entity_tag,
)


# --------------- Plan CRUD ---------------

def get_all(db: Session) -> list[Plan]:
    return (
        db.query(Plan)
        .options(joinedload(Plan.items))
        .order_by(Plan.created_at.desc())
        .all()
    )


def get_by_id(db: Session, plan_id: int) -> Plan | None:
    return (
        db.query(Plan)
        .options(joinedload(Plan.items))
        .filter(Plan.id == plan_id)
        .first()
    )


def create(
    db: Session,
    title: str,
    description: str | None = None,
    motivation: str | None = None,
    outcome: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> Plan:
    plan = Plan(
        title=title,
        description=description,
        motivation=motivation,
        outcome=outcome,
        start_date=start_date,
        end_date=end_date,
    )
    db.add(plan)
    db.flush()
    create_entity_tag(db, title, "plan", "plan", plan.id)
    db.commit()
    db.refresh(plan)
    return plan


def update(db: Session, plan_id: int, **kwargs) -> Plan | None:
    plan = get_by_id(db, plan_id)
    if not plan:
        return None
    for key, value in kwargs.items():
        if hasattr(plan, key):
            setattr(plan, key, value)
    if "title" in kwargs and kwargs["title"] is not None:
        update_entity_tag(db, "plan", plan_id, kwargs["title"])
    db.commit()
    db.refresh(plan)
    return plan


def delete(db: Session, plan_id: int) -> bool:
    plan = get_by_id(db, plan_id)
    if not plan:
        return False
    delete_entity_tag(db, "plan", plan_id)
    delete_entity_graph_data(db, "plan", plan_id)
    db.delete(plan)
    db.commit()
    return True


def activate(db: Session, plan_id: int) -> Plan | None:
    plan = get_by_id(db, plan_id)
    if not plan:
        return None
    plan.is_active = True
    db.commit()
    db.refresh(plan)
    return plan


def deactivate(db: Session, plan_id: int) -> Plan | None:
    plan = get_by_id(db, plan_id)
    if not plan:
        return None
    plan.is_active = False
    db.commit()
    db.refresh(plan)
    return plan


def archive(db: Session, plan_id: int) -> Plan | None:
    plan = get_by_id(db, plan_id)
    if not plan:
        return None
    plan.is_archived = True
    db.commit()
    db.refresh(plan)
    return plan


def unarchive(db: Session, plan_id: int) -> Plan | None:
    plan = get_by_id(db, plan_id)
    if not plan:
        return None
    plan.is_archived = False
    db.commit()
    db.refresh(plan)
    return plan


# --------------- Item CRUD ---------------

def get_items(db: Session, plan_id: int) -> list[PlanItem]:
    return (
        db.query(PlanItem)
        .filter(PlanItem.plan_id == plan_id)
        .order_by(PlanItem.position)
        .all()
    )


def add_item(
    db: Session,
    plan_id: int,
    activity_id: int,
    position: int = 0,
    is_done: bool = False,
    notes: str | None = None,
    header: str | None = None,
) -> PlanItem:
    item = PlanItem(
        plan_id=plan_id,
        activity_id=activity_id,
        position=position,
        is_done=is_done,
        notes=notes,
        header=header,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_item(db: Session, item_id: int, **kwargs) -> PlanItem | None:
    item = db.query(PlanItem).filter(PlanItem.id == item_id).first()
    if not item:
        return None
    for key, value in kwargs.items():
        if hasattr(item, key):
            setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


def remove_item(db: Session, item_id: int) -> bool:
    item = db.query(PlanItem).filter(PlanItem.id == item_id).first()
    if not item:
        return False
    db.delete(item)
    db.commit()
    return True
