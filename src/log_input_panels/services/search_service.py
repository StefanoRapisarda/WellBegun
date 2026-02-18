from datetime import datetime

from sqlalchemy import or_, func
from sqlalchemy.orm import Session

from log_input_panels.models import (
    Note, Log, Project, Activity, Source, Actor, Tag, EntityTag,
    ReadingList, Plan,
)


ALL_TYPES = ["note", "log", "project", "activity", "source", "actor", "reading_list", "plan"]

MODEL_CONFIG = {
    "note": {
        "model": Note,
        "text_fields": ["title", "content"],
        "title_field": "title",
        "desc_field": "content",
    },
    "log": {
        "model": Log,
        "text_fields": ["title", "content"],
        "title_field": "title",
        "desc_field": "content",
    },
    "project": {
        "model": Project,
        "text_fields": ["title", "description"],
        "title_field": "title",
        "desc_field": "description",
    },
    "activity": {
        "model": Activity,
        "text_fields": ["title", "description"],
        "title_field": "title",
        "desc_field": "description",
    },
    "source": {
        "model": Source,
        "text_fields": ["title", "description"],
        "title_field": "title",
        "desc_field": "description",
    },
    "actor": {
        "model": Actor,
        "text_fields": ["full_name", "role", "affiliation", "expertise", "notes"],
        "title_field": "full_name",
        "desc_field": "role",
    },
    "reading_list": {
        "model": ReadingList,
        "text_fields": ["title", "description"],
        "title_field": "title",
        "desc_field": "description",
    },
    "plan": {
        "model": Plan,
        "text_fields": ["title", "description", "motivation", "outcome"],
        "title_field": "title",
        "desc_field": "description",
    },
}


ARCHIVABLE_TYPES = {"project", "log", "note", "activity", "source", "actor", "plan"}


def search(
    db: Session,
    query: str | None = None,
    entity_types: list[str] | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    tag_ids: list[int] | None = None,
    tag_mode: str = "or",
    include_archived: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    types_to_search = entity_types if entity_types else ALL_TYPES
    results: list[dict] = []

    start_dt = datetime.fromisoformat(start_date) if start_date else None
    end_dt = datetime.fromisoformat(end_date + "T23:59:59") if end_date else None

    for entity_type in types_to_search:
        if entity_type not in MODEL_CONFIG:
            continue

        config = MODEL_CONFIG[entity_type]
        model = config["model"]
        q = db.query(model)

        # Text filter
        if query:
            text_filters = []
            for field_name in config["text_fields"]:
                field = getattr(model, field_name, None)
                if field is not None:
                    text_filters.append(field.ilike(f"%{query}%"))
            if text_filters:
                q = q.filter(or_(*text_filters))

        # Archived filter
        if not include_archived and entity_type in ARCHIVABLE_TYPES:
            q = q.filter(model.is_archived == False)  # noqa: E712

        # Date filter
        if start_dt:
            q = q.filter(
                or_(model.created_at >= start_dt, model.updated_at >= start_dt)
            )
        if end_dt:
            q = q.filter(
                or_(model.created_at <= end_dt, model.updated_at <= end_dt)
            )

        # Tag filter
        if tag_ids:
            if tag_mode == "and":
                # AND mode: entity must have ALL specified tags
                # Use HAVING COUNT to ensure entity has all tags
                matching_ids_subq = (
                    db.query(EntityTag.target_id)
                    .filter(
                        EntityTag.target_type == entity_type,
                        EntityTag.tag_id.in_(tag_ids),
                    )
                    .group_by(EntityTag.target_id)
                    .having(func.count(EntityTag.tag_id) == len(tag_ids))
                    .subquery()
                )
                q = q.filter(model.id.in_(matching_ids_subq))
            else:
                # OR mode: entity has at least one of the specified tags
                entity_tag_ids = (
                    db.query(EntityTag.target_id)
                    .filter(
                        EntityTag.target_type == entity_type,
                        EntityTag.tag_id.in_(tag_ids),
                    )
                    .subquery()
                )
                q = q.filter(model.id.in_(entity_tag_ids))

        items = q.order_by(model.updated_at.desc()).all()

        for item in items:
            # Get tags for this entity
            entity_tags = (
                db.query(Tag)
                .join(EntityTag, EntityTag.tag_id == Tag.id)
                .filter(
                    EntityTag.target_type == entity_type,
                    EntityTag.target_id == item.id,
                )
                .all()
            )

            results.append(
                {
                    "type": entity_type,
                    "id": item.id,
                    "title": getattr(item, config["title_field"], ""),
                    "description": getattr(item, config["desc_field"], None),
                    "created_at": item.created_at,
                    "updated_at": item.updated_at,
                    "tags": entity_tags,
                }
            )

    # Sort all results by updated_at desc
    results.sort(key=lambda r: r["updated_at"], reverse=True)

    return results[offset : offset + limit]
