import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session, joinedload

from wellbegun.models.workspace import Workspace, WorkspaceItem, WorkspaceEvent
from wellbegun.models.knowledge_triple import KnowledgeTriple
from wellbegun.models.log import Activity
from wellbegun.models.collection import CollectionItem
from wellbegun.services.knowledge_service import create_triple
from wellbegun.services.structural_relations import get_structural_predicate


def get_all(db: Session, include_archived: bool = False) -> list[Workspace]:
    q = (
        db.query(Workspace)
        .options(joinedload(Workspace.items))
        .order_by(Workspace.last_opened_at.desc())
    )
    if not include_archived:
        q = q.filter(Workspace.is_archived == False)
    return q.all()


def get_by_id(db: Session, workspace_id: int) -> Workspace | None:
    return (
        db.query(Workspace)
        .options(joinedload(Workspace.items))
        .filter(Workspace.id == workspace_id)
        .first()
    )


def get_detail(db: Session, workspace_id: int) -> Workspace | None:
    return (
        db.query(Workspace)
        .options(joinedload(Workspace.items), joinedload(Workspace.events))
        .filter(Workspace.id == workspace_id)
        .first()
    )


def create(db: Session, name: str, description: str | None = None) -> Workspace:
    workspace = Workspace(name=name, description=description)
    db.add(workspace)
    db.flush()
    record_event(db, workspace.id, "opened")
    db.commit()
    db.refresh(workspace)
    return workspace


def update(db: Session, workspace_id: int, **kwargs) -> Workspace | None:
    workspace = get_by_id(db, workspace_id)
    if not workspace:
        return None
    for key, value in kwargs.items():
        if hasattr(workspace, key):
            setattr(workspace, key, value)
    db.commit()
    db.refresh(workspace)
    return workspace


def delete(db: Session, workspace_id: int) -> bool:
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        return False
    db.delete(workspace)
    db.commit()
    return True


def archive(db: Session, workspace_id: int) -> Workspace | None:
    workspace = get_by_id(db, workspace_id)
    if not workspace:
        return None
    workspace.is_archived = True
    db.commit()
    db.refresh(workspace)
    return workspace


def open_workspace(db: Session, workspace_id: int) -> Workspace | None:
    workspace = get_by_id(db, workspace_id)
    if not workspace:
        return None
    workspace.last_opened_at = datetime.now(timezone.utc)
    db.flush()
    record_event(db, workspace_id, "opened")
    db.commit()
    db.refresh(workspace)
    return workspace


def add_item(
    db: Session,
    workspace_id: int,
    entity_type: str,
    entity_id: int,
    x: float = 0.0,
    y: float = 0.0,
) -> WorkspaceItem:
    # Check if already exists
    existing = (
        db.query(WorkspaceItem)
        .filter(
            WorkspaceItem.workspace_id == workspace_id,
            WorkspaceItem.entity_type == entity_type,
            WorkspaceItem.entity_id == entity_id,
        )
        .first()
    )
    if existing:
        return existing

    item = WorkspaceItem(
        workspace_id=workspace_id,
        entity_type=entity_type,
        entity_id=entity_id,
        x=x,
        y=y,
    )
    db.add(item)
    db.flush()
    record_event(db, workspace_id, "entity_added", entity_type, entity_id)
    db.commit()
    db.refresh(item)
    return item


def remove_item_by_entity(
    db: Session, workspace_id: int, entity_type: str, entity_id: int
) -> bool:
    item = (
        db.query(WorkspaceItem)
        .filter(
            WorkspaceItem.workspace_id == workspace_id,
            WorkspaceItem.entity_type == entity_type,
            WorkspaceItem.entity_id == entity_id,
        )
        .first()
    )
    if not item:
        return False
    db.delete(item)
    db.flush()
    record_event(db, workspace_id, "entity_removed", entity_type, entity_id)
    db.commit()
    return True


def update_item(db: Session, item_id: int, **kwargs) -> WorkspaceItem | None:
    item = db.query(WorkspaceItem).filter(WorkspaceItem.id == item_id).first()
    if not item:
        return None
    for key, value in kwargs.items():
        if hasattr(item, key) and value is not None:
            setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


def bulk_update_positions(
    db: Session, workspace_id: int, updates: list[dict]
) -> list[WorkspaceItem]:
    items = (
        db.query(WorkspaceItem)
        .filter(WorkspaceItem.workspace_id == workspace_id)
        .all()
    )
    item_map = {
        (i.entity_type, i.entity_id): i for i in items
    }

    updated = []
    for upd in updates:
        key = (upd.get("entity_type"), upd.get("entity_id"))
        item = item_map.get(key)
        if item:
            if "x" in upd:
                item.x = upd["x"]
            if "y" in upd:
                item.y = upd["y"]
            updated.append(item)

    db.commit()
    for item in updated:
        db.refresh(item)
    return updated


def record_event(
    db: Session,
    workspace_id: int,
    event_type: str,
    entity_type: str | None = None,
    entity_id: int | None = None,
    metadata: dict | None = None,
) -> WorkspaceEvent:
    event = WorkspaceEvent(
        workspace_id=workspace_id,
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        metadata_json=json.dumps(metadata) if metadata else None,
    )
    db.add(event)
    return event


def get_events(
    db: Session, workspace_id: int, limit: int = 50
) -> list[WorkspaceEvent]:
    return (
        db.query(WorkspaceEvent)
        .filter(WorkspaceEvent.workspace_id == workspace_id)
        .order_by(WorkspaceEvent.timestamp.desc())
        .limit(limit)
        .all()
    )


def get_expansion_entities(
    db: Session, entity_type: str, entity_id: int
) -> list[dict]:
    """Return list of {entity_type, entity_id} for auto-expansion."""
    result: list[dict] = []

    if entity_type == "plan":
        # Activities linked via FK
        activities = (
            db.query(Activity)
            .filter(Activity.plan_id == entity_id)
            .all()
        )
        for act in activities:
            result.append({"entity_type": "activity", "entity_id": act.id})

        # Collections via triples (plan -> has collection -> collection)
        coll_triples = (
            db.query(KnowledgeTriple)
            .filter(
                KnowledgeTriple.subject_type == "plan",
                KnowledgeTriple.subject_id == entity_id,
                KnowledgeTriple.object_type == "collection",
            )
            .all()
        )
        for t in coll_triples:
            result.append({"entity_type": "collection", "entity_id": t.object_id})
            # Collection members
            members = (
                db.query(CollectionItem)
                .filter(CollectionItem.collection_id == t.object_id)
                .all()
            )
            for m in members:
                result.append({
                    "entity_type": m.member_entity_type,
                    "entity_id": m.member_entity_id,
                })

        # Role notes via triples (plan -> has note -> note)
        note_triples = (
            db.query(KnowledgeTriple)
            .filter(
                KnowledgeTriple.subject_type == "plan",
                KnowledgeTriple.subject_id == entity_id,
                KnowledgeTriple.object_type == "note",
            )
            .all()
        )
        for t in note_triples:
            result.append({"entity_type": "note", "entity_id": t.object_id})

    elif entity_type == "project":
        # Active/in-progress activities via triples
        act_triples = (
            db.query(KnowledgeTriple)
            .filter(
                KnowledgeTriple.subject_type == "project",
                KnowledgeTriple.subject_id == entity_id,
                KnowledgeTriple.object_type == "activity",
            )
            .all()
        )
        act_ids = [t.object_id for t in act_triples]
        if act_ids:
            acts = (
                db.query(Activity)
                .filter(
                    Activity.id.in_(act_ids),
                    Activity.status.in_(["todo", "in_progress"]),
                )
                .all()
            )
            for act in acts:
                result.append({"entity_type": "activity", "entity_id": act.id})

    elif entity_type == "activity":
        # Its source (if source_id is set)
        activity = db.query(Activity).filter(Activity.id == entity_id).first()
        if activity and activity.source_id:
            result.append({"entity_type": "source", "entity_id": activity.source_id})

    elif entity_type == "collection":
        # Its member items
        members = (
            db.query(CollectionItem)
            .filter(CollectionItem.collection_id == entity_id)
            .all()
        )
        for m in members:
            result.append({
                "entity_type": m.member_entity_type,
                "entity_id": m.member_entity_id,
            })

    # Deduplicate
    seen = set()
    unique = []
    for item in result:
        key = (item["entity_type"], item["entity_id"])
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


def ensure_expansion_triples(
    db: Session,
    entity_type: str,
    entity_id: int,
    expanded_entities: list[dict],
) -> int:
    """Create knowledge triples between main entity and its expanded entities.

    Also creates FK-based triples (plan→activity, activity→source, collection→member)
    that aren't covered by tag-based relationships.

    Skips direct main→member triples for entities that belong to a collection
    in the expanded set (they'll be connected via collection→member instead).

    Returns the number of triples created/updated.
    """
    count = 0

    # FK-based relationships within expanded set
    all_keys = {(entity_type, entity_id)}
    for exp in expanded_entities:
        all_keys.add((exp["entity_type"], exp["entity_id"]))

    # Build set of entities that are members of any expanded collection
    # so we can skip redundant direct main→member triples
    collection_member_keys: set[tuple[str, int]] = set()
    coll_ids = [exp["entity_id"] for exp in expanded_entities if exp["entity_type"] == "collection"]
    if entity_type == "collection":
        coll_ids.append(entity_id)
    if coll_ids:
        coll_members = db.query(CollectionItem).filter(CollectionItem.collection_id.in_(coll_ids)).all()
        for m in coll_members:
            if (m.member_entity_type, m.member_entity_id) in all_keys:
                collection_member_keys.add((m.member_entity_type, m.member_entity_id))

    # Create main→expanded triples, skipping collection members (unless they are collections)
    for exp in expanded_entities:
        exp_type = exp["entity_type"]
        exp_id = exp["entity_id"]
        exp_key = (exp_type, exp_id)
        if exp_key in collection_member_keys and exp_type != "collection":
            continue
        predicate = get_structural_predicate(entity_type, exp_type)
        create_triple(db, entity_type, entity_id, predicate, exp_type, exp_id)
        count += 1

    # Plan→Activity (Activity.plan_id FK) — skip activities in collection_member_keys
    act_ids = [exp["entity_id"] for exp in expanded_entities if exp["entity_type"] == "activity"]
    if act_ids:
        activities = db.query(Activity).filter(Activity.id.in_(act_ids)).all()
        for act in activities:
            if act.plan_id and ("plan", act.plan_id) in all_keys:
                if ("activity", act.id) not in collection_member_keys:
                    create_triple(db, "plan", act.plan_id, "contains", "activity", act.id)
                    count += 1
            if act.source_id and ("source", act.source_id) in all_keys:
                create_triple(db, "activity", act.id, "consults", "source", act.source_id)
                count += 1

    # Collection→Member (CollectionItem FK)
    if coll_ids:
        members = db.query(CollectionItem).filter(CollectionItem.collection_id.in_(coll_ids)).all()
        for m in members:
            if ("collection", m.collection_id) in all_keys and (m.member_entity_type, m.member_entity_id) in all_keys:
                predicate = get_structural_predicate("collection", m.member_entity_type)
                create_triple(db, "collection", m.collection_id, predicate, m.member_entity_type, m.member_entity_id)
                count += 1

    return count


def ensure_workspace_triples(db: Session, workspace_id: int) -> int:
    """Create triples for FK-based structural relationships between all workspace items.

    Called after adding a single entity to ensure connections to existing items are visible.
    Skips plan→activity triples for activities that are members of collections also in the workspace.
    Returns the number of triples created/updated.
    """
    workspace = get_by_id(db, workspace_id)
    if not workspace:
        return 0

    ws_keys = {(item.entity_type, item.entity_id) for item in workspace.items}
    count = 0

    # Build set of activities that are members of workspace collections
    # so we can skip redundant plan→activity triples
    collection_member_keys: set[tuple[str, int]] = set()
    coll_ids = [eid for etype, eid in ws_keys if etype == "collection"]
    if coll_ids:
        coll_members = db.query(CollectionItem).filter(CollectionItem.collection_id.in_(coll_ids)).all()
        for m in coll_members:
            if (m.member_entity_type, m.member_entity_id) in ws_keys:
                collection_member_keys.add((m.member_entity_type, m.member_entity_id))

    # Plan→Activity (Activity.plan_id FK) — skip activities in collection_member_keys
    plan_ids = [eid for etype, eid in ws_keys if etype == "plan"]
    if plan_ids:
        activities = db.query(Activity).filter(Activity.plan_id.in_(plan_ids)).all()
        for act in activities:
            if ("activity", act.id) in ws_keys:
                if ("activity", act.id) not in collection_member_keys:
                    create_triple(db, "plan", act.plan_id, "contains", "activity", act.id)
                    count += 1

    # Activity→Source (Activity.source_id FK)
    act_ids = [eid for etype, eid in ws_keys if etype == "activity"]
    if act_ids:
        activities = db.query(Activity).filter(
            Activity.id.in_(act_ids),
            Activity.source_id.isnot(None),
        ).all()
        for act in activities:
            if ("source", act.source_id) in ws_keys:
                create_triple(db, "activity", act.id, "consults", "source", act.source_id)
                count += 1

    # Collection→Member (CollectionItem FK)
    if coll_ids:
        members = db.query(CollectionItem).filter(CollectionItem.collection_id.in_(coll_ids)).all()
        for m in members:
            if (m.member_entity_type, m.member_entity_id) in ws_keys:
                predicate = get_structural_predicate("collection", m.member_entity_type)
                create_triple(db, "collection", m.collection_id, predicate, m.member_entity_type, m.member_entity_id)
                count += 1

    return count
