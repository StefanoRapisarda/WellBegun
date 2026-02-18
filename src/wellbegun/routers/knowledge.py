from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from wellbegun.database import get_db
from wellbegun.schemas.knowledge import (
    BoardNodeBulkUpsert,
    BoardNodeOut,
    BoardNodeUpdate,
    BoardNodeUpsert,
    CustomPredicateCreate,
    CustomPredicateOut,
    CustomPredicateUpdate,
    PopulateFocusRequest,
    TripleCreate,
    TripleOut,
    TripleUpdate,
)
from wellbegun.services import board_service, knowledge_service, predicate_service

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


# ── Triples ──────────────────────────────────────────────────────────────────

@router.get("/triples", response_model=list[TripleOut])
def list_triples(db: Session = Depends(get_db)):
    return knowledge_service.get_all_triples(db)


@router.get("/triples/{entity_type}/{entity_id}", response_model=list[TripleOut])
def get_triples_for_entity(
    entity_type: str, entity_id: int, db: Session = Depends(get_db)
):
    return knowledge_service.get_triples_for_entity(db, entity_type, entity_id)


@router.post("/triples", response_model=TripleOut, status_code=201)
def create_triple(data: TripleCreate, db: Session = Depends(get_db)):
    return knowledge_service.create_triple(
        db,
        subject_type=data.subject_type,
        subject_id=data.subject_id,
        predicate=data.predicate,
        object_type=data.object_type,
        object_id=data.object_id,
    )


@router.put("/triples/{triple_id}/swap", response_model=TripleOut)
def swap_triple(triple_id: int, db: Session = Depends(get_db)):
    triple = knowledge_service.swap_triple_direction(db, triple_id)
    if not triple:
        raise HTTPException(status_code=404, detail="Triple not found")
    return triple


@router.put("/triples/{triple_id}", response_model=TripleOut)
def update_triple(triple_id: int, data: TripleUpdate, db: Session = Depends(get_db)):
    triple = knowledge_service.update_triple_predicate(db, triple_id, data.predicate)
    if not triple:
        raise HTTPException(status_code=404, detail="Triple not found")
    return triple


@router.delete("/triples/{triple_id}")
def delete_triple(triple_id: int, db: Session = Depends(get_db)):
    if not knowledge_service.delete_triple(db, triple_id):
        raise HTTPException(status_code=404, detail="Triple not found")
    return {"ok": True}


# ── Board nodes ──────────────────────────────────────────────────────────────

@router.get("/board", response_model=list[BoardNodeOut])
def list_board_nodes(db: Session = Depends(get_db)):
    return board_service.get_all_nodes(db)


@router.post("/board", response_model=BoardNodeOut, status_code=201)
def upsert_board_node(data: BoardNodeUpsert, db: Session = Depends(get_db)):
    return board_service.upsert_node(
        db,
        entity_type=data.entity_type,
        entity_id=data.entity_id,
        x=data.x,
        y=data.y,
    )


@router.post("/board/bulk", response_model=list[BoardNodeOut])
def bulk_upsert_board_nodes(data: BoardNodeBulkUpsert, db: Session = Depends(get_db)):
    nodes_list = [n.model_dump() for n in data.nodes]
    return board_service.bulk_upsert_nodes(db, nodes_list)


@router.patch("/board/{entity_type}/{entity_id}", response_model=BoardNodeOut)
def update_board_node(
    entity_type: str, entity_id: int, data: BoardNodeUpdate, db: Session = Depends(get_db)
):
    node = (
        db.query(board_service.BoardNode)
        .filter(
            board_service.BoardNode.entity_type == entity_type,
            board_service.BoardNode.entity_id == entity_id,
        )
        .first()
    )
    if not node:
        raise HTTPException(status_code=404, detail="Board node not found")
    return board_service.update_node(
        db, node.id, x=data.x, y=data.y, collapsed=data.collapsed
    )


@router.delete("/board/{entity_type}/{entity_id}")
def delete_board_node(
    entity_type: str, entity_id: int, db: Session = Depends(get_db)
):
    if not board_service.delete_node(db, entity_type, entity_id):
        raise HTTPException(status_code=404, detail="Board node not found")
    return {"ok": True}


# ── Populate from focus ──────────────────────────────────────────────────────

@router.post("/populate")
def populate_from_focus(data: PopulateFocusRequest, db: Session = Depends(get_db)):
    """Populate the graph with entities from a focus selection."""
    return knowledge_service.populate_from_focus(
        db,
        project_ids=data.project_ids,
        activity_ids=data.activity_ids,
    )


@router.post("/populate-all")
def populate_all(db: Session = Depends(get_db)):
    """Populate the graph with ALL entities in the system."""
    return knowledge_service.populate_all(db)


# ── Predicates ────────────────────────────────────────────────────────────────

@router.get("/predicates")
def get_predicates(db: Session = Depends(get_db)):
    from wellbegun.services.structural_relations import STRUCTURAL_PREDICATES, SEMANTIC_RELATIONS
    structural = {f"{k[0]}:{k[1]}": v for k, v in STRUCTURAL_PREDICATES.items()}
    custom = predicate_service.get_all_custom_predicates(db)
    return {
        "structural": structural,
        "semantic": SEMANTIC_RELATIONS,
        "custom": [CustomPredicateOut.model_validate(cp).model_dump(mode="json") for cp in custom],
    }


# ── Custom predicates CRUD ───────────────────────────────────────────────────

@router.get("/custom-predicates", response_model=list[CustomPredicateOut])
def list_custom_predicates(db: Session = Depends(get_db)):
    return predicate_service.get_all_custom_predicates(db)


@router.post("/custom-predicates", response_model=CustomPredicateOut, status_code=201)
def create_custom_predicate(data: CustomPredicateCreate, db: Session = Depends(get_db)):
    return predicate_service.create_custom_predicate(
        db, forward=data.forward, reverse=data.reverse, category=data.category
    )


@router.put("/custom-predicates/{predicate_id}", response_model=CustomPredicateOut)
def update_custom_predicate(predicate_id: int, data: CustomPredicateUpdate, db: Session = Depends(get_db)):
    cp = predicate_service.update_custom_predicate(
        db, predicate_id, forward=data.forward, reverse=data.reverse, category=data.category
    )
    if not cp:
        raise HTTPException(status_code=404, detail="Custom predicate not found")
    return cp


@router.delete("/custom-predicates/{predicate_id}")
def delete_custom_predicate(predicate_id: int, db: Session = Depends(get_db)):
    if not predicate_service.delete_custom_predicate(db, predicate_id):
        raise HTTPException(status_code=404, detail="Custom predicate not found")
    return {"ok": True}


# ── Sync migration ────────────────────────────────────────────────────────────

@router.post("/sync-migration")
def run_sync_migration(db: Session = Depends(get_db)):
    from wellbegun.services.sync_migration import (
        sync_tags_to_triples, sync_triples_to_tags, update_legacy_predicates,
    )
    r1 = sync_tags_to_triples(db)
    r2 = sync_triples_to_tags(db)
    r3 = update_legacy_predicates(db)
    db.commit()
    return {"tags_to_triples": r1, "triples_to_tags": r2, "predicates_updated": r3}
