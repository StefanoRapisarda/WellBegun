from sqlalchemy.orm import Session

from log_input_panels.models.log import Activity
from log_input_panels.services.tag_service import create_entity_tag, delete_entity_tag, update_entity_tag
from log_input_panels.services.graph_cleanup import delete_entity_graph_data


def get_all(db: Session) -> list[Activity]:
    return db.query(Activity).order_by(Activity.created_at.desc()).all()


def get_by_id(db: Session, activity_id: int) -> Activity | None:
    return db.query(Activity).filter(Activity.id == activity_id).first()


def create(
    db: Session,
    title: str,
    description: str | None = None,
    duration: int | None = None,
    log_id: int | None = None,
    status: str = "todo",
) -> Activity:
    activity = Activity(
        title=title,
        description=description,
        duration=duration,
        log_id=log_id,
        status=status,
    )
    db.add(activity)
    db.flush()
    create_entity_tag(db, title, "activity", "activity", activity.id)
    from log_input_panels.services.active_context_service import attach_active_context_tags
    attach_active_context_tags(db, "activity", activity.id)
    db.commit()
    db.refresh(activity)
    return activity


def update(db: Session, activity_id: int, **kwargs) -> Activity | None:
    activity = get_by_id(db, activity_id)
    if not activity:
        return None
    for key, value in kwargs.items():
        if hasattr(activity, key):
            setattr(activity, key, value)
    if "title" in kwargs and kwargs["title"] is not None:
        update_entity_tag(db, "activity", activity_id, kwargs["title"])
    db.commit()
    db.refresh(activity)
    return activity


def delete(db: Session, activity_id: int) -> bool:
    activity = get_by_id(db, activity_id)
    if not activity:
        return False
    delete_entity_tag(db, "activity", activity_id)
    delete_entity_graph_data(db, "activity", activity_id)
    db.delete(activity)
    db.commit()
    return True


def activate(db: Session, activity_id: int) -> Activity | None:
    activity = get_by_id(db, activity_id)
    if not activity:
        return None
    activity.is_active = True
    db.commit()
    db.refresh(activity)
    return activity


def deactivate(db: Session, activity_id: int) -> Activity | None:
    activity = get_by_id(db, activity_id)
    if not activity:
        return None
    activity.is_active = False
    db.commit()
    db.refresh(activity)
    return activity


def deactivate_all(db: Session) -> int:
    count = db.query(Activity).filter(Activity.is_active == True).update({"is_active": False})
    db.commit()
    return count


def archive(db: Session, activity_id: int) -> Activity | None:
    activity = get_by_id(db, activity_id)
    if not activity:
        return None
    activity.is_archived = True
    db.commit()
    db.refresh(activity)
    return activity


def unarchive(db: Session, activity_id: int) -> Activity | None:
    activity = get_by_id(db, activity_id)
    if not activity:
        return None
    activity.is_archived = False
    db.commit()
    db.refresh(activity)
    return activity
