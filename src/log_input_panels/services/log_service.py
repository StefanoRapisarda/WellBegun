from sqlalchemy.orm import Session

from log_input_panels.models.log import Log
from log_input_panels.services.tag_service import create_entity_tag, delete_entity_tag, update_entity_tag
from log_input_panels.services.active_context_service import attach_active_context_tags
from log_input_panels.services.graph_cleanup import delete_entity_graph_data


def get_all_logs(db: Session) -> list[Log]:
    return db.query(Log).order_by(Log.created_at.desc()).all()


def get_log_by_id(db: Session, log_id: int) -> Log | None:
    return db.query(Log).filter(Log.id == log_id).first()


def create_log(
    db: Session,
    log_type: str,
    title: str,
    content: str | None = None,
) -> Log:
    log = Log(log_type=log_type, title=title, content=content)
    db.add(log)
    db.flush()
    create_entity_tag(db, title, "log", "log", log.id)
    attach_active_context_tags(db, "log", log.id)
    db.commit()
    db.refresh(log)
    return log


def update_log(db: Session, log_id: int, **kwargs) -> Log | None:
    log = get_log_by_id(db, log_id)
    if not log:
        return None
    for key, value in kwargs.items():
        if hasattr(log, key):
            setattr(log, key, value)
    if "title" in kwargs and kwargs["title"] is not None:
        update_entity_tag(db, "log", log_id, kwargs["title"])
    db.commit()
    db.refresh(log)
    return log


def delete_log(db: Session, log_id: int) -> bool:
    log = get_log_by_id(db, log_id)
    if not log:
        return False
    delete_entity_tag(db, "log", log_id)
    delete_entity_graph_data(db, "log", log_id)
    db.delete(log)
    db.commit()
    return True


def activate_log(db: Session, log_id: int) -> Log | None:
    log = get_log_by_id(db, log_id)
    if not log:
        return None
    log.is_active = True
    db.commit()
    db.refresh(log)
    return log


def deactivate_log(db: Session, log_id: int) -> Log | None:
    log = get_log_by_id(db, log_id)
    if not log:
        return None
    log.is_active = False
    db.commit()
    db.refresh(log)
    return log


def get_active_logs(db: Session) -> list[Log]:
    return db.query(Log).filter(Log.is_active.is_(True)).all()


def archive_log(db: Session, log_id: int) -> Log | None:
    log = get_log_by_id(db, log_id)
    if not log:
        return None
    log.is_archived = True
    db.commit()
    db.refresh(log)
    return log


def unarchive_log(db: Session, log_id: int) -> Log | None:
    log = get_log_by_id(db, log_id)
    if not log:
        return None
    log.is_archived = False
    db.commit()
    db.refresh(log)
    return log
