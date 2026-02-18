from sqlalchemy import delete, or_
from sqlalchemy.orm import Session

from log_input_panels.models.knowledge_triple import KnowledgeTriple
from log_input_panels.models.board_node import BoardNode
from log_input_panels.services.structural_relations import get_structural_predicate


def get_default_predicate(subject_type: str, object_type: str) -> str:
    """Return the default verb for a given (subject, object) type pair."""
    return get_structural_predicate(subject_type, object_type)


def get_all_triples(db: Session) -> list[KnowledgeTriple]:
    return db.query(KnowledgeTriple).order_by(KnowledgeTriple.created_at.desc()).all()


def get_triples_for_entity(
    db: Session, entity_type: str, entity_id: int
) -> list[KnowledgeTriple]:
    return (
        db.query(KnowledgeTriple)
        .filter(
            or_(
                (KnowledgeTriple.subject_type == entity_type)
                & (KnowledgeTriple.subject_id == entity_id),
                (KnowledgeTriple.object_type == entity_type)
                & (KnowledgeTriple.object_id == entity_id),
            )
        )
        .order_by(KnowledgeTriple.created_at.desc())
        .all()
    )


def create_triple(
    db: Session,
    subject_type: str,
    subject_id: int,
    predicate: str,
    object_type: str,
    object_id: int,
) -> KnowledgeTriple:
    """Create or return existing triple (upsert by unique constraint).

    Matches on (subject_type, subject_id, object_type, object_id).
    If a triple exists with a different predicate, updates it.
    """
    existing = (
        db.query(KnowledgeTriple)
        .filter(
            KnowledgeTriple.subject_type == subject_type,
            KnowledgeTriple.subject_id == subject_id,
            KnowledgeTriple.object_type == object_type,
            KnowledgeTriple.object_id == object_id,
        )
        .first()
    )
    if existing:
        if existing.predicate != predicate:
            existing.predicate = predicate
            db.flush()
        return existing
    triple = KnowledgeTriple(
        subject_type=subject_type,
        subject_id=subject_id,
        predicate=predicate,
        object_type=object_type,
        object_id=object_id,
    )
    db.add(triple)
    db.commit()
    db.refresh(triple)
    return triple


def swap_triple_direction(db: Session, triple_id: int) -> KnowledgeTriple | None:
    """Swap subject and object of a triple, updating the predicate to match."""
    from log_input_panels.models.tag import Tag, EntityTag

    triple = db.query(KnowledgeTriple).filter(KnowledgeTriple.id == triple_id).first()
    if not triple:
        return None
    # Swap fields
    old_sub_type, old_sub_id = triple.subject_type, triple.subject_id
    triple.subject_type = triple.object_type
    triple.subject_id = triple.object_id
    triple.object_type = old_sub_type
    triple.object_id = old_sub_id

    # Sync tag swap: remove old tag link, add new
    old_tag = db.query(Tag).filter(
        Tag.entity_type == old_sub_type, Tag.entity_id == old_sub_id
    ).first()
    if old_tag:
        db.execute(delete(EntityTag).where(
            EntityTag.tag_id == old_tag.id,
            EntityTag.target_type == triple.object_type,
            EntityTag.target_id == triple.object_id,
        ))
    # New subject → new object
    new_tag = db.query(Tag).filter(
        Tag.entity_type == triple.subject_type, Tag.entity_id == triple.subject_id
    ).first()
    if new_tag:
        existing_et = db.query(EntityTag).filter(
            EntityTag.tag_id == new_tag.id,
            EntityTag.target_type == triple.object_type,
            EntityTag.target_id == triple.object_id,
        ).first()
        if not existing_et:
            db.add(EntityTag(
                tag_id=new_tag.id,
                target_type=triple.object_type,
                target_id=triple.object_id,
            ))

    db.commit()
    db.refresh(triple)
    return triple


def update_triple_predicate(
    db: Session, triple_id: int, predicate: str
) -> KnowledgeTriple | None:
    triple = db.query(KnowledgeTriple).filter(KnowledgeTriple.id == triple_id).first()
    if not triple:
        return None
    triple.predicate = predicate
    db.commit()
    db.refresh(triple)
    return triple


def delete_triple(db: Session, triple_id: int) -> bool:
    triple = db.query(KnowledgeTriple).filter(KnowledgeTriple.id == triple_id).first()
    if not triple:
        return False
    # Auto-detach entity tag
    from log_input_panels.models.tag import Tag, EntityTag

    subject_tag = db.query(Tag).filter(
        Tag.entity_type == triple.subject_type,
        Tag.entity_id == triple.subject_id,
    ).first()
    if subject_tag:
        db.execute(
            delete(EntityTag).where(
                EntityTag.tag_id == subject_tag.id,
                EntityTag.target_type == triple.object_type,
                EntityTag.target_id == triple.object_id,
            )
        )
    db.delete(triple)
    db.commit()
    return True


def delete_triples_for_entity(db: Session, entity_type: str, entity_id: int) -> int:
    """Delete all triples where entity is subject OR object. Returns count deleted."""
    triples = (
        db.query(KnowledgeTriple)
        .filter(
            or_(
                (KnowledgeTriple.subject_type == entity_type)
                & (KnowledgeTriple.subject_id == entity_id),
                (KnowledgeTriple.object_type == entity_type)
                & (KnowledgeTriple.object_id == entity_id),
            )
        )
        .all()
    )
    count = len(triples)
    for t in triples:
        db.delete(t)
    return count


def populate_from_focus(
    db: Session,
    project_ids: list[int],
    activity_ids: list[int],
) -> dict:
    """Populate the graph board with entities from a focus selection.

    1. Finds entity tags for the selected projects/activities
    2. Finds all entities tagged with those tags
    3. Creates board nodes (only for new entities, preserving existing positions)
    4. Creates knowledge triples for the tag-based relationships
    """
    from log_input_panels.models.tag import Tag, EntityTag

    # 1. Find entity tags for focused projects/activities
    tag_filters = []
    if project_ids:
        tag_filters.append(
            (Tag.entity_type == "project") & (Tag.entity_id.in_(project_ids))
        )
    if activity_ids:
        tag_filters.append(
            (Tag.entity_type == "activity") & (Tag.entity_id.in_(activity_ids))
        )

    entity_tags = []
    if tag_filters:
        entity_tags = db.query(Tag).filter(or_(*tag_filters)).all()

    tag_ids = [t.id for t in entity_tags]

    # 2. Find all entities tagged with these tags
    tagged_records = []
    if tag_ids:
        tagged_records = (
            db.query(EntityTag).filter(EntityTag.tag_id.in_(tag_ids)).all()
        )

    # 3. Collect all entities that should be on the board, validating they exist
    from log_input_panels.models import (
        Project, Activity, Note, Log, Source, Actor, ReadingList,
    )

    MODEL_MAP: dict[str, type] = {
        "project": Project,
        "activity": Activity,
        "note": Note,
        "log": Log,
        "source": Source,
        "actor": Actor,
        "reading_list": ReadingList,
    }

    def entity_exists(etype: str, eid: int) -> bool:
        model = MODEL_MAP.get(etype)
        if not model:
            return False
        return db.query(model.id).filter(model.id == eid).first() is not None

    entities: set[tuple[str, int]] = set()
    for pid in project_ids:
        entities.add(("project", pid))
    for aid in activity_ids:
        entities.add(("activity", aid))
    for et in tagged_records:
        if entity_exists(et.target_type, et.target_id):
            entities.add((et.target_type, et.target_id))
        else:
            # Clean up orphaned EntityTag
            db.delete(et)

    # 4. Find which entities already have board nodes; remove stale ones
    existing_nodes = db.query(BoardNode).all()
    valid_nodes = []
    for n in existing_nodes:
        if entity_exists(n.entity_type, n.entity_id):
            valid_nodes.append(n)
        else:
            db.delete(n)
    # Commit orphaned EntityTag and stale BoardNode deletions
    db.commit()

    existing_keys = {(n.entity_type, n.entity_id) for n in valid_nodes}
    # Also track max x/y for layout offset
    max_x = max((n.x for n in valid_nodes), default=0)

    new_entities = entities - existing_keys

    # 5. Layout new entities in columns by type, offset from existing content
    TYPE_ORDER = [
        "project", "activity", "log", "note",
        "source", "actor", "reading_list",
    ]
    type_groups: dict[str, list[int]] = {}
    for etype, eid in new_entities:
        type_groups.setdefault(etype, []).append(eid)

    start_x = max_x + 250 if valid_nodes else 100
    nodes_to_create = []
    col = 0
    for etype in TYPE_ORDER:
        ids = type_groups.get(etype, [])
        if not ids:
            continue
        for row, eid in enumerate(sorted(ids)):
            x = start_x + col * 200
            y = 100 + row * 100
            nodes_to_create.append({
                "entity_type": etype,
                "entity_id": eid,
                "x": x,
                "y": y,
            })
        col += 1

    if nodes_to_create:
        # Bulk create only (don't update existing)
        from datetime import datetime

        for data in nodes_to_create:
            node = BoardNode(
                entity_type=data["entity_type"],
                entity_id=data["entity_id"],
                x=data["x"],
                y=data["y"],
            )
            db.add(node)
        db.commit()

    # 6. Create knowledge triples for tag relationships (only for validated entities)
    triples_created = 0
    for tag in entity_tags:
        tagged_with_this = [
            et for et in tagged_records
            if et.tag_id == tag.id and (et.target_type, et.target_id) in entities
        ]
        for et in tagged_with_this:
            predicate = get_default_predicate(tag.entity_type, et.target_type)
            # create_triple does upsert, won't duplicate
            create_triple(
                db,
                tag.entity_type, tag.entity_id,
                predicate,
                et.target_type, et.target_id,
            )
            triples_created += 1

    return {
        "entities_total": len(entities),
        "nodes_created": len(nodes_to_create),
        "triples_created": triples_created,
    }


def populate_all(db: Session) -> dict:
    """Populate the graph board with ALL entities in the system.

    Unlike populate_from_focus which only includes entities related to a focus
    selection, this queries every entity table directly and creates board nodes
    and triples for all of them.
    """
    from log_input_panels.models.tag import Tag, EntityTag
    from log_input_panels.models import (
        Project, Activity, Note, Log, Source, Actor, ReadingList,
    )

    MODEL_MAP: dict[str, type] = {
        "project": Project,
        "activity": Activity,
        "note": Note,
        "log": Log,
        "source": Source,
        "actor": Actor,
        "reading_list": ReadingList,
    }

    # 1. Collect ALL entities from all model tables
    entities: set[tuple[str, int]] = set()
    for etype, model in MODEL_MAP.items():
        ids = db.query(model.id).all()
        for (eid,) in ids:
            entities.add((etype, eid))

    def entity_exists(etype: str, eid: int) -> bool:
        return (etype, eid) in entities

    # 2. Clean stale board nodes (same logic as populate_from_focus)
    existing_nodes = db.query(BoardNode).all()
    valid_nodes = []
    for n in existing_nodes:
        if entity_exists(n.entity_type, n.entity_id):
            valid_nodes.append(n)
        else:
            db.delete(n)
    db.commit()

    existing_keys = {(n.entity_type, n.entity_id) for n in valid_nodes}
    max_x = max((n.x for n in valid_nodes), default=0)

    new_entities = entities - existing_keys

    # 3. Layout new entities in columns by type
    TYPE_ORDER = [
        "project", "activity", "log", "note",
        "source", "actor", "reading_list",
    ]
    type_groups: dict[str, list[int]] = {}
    for etype, eid in new_entities:
        type_groups.setdefault(etype, []).append(eid)

    start_x = max_x + 250 if valid_nodes else 100
    nodes_to_create = []
    col = 0
    for etype in TYPE_ORDER:
        ids = type_groups.get(etype, [])
        if not ids:
            continue
        for row, eid in enumerate(sorted(ids)):
            x = start_x + col * 200
            y = 100 + row * 100
            nodes_to_create.append({
                "entity_type": etype,
                "entity_id": eid,
                "x": x,
                "y": y,
            })
        col += 1

    if nodes_to_create:
        for data in nodes_to_create:
            node = BoardNode(
                entity_type=data["entity_type"],
                entity_id=data["entity_id"],
                x=data["x"],
                y=data["y"],
            )
            db.add(node)
        db.commit()

    # 4. Create triples from ALL EntityTag relationships
    all_entity_tags = db.query(Tag).all()
    all_tagged_records = db.query(EntityTag).all()

    triples_created = 0
    for tag in all_entity_tags:
        # Only create triples where both the tag source and target exist
        if not entity_exists(tag.entity_type, tag.entity_id):
            continue
        tagged_with_this = [
            et for et in all_tagged_records
            if et.tag_id == tag.id and entity_exists(et.target_type, et.target_id)
        ]
        for et in tagged_with_this:
            predicate = get_default_predicate(tag.entity_type, et.target_type)
            create_triple(
                db,
                tag.entity_type, tag.entity_id,
                predicate,
                et.target_type, et.target_id,
            )
            triples_created += 1

    return {
        "entities_total": len(entities),
        "nodes_created": len(nodes_to_create),
        "triples_created": triples_created,
    }
