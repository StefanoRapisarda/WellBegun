from sqlalchemy.orm import Session

from wellbegun.models.actor import Actor
from wellbegun.services.tag_service import create_entity_tag, delete_entity_tag, update_entity_tag
from wellbegun.services.graph_cleanup import delete_entity_graph_data


def get_all(db: Session) -> list[Actor]:
    return db.query(Actor).order_by(Actor.created_at.desc()).all()


def get_by_id(db: Session, actor_id: int) -> Actor | None:
    return db.query(Actor).filter(Actor.id == actor_id).first()


def create(
    db: Session,
    full_name: str,
    role: str | None = None,
    affiliation: str | None = None,
    expertise: str | None = None,
    notes: str | None = None,
    email: str | None = None,
    url: str | None = None,
) -> Actor:
    actor = Actor(
        full_name=full_name,
        role=role,
        affiliation=affiliation,
        expertise=expertise,
        notes=notes,
        email=email,
        url=url,
    )
    db.add(actor)
    db.flush()
    create_entity_tag(db, full_name, "actor", "actor", actor.id)
    db.commit()
    db.refresh(actor)
    return actor


def update(db: Session, actor_id: int, **kwargs) -> Actor | None:
    actor = get_by_id(db, actor_id)
    if not actor:
        return None
    for key, value in kwargs.items():
        if hasattr(actor, key):
            setattr(actor, key, value)
    if "full_name" in kwargs and kwargs["full_name"] is not None:
        update_entity_tag(db, "actor", actor_id, kwargs["full_name"])
    db.commit()
    db.refresh(actor)
    return actor


def delete(db: Session, actor_id: int) -> bool:
    actor = get_by_id(db, actor_id)
    if not actor:
        return False
    delete_entity_tag(db, "actor", actor_id)
    delete_entity_graph_data(db, "actor", actor_id)
    db.delete(actor)
    db.commit()
    return True


def activate(db: Session, actor_id: int) -> Actor | None:
    actor = get_by_id(db, actor_id)
    if not actor:
        return None
    actor.is_active = True
    db.commit()
    db.refresh(actor)
    return actor


def deactivate(db: Session, actor_id: int) -> Actor | None:
    actor = get_by_id(db, actor_id)
    if not actor:
        return None
    actor.is_active = False
    db.commit()
    db.refresh(actor)
    return actor


def archive(db: Session, actor_id: int) -> Actor | None:
    actor = get_by_id(db, actor_id)
    if not actor:
        return None
    actor.is_archived = True
    db.commit()
    db.refresh(actor)
    return actor


def unarchive(db: Session, actor_id: int) -> Actor | None:
    actor = get_by_id(db, actor_id)
    if not actor:
        return None
    actor.is_archived = False
    db.commit()
    db.refresh(actor)
    return actor
