from sqlalchemy.orm import Session

from log_input_panels.models.note import Note
from log_input_panels.services.tag_service import create_entity_tag, delete_entity_tag, update_entity_tag
from log_input_panels.services.active_context_service import attach_active_context_tags
from log_input_panels.services.graph_cleanup import delete_entity_graph_data


def get_all(db: Session) -> list[Note]:
    return db.query(Note).order_by(Note.created_at.desc()).all()


def get_by_id(db: Session, note_id: int) -> Note | None:
    return db.query(Note).filter(Note.id == note_id).first()


def create(
    db: Session,
    title: str,
    content: str | None = None,
    skip_context_tags: bool = False,
) -> Note:
    note = Note(title=title, content=content)
    db.add(note)
    db.flush()
    create_entity_tag(db, title, "note", "note", note.id)
    if not skip_context_tags:
        attach_active_context_tags(db, "note", note.id)
    db.commit()
    db.refresh(note)
    return note


def update(db: Session, note_id: int, **kwargs) -> Note | None:
    note = get_by_id(db, note_id)
    if not note:
        return None
    for key, value in kwargs.items():
        if hasattr(note, key):
            setattr(note, key, value)
    if "title" in kwargs and kwargs["title"] is not None:
        update_entity_tag(db, "note", note_id, kwargs["title"])
    db.commit()
    db.refresh(note)
    return note


def delete(db: Session, note_id: int) -> bool:
    note = get_by_id(db, note_id)
    if not note:
        return False
    delete_entity_tag(db, "note", note_id)
    delete_entity_graph_data(db, "note", note_id)
    db.delete(note)
    db.commit()
    return True


def archive(db: Session, note_id: int) -> Note | None:
    note = get_by_id(db, note_id)
    if not note:
        return None
    note.is_archived = True
    db.commit()
    db.refresh(note)
    return note


def unarchive(db: Session, note_id: int) -> Note | None:
    note = get_by_id(db, note_id)
    if not note:
        return None
    note.is_archived = False
    db.commit()
    db.refresh(note)
    return note
