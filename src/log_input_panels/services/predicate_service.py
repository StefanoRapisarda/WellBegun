from sqlalchemy import select
from sqlalchemy.orm import Session

from log_input_panels.models.custom_predicate import CustomPredicate


def get_all_custom_predicates(db: Session) -> list[CustomPredicate]:
    return list(db.execute(select(CustomPredicate).order_by(CustomPredicate.id)).scalars().all())


def create_custom_predicate(
    db: Session,
    forward: str,
    reverse: str | None = None,
    category: str = "Custom",
) -> CustomPredicate:
    cp = CustomPredicate(forward=forward, reverse=reverse, category=category)
    db.add(cp)
    db.commit()
    db.refresh(cp)
    return cp


def update_custom_predicate(
    db: Session,
    predicate_id: int,
    forward: str | None = None,
    reverse: str | None = None,
    category: str | None = None,
) -> CustomPredicate | None:
    cp = db.get(CustomPredicate, predicate_id)
    if not cp:
        return None
    if forward is not None:
        cp.forward = forward
    if reverse is not None:
        cp.reverse = reverse
    if category is not None:
        cp.category = category
    db.commit()
    db.refresh(cp)
    return cp


def delete_custom_predicate(db: Session, predicate_id: int) -> bool:
    cp = db.get(CustomPredicate, predicate_id)
    if not cp:
        return False
    db.delete(cp)
    db.commit()
    return True
