from sqlalchemy.orm import Session, joinedload

from wellbegun.models.plan import Plan
from wellbegun.models.collection import Collection
from wellbegun.services.graph_cleanup import delete_entity_graph_data
from wellbegun.services.tag_service import (
    create_entity_tag,
    delete_entity_tag,
    update_entity_tag,
)
from wellbegun.services import knowledge_service


def ensure_plan_collection(
    db: Session, plan_id: int, section: str, member_entity_type: str
) -> Collection:
    """Find or create the collection for a plan section (activities/sources/actors).

    Looks for an existing plan→collection triple with predicate "has {section}",
    then verifies the collection exists. Creates one if not found.
    """
    from wellbegun.services import collection_service, category_service

    predicate = f"has {section}"
    triples = knowledge_service.get_triples_for_entity(db, "plan", plan_id)
    for t in triples:
        if (
            t.subject_type == "plan"
            and t.subject_id == plan_id
            and t.object_type == "collection"
            and t.predicate == predicate
        ):
            coll = collection_service.get_by_id(db, t.object_id)
            if coll:
                return coll

    # Not found — create
    plan = get_by_id(db, plan_id)
    if not plan:
        raise ValueError(f"Plan {plan_id} not found")

    # Use base section type for category lookup (e.g. "activities:Research" → "activities")
    base_section = section.split(":")[0]
    if member_entity_type == "*":
        category = category_service.get_by_slug(db, "plan_items")
    else:
        category = category_service.get_by_slug(db, f"plan_{base_section}")
    if not category:
        raise ValueError(f"Category not found — run seed_categories first")

    coll = collection_service.create(db, title=f"{plan.title} {section}", category_id=category.id)
    knowledge_service.create_triple(
        db,
        subject_type="plan",
        subject_id=plan_id,
        predicate=predicate,
        object_type="collection",
        object_id=coll.id,
    )
    return coll


# --------------- Plan CRUD ---------------

def get_all(db: Session) -> list[Plan]:
    return (
        db.query(Plan)
        .options(joinedload(Plan.items), joinedload(Plan.activities))
        .order_by(Plan.created_at.desc())
        .all()
    )


def get_by_id(db: Session, plan_id: int) -> Plan | None:
    return (
        db.query(Plan)
        .options(joinedload(Plan.items), joinedload(Plan.activities))
        .filter(Plan.id == plan_id)
        .first()
    )


def create(
    db: Session,
    title: str,
    description: str | None = None,
    motivation: str | None = None,
    outcome: str | None = None,
    goal: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    status: str = "planned",
) -> Plan:
    plan = Plan(
        title=title,
        description=description,
        motivation=motivation,
        outcome=outcome,
        goal=goal,
        start_date=start_date,
        end_date=end_date,
        status=status,
    )
    db.add(plan)
    db.flush()
    create_entity_tag(db, title, "plan", "plan", plan.id)
    db.commit()
    db.refresh(plan)

    return plan


def update(db: Session, plan_id: int, **kwargs) -> Plan | None:
    plan = get_by_id(db, plan_id)
    if not plan:
        return None
    for key, value in kwargs.items():
        if hasattr(plan, key):
            setattr(plan, key, value)
    if "title" in kwargs and kwargs["title"] is not None:
        update_entity_tag(db, "plan", plan_id, kwargs["title"])
    db.commit()
    db.refresh(plan)
    return plan


def delete(db: Session, plan_id: int) -> bool:
    plan = get_by_id(db, plan_id)
    if not plan:
        return False
    delete_entity_tag(db, "plan", plan_id)
    delete_entity_graph_data(db, "plan", plan_id)
    db.delete(plan)
    db.commit()
    return True


def _delete_entity_by_type(db: Session, entity_type: str, entity_id: int) -> None:
    """Delete an entity by type and ID using the appropriate service."""
    # Lazy imports to avoid circular deps at module level
    from wellbegun.services import (
        note_service,
        source_service,
        activity_service,
        collection_service,
        actor_service,
        project_service,
    )

    deleters = {
        "note": note_service.delete,
        "source": source_service.delete,
        "activity": activity_service.delete,
        "collection": collection_service.delete,
        "actor": actor_service.delete,
        "project": project_service.delete,
    }
    fn = deleters.get(entity_type)
    if fn:
        fn(db, entity_id)


def delete_cascade(db: Session, plan_id: int) -> bool:
    """Delete a plan and all entities related to it via knowledge triples.

    For collections: also deletes member entities referenced by CollectionItems.
    For standalone entities: deletes them directly.
    Also deletes activities linked via the legacy plan_id FK.
    """
    from wellbegun.services import collection_service

    plan = get_by_id(db, plan_id)
    if not plan:
        return False

    # Snapshot activity IDs before cascade (FK relationship may go stale)
    fk_activity_ids = [a.id for a in plan.activities]

    # Get outgoing triples (plan is subject)
    triples = knowledge_service.get_triples_for_entity(db, "plan", plan_id)
    outgoing = [
        t for t in triples if t.subject_type == "plan" and t.subject_id == plan_id
    ]

    deleted: set[tuple[str, int]] = set()

    # Phase 1: Delete collection members first
    for triple in outgoing:
        if triple.object_type == "collection":
            coll = collection_service.get_by_id(db, triple.object_id)
            if coll:
                for item in coll.items:
                    key = (item.member_entity_type, item.member_entity_id)
                    if key not in deleted:
                        _delete_entity_by_type(db, item.member_entity_type, item.member_entity_id)
                        deleted.add(key)

    # Phase 2: Delete direct targets (collections, standalone entities)
    for triple in outgoing:
        key = (triple.object_type, triple.object_id)
        if key not in deleted:
            _delete_entity_by_type(db, triple.object_type, triple.object_id)
            deleted.add(key)

    # Phase 3: Delete legacy FK activities not already handled
    for act_id in fk_activity_ids:
        key = ("activity", act_id)
        if key not in deleted:
            _delete_entity_by_type(db, "activity", act_id)
            deleted.add(key)

    # Phase 4: Delete the plan itself (re-fetch since earlier commits may have expired it)
    plan = get_by_id(db, plan_id)
    if plan:
        delete_entity_tag(db, "plan", plan_id)
        delete_entity_graph_data(db, "plan", plan_id)
        db.delete(plan)
        db.commit()

    return True


def activate(db: Session, plan_id: int) -> Plan | None:
    plan = get_by_id(db, plan_id)
    if not plan:
        return None
    plan.is_active = True
    db.commit()
    db.refresh(plan)
    return plan


def deactivate(db: Session, plan_id: int) -> Plan | None:
    plan = get_by_id(db, plan_id)
    if not plan:
        return None
    plan.is_active = False
    db.commit()
    db.refresh(plan)
    return plan


def archive(db: Session, plan_id: int) -> Plan | None:
    plan = get_by_id(db, plan_id)
    if not plan:
        return None
    plan.is_archived = True
    plan.is_active = False
    db.commit()
    db.refresh(plan)
    return plan


# --------------- Plan ↔ Role Notes CRUD ---------------

ROLE_PREDICATES = {
    "motivation": "has motivation",
    "goal": "has goal",
    "outcome": "has outcome",
}

ROLE_TITLE_PREFIX = {
    "motivation": "Motivation",
    "goal": "Goal",
    "outcome": "Outcome",
}

VALID_ROLES = set(ROLE_PREDICATES.keys())


ROLE_TAG_NAME = {
    "motivation": "Motivation",
    "goal": "Goal",
    "outcome": "Outcome",
}


def add_role_note(
    db: Session, plan_id: int, role: str, content: str
) -> "Note":
    """Create a Note linked to the plan via a role predicate triple."""
    from wellbegun.services import note_service
    from wellbegun.services.tag_service import get_tag_by_name, attach_tag

    if role not in VALID_ROLES:
        raise ValueError(f"Invalid role: {role}")

    plan = get_by_id(db, plan_id)
    if not plan:
        raise ValueError(f"Plan {plan_id} not found")

    title = f"{ROLE_TITLE_PREFIX[role]}: {plan.title}"
    note = note_service.create(db, title=title, content=content.strip())
    knowledge_service.create_triple(
        db,
        subject_type="plan",
        subject_id=plan_id,
        predicate=ROLE_PREDICATES[role],
        object_type="note",
        object_id=note.id,
    )
    # Auto-tag with the role tag
    tag_name = ROLE_TAG_NAME.get(role)
    if tag_name:
        tag = get_tag_by_name(db, tag_name)
        if tag:
            attach_tag(db, tag.id, "note", note.id)
    return note


def remove_role_note(db: Session, plan_id: int, note_id: int) -> bool:
    """Remove a note linked to this plan (delete triple + note)."""
    from wellbegun.services import note_service

    triples = knowledge_service.get_triples_for_entity(db, "plan", plan_id)
    for t in triples:
        if (
            t.subject_type == "plan"
            and t.subject_id == plan_id
            and t.object_type == "note"
            and t.object_id == note_id
            and t.predicate in ROLE_PREDICATES.values()
        ):
            knowledge_service.delete_triple(db, t.id)
            note_service.delete(db, note_id)
            return True
    return False
