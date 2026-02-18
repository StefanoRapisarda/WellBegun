from sqlalchemy.orm import Session

from wellbegun.models.actor import Actor
from wellbegun.models.log import Activity, Log
from wellbegun.models.project import Project
from wellbegun.models.plan import Plan
from wellbegun.models.reading_list import ReadingList
from wellbegun.models.source import Source
from wellbegun.models.tag import Tag
from wellbegun.services.tag_service import attach_tag


def get_active_context(db: Session) -> dict:
    return {
        "projects": db.query(Project).filter(Project.is_active.is_(True)).all(),
        "logs": db.query(Log).filter(Log.is_active.is_(True)).all(),
        "activities": db.query(Activity).filter(Activity.is_active.is_(True)).all(),
        "sources": db.query(Source).filter(Source.is_active.is_(True)).all(),
        "actors": db.query(Actor).filter(Actor.is_active.is_(True)).all(),
        "reading_lists": db.query(ReadingList).filter(ReadingList.is_active.is_(True)).all(),
        "plans": db.query(Plan).filter(Plan.is_active.is_(True)).all(),
    }


def attach_active_context_tags(db: Session, target_type: str, target_id: int) -> None:
    """Find tags for all active entities and attach them to the target.

    All active entities tag all new entities (no type restrictions).
    """
    active = get_active_context(db)

    entity_specs = [
        ("project", [(p.id, "project") for p in active["projects"]]),
        ("log", [(l.id, "log") for l in active["logs"]]),
        ("activity", [(a.id, "activity") for a in active["activities"]]),
        ("source", [(s.id, "source") for s in active["sources"]]),
        ("actor", [(a.id, "actor") for a in active["actors"]]),
        ("reading_list", [(r.id, "reading_list") for r in active["reading_lists"]]),
        ("plan", [(p.id, "plan") for p in active["plans"]]),
    ]

    for entity_type, items in entity_specs:
        for entity_id, etype in items:
            tag = (
                db.query(Tag)
                .filter(Tag.entity_type == entity_type, Tag.entity_id == entity_id)
                .first()
            )
            if tag:
                attach_tag(db, tag.id, target_type, target_id)
