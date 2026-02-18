"""One-time migration: sync existing EntityTags ↔ KnowledgeTriples."""

from sqlalchemy.orm import Session

from wellbegun.models.knowledge_triple import KnowledgeTriple
from wellbegun.models.tag import EntityTag, Tag
from wellbegun.services.structural_relations import (
    STRUCTURAL_PREDICATES,
    get_structural_predicate,
)


def sync_tags_to_triples(db: Session) -> int:
    """For every EntityTag backed by an entity tag, create a KnowledgeTriple if missing."""
    all_entity_tags = db.query(EntityTag).all()
    tag_map: dict[int, Tag] = {}
    created = 0
    for et in all_entity_tags:
        tag = tag_map.get(et.tag_id)
        if tag is None:
            tag = db.query(Tag).filter(Tag.id == et.tag_id).first()
            if tag:
                tag_map[et.tag_id] = tag
        if not tag or tag.entity_type is None:
            continue
        existing = (
            db.query(KnowledgeTriple)
            .filter(
                KnowledgeTriple.subject_type == tag.entity_type,
                KnowledgeTriple.subject_id == tag.entity_id,
                KnowledgeTriple.object_type == et.target_type,
                KnowledgeTriple.object_id == et.target_id,
            )
            .first()
        )
        if not existing:
            predicate = get_structural_predicate(tag.entity_type, et.target_type)
            db.add(KnowledgeTriple(
                subject_type=tag.entity_type,
                subject_id=tag.entity_id,
                predicate=predicate,
                object_type=et.target_type,
                object_id=et.target_id,
            ))
            created += 1
    db.flush()
    return created


def sync_triples_to_tags(db: Session) -> int:
    """For every KnowledgeTriple, create an EntityTag if the subject has an entity tag."""
    all_triples = db.query(KnowledgeTriple).all()
    created = 0
    for triple in all_triples:
        subject_tag = (
            db.query(Tag)
            .filter(
                Tag.entity_type == triple.subject_type,
                Tag.entity_id == triple.subject_id,
            )
            .first()
        )
        if not subject_tag:
            continue
        existing_et = (
            db.query(EntityTag)
            .filter(
                EntityTag.tag_id == subject_tag.id,
                EntityTag.target_type == triple.object_type,
                EntityTag.target_id == triple.object_id,
            )
            .first()
        )
        if not existing_et:
            db.add(EntityTag(
                tag_id=subject_tag.id,
                target_type=triple.object_type,
                target_id=triple.object_id,
            ))
            created += 1
    db.flush()
    return created


def update_legacy_predicates(db: Session) -> int:
    """Update triples whose predicate doesn't match the structural default.

    Only updates triples whose predicate is NOT a known semantic relation
    (i.e., triples that were created with old/mismatched structural predicates).
    """
    from wellbegun.services.structural_relations import SEMANTIC_RELATIONS

    # Build set of known semantic predicate keys
    semantic_keys: set[str] = set()
    for predicates in SEMANTIC_RELATIONS.values():
        for pred in predicates:
            semantic_keys.add(pred["forward"])
            semantic_keys.add(pred["reverse"])

    all_triples = db.query(KnowledgeTriple).all()
    updated = 0
    for triple in all_triples:
        expected = get_structural_predicate(triple.subject_type, triple.object_type)
        # Don't overwrite semantic predicates or predicates that already match
        if triple.predicate == expected:
            continue
        if triple.predicate in semantic_keys:
            continue
        # Check if predicate is a known structural predicate (just for a different type pair)
        structural_values = set(STRUCTURAL_PREDICATES.values())
        if triple.predicate in structural_values:
            # It's a valid structural predicate, just possibly for the wrong pair — update
            triple.predicate = expected
            updated += 1
        elif triple.predicate == "related to":
            triple.predicate = expected
            updated += 1
    db.flush()
    return updated
