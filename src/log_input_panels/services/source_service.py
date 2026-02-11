from sqlalchemy.orm import Session

from log_input_panels.models.source import Source
from log_input_panels.services.tag_service import create_entity_tag, delete_entity_tag, update_entity_tag
from log_input_panels.services.active_context_service import attach_active_context_tags
from log_input_panels.services.graph_cleanup import delete_entity_graph_data


def get_all(db: Session) -> list[Source]:
    return db.query(Source).order_by(Source.created_at.desc()).all()


def get_by_id(db: Session, source_id: int) -> Source | None:
    return db.query(Source).filter(Source.id == source_id).first()


def create(
    db: Session,
    title: str,
    description: str | None = None,
    content_url: str | None = None,
    source_type: str | None = None,
) -> Source:
    source = Source(
        title=title,
        description=description,
        content_url=content_url,
        source_type=source_type,
    )
    db.add(source)
    db.flush()
    create_entity_tag(db, title, "source", "source", source.id)
    attach_active_context_tags(db, "source", source.id)
    db.commit()
    db.refresh(source)
    return source


def update(db: Session, source_id: int, **kwargs) -> Source | None:
    source = get_by_id(db, source_id)
    if not source:
        return None
    for key, value in kwargs.items():
        if hasattr(source, key):
            setattr(source, key, value)
    if "title" in kwargs and kwargs["title"] is not None:
        update_entity_tag(db, "source", source_id, kwargs["title"])
    db.commit()
    db.refresh(source)
    return source


def delete(db: Session, source_id: int) -> bool:
    source = get_by_id(db, source_id)
    if not source:
        return False
    delete_entity_tag(db, "source", source_id)
    delete_entity_graph_data(db, "source", source_id)
    db.delete(source)
    db.commit()
    return True


def activate(db: Session, source_id: int) -> Source | None:
    source = get_by_id(db, source_id)
    if not source:
        return None
    source.is_active = True
    db.commit()
    db.refresh(source)
    return source


def deactivate(db: Session, source_id: int) -> Source | None:
    source = get_by_id(db, source_id)
    if not source:
        return None
    source.is_active = False
    db.commit()
    db.refresh(source)
    return source


def archive(db: Session, source_id: int) -> Source | None:
    source = get_by_id(db, source_id)
    if not source:
        return None
    source.is_archived = True
    db.commit()
    db.refresh(source)
    return source


def unarchive(db: Session, source_id: int) -> Source | None:
    source = get_by_id(db, source_id)
    if not source:
        return None
    source.is_archived = False
    db.commit()
    db.refresh(source)
    return source
