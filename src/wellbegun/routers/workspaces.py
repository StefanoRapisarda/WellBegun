from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from wellbegun.database import get_db
from wellbegun.schemas.workspace import (
    WorkspaceCreate,
    WorkspaceDetailOut,
    WorkspaceEventCreate,
    WorkspaceEventOut,
    WorkspaceItemCreate,
    WorkspaceItemBulkUpdate,
    WorkspaceItemOut,
    WorkspaceItemUpdate,
    WorkspaceOut,
    WorkspaceUpdate,
)
from wellbegun.services import workspace_service

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.get("/", response_model=list[WorkspaceOut])
def list_workspaces(
    include_archived: bool = False, db: Session = Depends(get_db)
):
    return workspace_service.get_all(db, include_archived=include_archived)


@router.get("/{workspace_id}", response_model=WorkspaceDetailOut)
def get_workspace(workspace_id: int, db: Session = Depends(get_db)):
    workspace = workspace_service.get_detail(db, workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace


@router.post("/", response_model=WorkspaceOut, status_code=201)
def create_workspace(data: WorkspaceCreate, db: Session = Depends(get_db)):
    return workspace_service.create(db, name=data.name, description=data.description)


@router.put("/{workspace_id}", response_model=WorkspaceOut)
def update_workspace(
    workspace_id: int, data: WorkspaceUpdate, db: Session = Depends(get_db)
):
    updates = data.model_dump(exclude_unset=True)
    workspace = workspace_service.update(db, workspace_id, **updates)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace


@router.delete("/{workspace_id}")
def delete_workspace(workspace_id: int, db: Session = Depends(get_db)):
    if not workspace_service.delete(db, workspace_id):
        raise HTTPException(status_code=404, detail="Workspace not found")
    return {"ok": True}


@router.post("/{workspace_id}/archive", response_model=WorkspaceOut)
def archive_workspace(workspace_id: int, db: Session = Depends(get_db)):
    workspace = workspace_service.archive(db, workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace


@router.post("/{workspace_id}/open", response_model=WorkspaceOut)
def open_workspace(workspace_id: int, db: Session = Depends(get_db)):
    workspace = workspace_service.open_workspace(db, workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace


# --- Item endpoints ---

@router.post("/{workspace_id}/items", response_model=WorkspaceItemOut, status_code=201)
def add_item(
    workspace_id: int, data: WorkspaceItemCreate, db: Session = Depends(get_db)
):
    item = workspace_service.add_item(
        db,
        workspace_id=workspace_id,
        entity_type=data.entity_type,
        entity_id=data.entity_id,
        x=data.x,
        y=data.y,
    )
    workspace_service.ensure_workspace_triples(db, workspace_id)
    return item


@router.delete("/{workspace_id}/items/{entity_type}/{entity_id}")
def remove_item(
    workspace_id: int,
    entity_type: str,
    entity_id: int,
    db: Session = Depends(get_db),
):
    if not workspace_service.remove_item_by_entity(db, workspace_id, entity_type, entity_id):
        raise HTTPException(status_code=404, detail="Item not found")
    return {"ok": True}


@router.patch("/items/{item_id}", response_model=WorkspaceItemOut)
def update_item(
    item_id: int, data: WorkspaceItemUpdate, db: Session = Depends(get_db)
):
    updates = data.model_dump(exclude_unset=True)
    item = workspace_service.update_item(db, item_id, **updates)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@router.post("/{workspace_id}/items/bulk-positions")
def bulk_update_positions(
    workspace_id: int,
    data: WorkspaceItemBulkUpdate,
    db: Session = Depends(get_db),
):
    workspace_service.bulk_update_positions(db, workspace_id, data.items)
    return {"ok": True}


# --- Event endpoints ---

@router.get("/{workspace_id}/events", response_model=list[WorkspaceEventOut])
def get_events(
    workspace_id: int, limit: int = 50, db: Session = Depends(get_db)
):
    return workspace_service.get_events(db, workspace_id, limit=limit)


@router.post("/{workspace_id}/events", response_model=WorkspaceEventOut, status_code=201)
def create_event(
    workspace_id: int, data: WorkspaceEventCreate, db: Session = Depends(get_db)
):
    import json
    event = workspace_service.record_event(
        db,
        workspace_id,
        event_type=data.event_type,
        entity_type=data.entity_type,
        entity_id=data.entity_id,
        metadata=data.metadata,
    )
    db.commit()
    db.refresh(event)
    return event


# --- Expand endpoint ---

@router.post("/{workspace_id}/expand/{entity_type}/{entity_id}", response_model=WorkspaceOut)
def expand_entity(
    workspace_id: int,
    entity_type: str,
    entity_id: int,
    db: Session = Depends(get_db),
):
    workspace = workspace_service.get_by_id(db, workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    # Get existing items to calculate positions
    existing_keys = {
        (item.entity_type, item.entity_id) for item in workspace.items
    }

    # Calculate base position for new entities
    CARD_W = 150
    GAP = 30
    if workspace.items:
        max_x = max(item.x for item in workspace.items)
        base_x = max_x + CARD_W + GAP
    else:
        base_x = 100.0

    base_y = 100.0

    # Add the main entity first
    if (entity_type, entity_id) not in existing_keys:
        workspace_service.add_item(db, workspace_id, entity_type, entity_id, x=base_x, y=base_y)
        existing_keys.add((entity_type, entity_id))
        base_x += CARD_W + GAP

    # Get expansion entities
    expansion = workspace_service.get_expansion_entities(db, entity_type, entity_id)

    # Add expanded entities in a grid layout
    col = 0
    row = 0
    cols_per_row = 4
    for exp in expansion:
        key = (exp["entity_type"], exp["entity_id"])
        if key not in existing_keys:
            x = base_x + col * (CARD_W + GAP)
            y = base_y + row * (80 + GAP)
            workspace_service.add_item(db, workspace_id, exp["entity_type"], exp["entity_id"], x=x, y=y)
            existing_keys.add(key)
            col += 1
            if col >= cols_per_row:
                col = 0
                row += 1

    # Create triples for structural relationships between expanded entities
    workspace_service.ensure_expansion_triples(db, entity_type, entity_id, expansion)

    # Refresh and return
    workspace = workspace_service.get_by_id(db, workspace_id)
    return workspace
