from datetime import datetime

from sqlalchemy import delete, func
from sqlalchemy.orm import Session

from wellbegun.models.tag import EntityTag, Tag


def create_entity_tag(
    db: Session,
    name: str,
    category: str,
    entity_type: str,
    entity_id: int,
) -> Tag:
    now = datetime.utcnow()
    full_tag = f"#{category}: {name}-{now.isoformat()}"
    tag = Tag(
        name=name,
        category=category,
        full_tag=full_tag,
        entity_type=entity_type,
        entity_id=entity_id,
        created_at=now,
    )
    db.add(tag)
    db.flush()
    return tag


def delete_entity_tag(db: Session, entity_type: str, entity_id: int) -> None:
    # Remove the entity's own tag and any EntityTags pointing FROM it
    tag = (
        db.query(Tag)
        .filter(Tag.entity_type == entity_type, Tag.entity_id == entity_id)
        .first()
    )
    if tag:
        db.execute(
            delete(EntityTag).where(EntityTag.tag_id == tag.id)
        )
        db.delete(tag)

    # Also remove any EntityTags where this entity is the TARGET
    # (e.g. wild tags attached to this entity). This prevents orphaned
    # tag attachments from leaking to new entities if IDs are reused.
    db.execute(
        delete(EntityTag).where(
            EntityTag.target_type == entity_type,
            EntityTag.target_id == entity_id,
        )
    )


def update_entity_tag(db: Session, entity_type: str, entity_id: int, new_name: str) -> Tag | None:
    tag = (
        db.query(Tag)
        .filter(Tag.entity_type == entity_type, Tag.entity_id == entity_id)
        .first()
    )
    if not tag:
        return None
    tag.name = new_name
    tag.full_tag = f"#{tag.category}: {new_name}-{tag.created_at.isoformat()}"
    db.flush()
    return tag


def search_tags(db: Session, query: str, limit: int = 20) -> list[Tag]:
    return (
        db.query(Tag)
        .filter(Tag.name.ilike(f"{query}%"))
        .order_by(Tag.name)
        .limit(limit)
        .all()
    )


def get_tag_usage_counts(db: Session) -> dict[int, int]:
    """Return {tag_id: count} for all tags that have at least one entity attachment."""
    rows = (
        db.query(EntityTag.tag_id, func.count(EntityTag.id))
        .group_by(EntityTag.tag_id)
        .all()
    )
    return {tag_id: count for tag_id, count in rows}


def get_all_tags(db: Session) -> list[Tag]:
    return db.query(Tag).order_by(Tag.name).all()


def get_tags_by_category(db: Session, category: str) -> list[Tag]:
    return (
        db.query(Tag)
        .filter(Tag.category == category)
        .order_by(Tag.name)
        .all()
    )


def _target_exists(db: Session, target_type: str, target_id: int) -> bool:
    """Verify the target entity actually exists before attaching a tag."""
    from wellbegun.models.note import Note
    from wellbegun.models.project import Project
    from wellbegun.models.log import Log, Activity
    from wellbegun.models.source import Source
    from wellbegun.models.actor import Actor

    from wellbegun.models.plan import Plan

    from wellbegun.models.collection import Collection

    model_map = {
        "note": Note, "project": Project, "log": Log,
        "activity": Activity, "source": Source, "actor": Actor,
        "plan": Plan, "collection": Collection,
    }
    model = model_map.get(target_type)
    if model is None:
        return True  # Unknown type — don't block
    return db.query(model).filter(model.id == target_id).first() is not None


def attach_tag(db: Session, tag_id: int, target_type: str, target_id: int) -> EntityTag | None:
    if not _target_exists(db, target_type, target_id):
        return None

    existing = (
        db.query(EntityTag)
        .filter(
            EntityTag.tag_id == tag_id,
            EntityTag.target_type == target_type,
            EntityTag.target_id == target_id,
        )
        .first()
    )
    if existing:
        return existing
    entity_tag = EntityTag(
        tag_id=tag_id,
        target_type=target_type,
        target_id=target_id,
        created_at=datetime.utcnow(),
    )
    db.add(entity_tag)
    db.flush()

    # Auto-create triple for entity tags
    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if tag and tag.entity_type is not None:
        from sqlalchemy.exc import IntegrityError
        from wellbegun.models.knowledge_triple import KnowledgeTriple
        from wellbegun.services.structural_relations import get_structural_predicate

        # Check both directions to avoid duplicate connections
        existing_triple = db.query(KnowledgeTriple).filter(
            KnowledgeTriple.subject_type == tag.entity_type,
            KnowledgeTriple.subject_id == tag.entity_id,
            KnowledgeTriple.object_type == target_type,
            KnowledgeTriple.object_id == target_id,
        ).first()
        if not existing_triple:
            existing_triple = db.query(KnowledgeTriple).filter(
                KnowledgeTriple.subject_type == target_type,
                KnowledgeTriple.subject_id == target_id,
                KnowledgeTriple.object_type == tag.entity_type,
                KnowledgeTriple.object_id == tag.entity_id,
            ).first()
        if not existing_triple:
            predicate = get_structural_predicate(tag.entity_type, target_type)

            # Override predicate for actor → activity when the activity
            # is tagged as a meeting (or similar event-type tags).
            if tag.entity_type == "actor" and target_type == "activity":
                meeting_tags = {"meeting", "meetings", "seminar", "workshop", "conference"}
                activity_tag_names = set()
                for et in db.query(EntityTag).filter(
                    EntityTag.target_type == "activity",
                    EntityTag.target_id == target_id,
                ).all():
                    t = db.query(Tag).filter(Tag.id == et.tag_id).first()
                    if t is not None:
                        activity_tag_names.add(t.name.lower())
                if meeting_tags & activity_tag_names:
                    predicate = "attends"

            triple = KnowledgeTriple(
                subject_type=tag.entity_type,
                subject_id=tag.entity_id,
                predicate=predicate,
                object_type=target_type,
                object_id=target_id,
            )
            db.add(triple)
            try:
                db.flush()
            except IntegrityError:
                db.rollback()
                # Re-add the entity_tag since rollback removed it
                db.add(entity_tag)
                db.flush()

    return entity_tag


def detach_tag(db: Session, tag_id: int, target_type: str, target_id: int) -> bool:
    # Auto-delete triple for entity tags
    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if tag and tag.entity_type is not None:
        from wellbegun.models.knowledge_triple import KnowledgeTriple

        db.query(KnowledgeTriple).filter(
            KnowledgeTriple.subject_type == tag.entity_type,
            KnowledgeTriple.subject_id == tag.entity_id,
            KnowledgeTriple.object_type == target_type,
            KnowledgeTriple.object_id == target_id,
        ).delete()

    result = db.execute(
        delete(EntityTag).where(
            EntityTag.tag_id == tag_id,
            EntityTag.target_type == target_type,
            EntityTag.target_id == target_id,
        )
    )
    return result.rowcount > 0


def get_entity_tags(db: Session, target_type: str, target_id: int) -> list[Tag]:
    entity_tags = (
        db.query(EntityTag)
        .filter(EntityTag.target_type == target_type, EntityTag.target_id == target_id)
        .all()
    )
    tag_ids = [et.tag_id for et in entity_tags]
    if not tag_ids:
        return []
    return db.query(Tag).filter(Tag.id.in_(tag_ids)).order_by(Tag.name).all()


def get_all_entity_tags_bulk(db: Session) -> dict[str, list[dict]]:
    """Return tags grouped by 'entity_type:entity_id' key for all entities.

    Single query approach to avoid N+1 per-node fetches.
    """
    all_et = db.query(EntityTag).all()
    if not all_et:
        return {}

    tag_ids = list({et.tag_id for et in all_et})
    all_tags = db.query(Tag).filter(Tag.id.in_(tag_ids)).all()
    tag_map = {t.id: t for t in all_tags}

    result: dict[str, list[dict]] = {}
    for et in all_et:
        key = f"{et.target_type}:{et.target_id}"
        tag = tag_map.get(et.tag_id)
        if not tag:
            continue
        result.setdefault(key, []).append({
            "id": tag.id,
            "name": tag.name,
            "category": tag.category,
            "full_tag": tag.full_tag,
            "color": tag.color,
            "entity_type": tag.entity_type,
            "entity_id": tag.entity_id,
            "created_at": tag.created_at.isoformat() if tag.created_at else None,
        })
    return result


def get_tag_links(db: Session, entity_type: str, entity_id: int) -> list[dict]:
    """Get all tag-based links for an entity.

    Returns two kinds of links:
    1. 'tagged_by': entities whose entity tag is attached to this entity
       (e.g., project tag on a note → the note is tagged by the project)
    2. 'tags': entities that have this entity's tag attached
       (e.g., notes with this project's tag → project tags those notes)
    """
    links: list[dict] = []

    # Direction 1: Find this entity's own entity tag, then find all entities that have it
    own_tag = (
        db.query(Tag)
        .filter(Tag.entity_type == entity_type, Tag.entity_id == entity_id)
        .first()
    )
    if own_tag:
        tagged_entities = (
            db.query(EntityTag)
            .filter(EntityTag.tag_id == own_tag.id)
            .all()
        )
        for et in tagged_entities:
            links.append({
                "entity_type": et.target_type,
                "entity_id": et.target_id,
                "direction": "tags",  # this entity tags the other
                "tag_name": own_tag.name,
                "tag_id": own_tag.id,
                "entity_tag_id": et.id,
            })

    # Direction 2: Find all entity tags attached TO this entity
    attached_tags = (
        db.query(EntityTag)
        .filter(EntityTag.target_type == entity_type, EntityTag.target_id == entity_id)
        .all()
    )
    tag_ids = [et.tag_id for et in attached_tags]
    if tag_ids:
        # Build a map from tag_id to entity_tag_id for the "tagged_by" direction
        tag_id_to_et_id = {et.tag_id: et.id for et in attached_tags}
        entity_tags = (
            db.query(Tag)
            .filter(Tag.id.in_(tag_ids), Tag.entity_type.isnot(None))
            .all()
        )
        for tag in entity_tags:
            links.append({
                "entity_type": tag.entity_type,
                "entity_id": tag.entity_id,
                "direction": "tagged_by",  # this entity is tagged by the other
                "tag_name": tag.name,
                "tag_id": tag.id,
                "entity_tag_id": tag_id_to_et_id.get(tag.id),
            })

    return links


def create_wild_tag(
    db: Session,
    name: str,
    description: str | None = None,
    category: str = "wild",
    is_system: bool = False,
    color: str | None = None,
) -> Tag:
    now = datetime.utcnow()
    full_tag = f"#{category}: {name}-{now.isoformat()}"
    tag = Tag(
        name=name,
        category=category,
        full_tag=full_tag,
        description=description,
        color=color,
        entity_type=None,
        entity_id=None,
        is_system=is_system,
        created_at=now,
    )
    db.add(tag)
    db.flush()
    return tag


def update_wild_tag(
    db: Session,
    tag_id: int,
    description: str | None = None,
    category: str | None = None,
    color: str | None = ...,
) -> Tag | None:
    tag = db.query(Tag).filter(Tag.id == tag_id, Tag.entity_id.is_(None)).first()
    if not tag:
        return None
    if description is not None:
        tag.description = description
    if category is not None:
        tag.category = category
        # Update full_tag to reflect new category
        tag.full_tag = f"#{category}: {tag.name}-{tag.created_at.isoformat()}"
    if color is not ...:
        tag.color = color
    db.flush()
    return tag


def move_category_tags(db: Session, from_category: str, to_category: str) -> int:
    """Move all standalone tags from one category to another."""
    tags = (
        db.query(Tag)
        .filter(Tag.category == from_category, Tag.entity_id.is_(None), Tag.is_system == False)
        .all()
    )
    count = 0
    for tag in tags:
        tag.category = to_category
        tag.full_tag = f"#{to_category}: {tag.name}-{tag.created_at.isoformat()}"
        count += 1
    db.flush()
    return count


def delete_wild_tag(db: Session, tag_id: int) -> bool:
    tag = db.query(Tag).filter(
        Tag.id == tag_id, Tag.entity_id.is_(None), Tag.is_system == False
    ).first()
    if not tag:
        return False
    db.execute(delete(EntityTag).where(EntityTag.tag_id == tag.id))
    db.delete(tag)
    return True


def get_tag_by_name(db: Session, name: str) -> Tag | None:
    return db.query(Tag).filter(Tag.name == name).first()


def get_or_create_wild_tag(db: Session, name: str) -> Tag:
    tag = get_tag_by_name(db, name)
    if tag:
        return tag
    return create_wild_tag(db, name)


def sync_inline_hashtags(
    db: Session, content: str, target_type: str, target_id: int
) -> list[Tag]:
    """Extract hashtags from content and attach them as entity_tags."""
    import re

    # Find all hashtags in content
    hashtag_pattern = r'#(\w+)'
    found_names = set(re.findall(hashtag_pattern, content or ''))

    attached_tags = []
    for name in found_names:
        tag = get_or_create_wild_tag(db, name)
        attach_tag(db, tag.id, target_type, target_id)
        attached_tags.append(tag)

    return attached_tags


def _deduplicate_tags(db: Session) -> None:
    """Remove duplicate standalone tags, keeping the one with the most attachments."""
    standalone = (
        db.query(Tag)
        .filter(Tag.entity_id.is_(None))
        .all()
    )
    # Group by (category, name)
    groups: dict[tuple[str, str], list[Tag]] = {}
    for tag in standalone:
        key = (tag.category, tag.name)
        groups.setdefault(key, []).append(tag)

    usage = get_tag_usage_counts(db)

    for (_cat, _name), tags_list in groups.items():
        if len(tags_list) <= 1:
            continue
        # Sort: most attachments first, then by id (oldest first as tiebreaker)
        tags_list.sort(key=lambda t: (-usage.get(t.id, 0), t.id))
        keeper = tags_list[0]
        for dup in tags_list[1:]:
            # Move any attachments from the duplicate to the keeper
            dup_attachments = db.query(EntityTag).filter(EntityTag.tag_id == dup.id).all()
            for et in dup_attachments:
                existing = (
                    db.query(EntityTag)
                    .filter(
                        EntityTag.tag_id == keeper.id,
                        EntityTag.target_type == et.target_type,
                        EntityTag.target_id == et.target_id,
                    )
                    .first()
                )
                if not existing:
                    et.tag_id = keeper.id
                else:
                    db.delete(et)
            db.delete(dup)


def _migrate_tags_to_category(db: Session, tag_names: list[str], old_categories: list[str], new_category: str) -> None:
    """Move existing tags from old categories to a new category, preserving attachments."""
    for name in tag_names:
        existing = (
            db.query(Tag)
            .filter(Tag.name == name, Tag.category.in_(old_categories), Tag.entity_id.is_(None))
            .first()
        )
        if existing:
            existing.category = new_category
            existing.full_tag = f"#{new_category}: {existing.name}-{existing.created_at.isoformat()}"


def seed_default_tags(db: Session) -> None:
    """Seed default tags for each entity category."""

    # Deduplicate: if multiple standalone tags share the same name within a
    # category, keep the one with the most attachments and delete the rest.
    _deduplicate_tags(db)

    # Move Milestone back to note if it was previously migrated to status
    _migrate_tags_to_category(
        db,
        ["Milestone"],
        ["status", "log"],
        "note",
    )

    # Phase 5: Clean up status tag category — status is now a column, not a tag
    status_tags = (
        db.query(Tag)
        .filter(Tag.category == "status", Tag.entity_id.is_(None))
        .all()
    )
    for tag in status_tags:
        db.execute(delete(EntityTag).where(EntityTag.tag_id == tag.id))
        db.delete(tag)

    defaults_by_category = {
        "activity": ["Meeting", "Coding", "Reading", "Writing", "Review", "Research", "Planning", "Designing"],
        "note": ["Idea", "Quote", "Definition", "Question", "Feature", "Milestone", "Goal", "Motivation", "Outcome"],
        "log": ["Daily Log", "Progress", "Decision", "Issue", "Reflection", "Insight", "Workspace", "Work", "Travel", "Health"],
        "project": ["Personal", "Work", "SideProject", "Experiment"],
    }
    for category, tag_names in defaults_by_category.items():
        for name in tag_names:
            existing = (
                db.query(Tag)
                .filter(Tag.category == category, Tag.name == name)
                .first()
            )
            if not existing:
                create_wild_tag(db, name, category=category, is_system=True)
            elif not existing.is_system:
                # Mark existing default tags as system
                existing.is_system = True
    # Remove legacy default tags that are no longer in the defaults list
    all_default_names = {(cat, name) for cat, names in defaults_by_category.items() for name in names}
    legacy = (
        db.query(Tag)
        .filter(Tag.is_system == True, Tag.entity_id.is_(None))
        .all()
    )
    for tag in legacy:
        if (tag.category, tag.name) not in all_default_names:
            db.execute(delete(EntityTag).where(EntityTag.tag_id == tag.id))
            db.delete(tag)
    # Tag existing plan-linked notes with Goal/Motivation/Outcome tags
    _tag_existing_role_notes(db)

    db.commit()


def _tag_existing_role_notes(db: Session) -> None:
    """One-time migration: attach Goal/Motivation/Outcome tags to notes
    already linked to plans via knowledge triples."""
    from wellbegun.models.knowledge_triple import KnowledgeTriple

    predicate_to_tag = {
        "has motivation": "Motivation",
        "has goal": "Goal",
        "has outcome": "Outcome",
    }

    role_triples = (
        db.query(KnowledgeTriple)
        .filter(
            KnowledgeTriple.subject_type == "plan",
            KnowledgeTriple.object_type == "note",
            KnowledgeTriple.predicate.in_(list(predicate_to_tag.keys())),
        )
        .all()
    )

    for triple in role_triples:
        tag_name = predicate_to_tag.get(triple.predicate)
        if not tag_name:
            continue
        tag = get_tag_by_name(db, tag_name)
        if not tag:
            continue
        # attach_tag is idempotent — skips if already attached
        attach_tag(db, tag.id, "note", triple.object_id)


def seed_wild_tags(db: Session) -> None:
    """Legacy function - now calls seed_default_tags."""
    seed_default_tags(db)
