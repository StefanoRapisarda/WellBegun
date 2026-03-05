from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from wellbegun.database import get_db
from wellbegun.schemas.plan import (
    PlanActivityGroupAdd,
    PlanCollectionCreate,
    PlanCreate,
    PlanOut,
    PlanRoleNoteCreate,
    PlanRoleNoteOut,
    PlanTypedCollectionCreate,
    PlanUpdate,
)
from wellbegun.services import plan_service, collection_service
from wellbegun.services.plan_service import ensure_plan_collection
from wellbegun.models.collection import CollectionItem

router = APIRouter(prefix="/plans", tags=["plans"])


@router.get("/", response_model=list[PlanOut])
def list_plans(db: Session = Depends(get_db)):
    return plan_service.get_all(db)


@router.get("/{plan_id}", response_model=PlanOut)
def get_plan(plan_id: int, db: Session = Depends(get_db)):
    plan = plan_service.get_by_id(db, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan


@router.post("/", response_model=PlanOut, status_code=201)
def create_plan(data: PlanCreate, db: Session = Depends(get_db)):
    return plan_service.create(
        db,
        title=data.title,
        description=data.description,
        motivation=data.motivation,
        outcome=data.outcome,
        goal=data.goal,
        start_date=data.start_date,
        end_date=data.end_date,
        status=data.status,
    )


@router.put("/{plan_id}", response_model=PlanOut)
def update_plan(plan_id: int, data: PlanUpdate, db: Session = Depends(get_db)):
    updates = data.model_dump(exclude_unset=True)
    plan = plan_service.update(db, plan_id, **updates)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan


@router.delete("/{plan_id}")
def delete_plan(plan_id: int, cascade: bool = False, db: Session = Depends(get_db)):
    if cascade:
        if not plan_service.delete_cascade(db, plan_id):
            raise HTTPException(status_code=404, detail="Plan not found")
    else:
        if not plan_service.delete(db, plan_id):
            raise HTTPException(status_code=404, detail="Plan not found")
    return {"ok": True}


@router.post("/{plan_id}/activate", response_model=PlanOut)
def activate_plan(plan_id: int, db: Session = Depends(get_db)):
    plan = plan_service.activate(db, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan


@router.post("/{plan_id}/deactivate", response_model=PlanOut)
def deactivate_plan(plan_id: int, db: Session = Depends(get_db)):
    plan = plan_service.deactivate(db, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan


@router.post("/{plan_id}/role-notes", response_model=PlanRoleNoteOut, status_code=201)
def add_role_note(plan_id: int, body: PlanRoleNoteCreate, db: Session = Depends(get_db)):
    try:
        note = plan_service.add_role_note(db, plan_id, role=body.role, content=body.content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return PlanRoleNoteOut(
        note_id=note.id,
        role=body.role,
        title=note.title,
        content=note.content,
    )


@router.delete("/{plan_id}/role-notes/{note_id}")
def remove_role_note(plan_id: int, note_id: int, db: Session = Depends(get_db)):
    if not plan_service.remove_role_note(db, plan_id, note_id):
        raise HTTPException(status_code=404, detail="Role note not found")
    return {"ok": True}


@router.post("/{plan_id}/archive", response_model=PlanOut)
def archive_plan(plan_id: int, db: Session = Depends(get_db)):
    plan = plan_service.archive(db, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan


# --------------- Source/Actor collection endpoints ---------------

@router.post("/{plan_id}/sources/{source_id}", status_code=201)
def add_plan_source(plan_id: int, source_id: int, collection_id: int | None = None, db: Session = Depends(get_db)):
    plan = plan_service.get_by_id(db, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    if collection_id is not None:
        coll = collection_service.get_by_id(db, collection_id)
        if not coll:
            raise HTTPException(status_code=404, detail="Collection not found")
    else:
        coll = ensure_plan_collection(db, plan_id, "sources", "source")
    try:
        collection_service.add_item(db, coll.id, member_entity_type="source", member_entity_id=source_id)
    except ValueError:
        pass  # duplicate or validation error
    return {"ok": True, "collection_id": coll.id}


@router.delete("/{plan_id}/sources/{source_id}")
def remove_plan_source(plan_id: int, source_id: int, db: Session = Depends(get_db)):
    plan = plan_service.get_by_id(db, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    coll = ensure_plan_collection(db, plan_id, "sources", "source")
    item = (
        db.query(CollectionItem)
        .filter(
            CollectionItem.collection_id == coll.id,
            CollectionItem.member_entity_type == "source",
            CollectionItem.member_entity_id == source_id,
        )
        .first()
    )
    if item:
        collection_service.remove_item(db, item.id)
    return {"ok": True}


@router.post("/{plan_id}/actors/{actor_id}", status_code=201)
def add_plan_actor(plan_id: int, actor_id: int, collection_id: int | None = None, db: Session = Depends(get_db)):
    plan = plan_service.get_by_id(db, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    if collection_id is not None:
        coll = collection_service.get_by_id(db, collection_id)
        if not coll:
            raise HTTPException(status_code=404, detail="Collection not found")
    else:
        coll = ensure_plan_collection(db, plan_id, "actors", "actor")
    try:
        collection_service.add_item(db, coll.id, member_entity_type="actor", member_entity_id=actor_id)
    except ValueError:
        pass  # duplicate or validation error
    return {"ok": True, "collection_id": coll.id}


@router.delete("/{plan_id}/actors/{actor_id}")
def remove_plan_actor(plan_id: int, actor_id: int, db: Session = Depends(get_db)):
    plan = plan_service.get_by_id(db, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    coll = ensure_plan_collection(db, plan_id, "actors", "actor")
    item = (
        db.query(CollectionItem)
        .filter(
            CollectionItem.collection_id == coll.id,
            CollectionItem.member_entity_type == "actor",
            CollectionItem.member_entity_id == actor_id,
        )
        .first()
    )
    if item:
        collection_service.remove_item(db, item.id)
    return {"ok": True}


# --------------- Plan collections endpoints ---------------

@router.post("/{plan_id}/typed-collections", status_code=201)
def create_typed_collection(plan_id: int, body: PlanTypedCollectionCreate, db: Session = Depends(get_db)):
    """Create a named typed collection for a plan.

    Maps member_type to the section prefix (e.g. "activity" → "activities").
    Uses ensure_plan_collection with predicate 'has {section}:{title}'.
    """
    plan = plan_service.get_by_id(db, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    type_to_section = {"activity": "activities", "source": "sources", "actor": "actors"}
    section_prefix = type_to_section.get(body.member_type)
    if not section_prefix:
        raise HTTPException(status_code=400, detail=f"Invalid member_type: {body.member_type}")
    section = f"{section_prefix}:{body.title}"
    coll = ensure_plan_collection(db, plan_id, section, body.member_type)
    if coll.title != body.title:
        collection_service.update(db, coll.id, title=body.title)
    return {"collection_id": coll.id, "title": body.title}


@router.post("/{plan_id}/collections", status_code=201)
def create_plan_collection(plan_id: int, body: PlanCollectionCreate, db: Session = Depends(get_db)):
    """Create a named unified collection for a plan.

    Uses ensure_plan_collection with predicate 'has collection:<title>'.
    The collection accepts any entity type (activities, sources, actors).
    Returns the collection_id and title.
    """
    plan = plan_service.get_by_id(db, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    section = f"collection:{body.title}"
    coll = ensure_plan_collection(db, plan_id, section, "*")
    if coll.title != body.title:
        collection_service.update(db, coll.id, title=body.title)
    return {"collection_id": coll.id, "title": body.title}


@router.get("/{plan_id}/collections")
def get_plan_collections(plan_id: int, db: Session = Depends(get_db)):
    """Return all collections linked to this plan via knowledge triples.

    Each entry includes collection_id, title, predicate, category_id, and items[].
    """
    from wellbegun.services import knowledge_service

    plan = plan_service.get_by_id(db, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    triples = knowledge_service.get_triples_for_entity(db, "plan", plan_id)
    results = []
    for t in triples:
        if (
            t.subject_type == "plan"
            and t.subject_id == plan_id
            and t.object_type == "collection"
        ):
            coll = collection_service.get_by_id(db, t.object_id)
            if not coll:
                continue
            items = []
            for item in (coll.items or []):
                items.append({
                    "item_id": item.id,
                    "member_entity_type": item.member_entity_type,
                    "member_entity_id": item.member_entity_id,
                    "status": item.status,
                    "position": item.position,
                    "header": item.header,
                })
            results.append({
                "collection_id": coll.id,
                "title": coll.title,
                "predicate": t.predicate,
                "category_id": coll.category_id,
                "items": items,
            })
    return results


# --------------- Activity group (collection) endpoints ---------------

@router.post("/{plan_id}/activity-group", status_code=201)
def add_activity_to_group(plan_id: int, body: PlanActivityGroupAdd, db: Session = Depends(get_db)):
    """Add an activity to a named collection group within a plan.

    Creates the collection if it doesn't exist yet, using predicate
    'has activities:<header>' to keep per-header collections separate.
    """
    plan = plan_service.get_by_id(db, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    section = f"activities:{body.header}"
    coll = ensure_plan_collection(db, plan_id, section, "activity")
    # Give the collection the header name as title (not the auto-generated one)
    if coll.title != body.header:
        collection_service.update(db, coll.id, title=body.header)
    try:
        collection_service.add_item(
            db, coll.id,
            member_entity_type="activity",
            member_entity_id=body.activity_id,
        )
    except ValueError:
        pass  # duplicate
    return {"ok": True, "collection_id": coll.id}


@router.delete("/{plan_id}/activity-group/{activity_id}")
def remove_activity_from_group(plan_id: int, activity_id: int, db: Session = Depends(get_db)):
    """Remove an activity from ALL plan activity collections (default + named)."""
    from wellbegun.services import knowledge_service

    plan = plan_service.get_by_id(db, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    # Find all activity collections for this plan (both "has activities" and "has activities:*")
    triples = knowledge_service.get_triples_for_entity(db, "plan", plan_id)
    for t in triples:
        if (
            t.subject_type == "plan"
            and t.subject_id == plan_id
            and t.object_type == "collection"
            and (t.predicate == "has activities" or t.predicate.startswith("has activities:"))
        ):
            item = (
                db.query(CollectionItem)
                .filter(
                    CollectionItem.collection_id == t.object_id,
                    CollectionItem.member_entity_type == "activity",
                    CollectionItem.member_entity_id == activity_id,
                )
                .first()
            )
            if item:
                collection_service.remove_item(db, item.id)
    return {"ok": True}


