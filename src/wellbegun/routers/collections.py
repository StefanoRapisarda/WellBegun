from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from wellbegun.database import get_db
from wellbegun.schemas.collection import (
    CollectionCreate,
    CollectionItemCreate,
    CollectionItemOut,
    CollectionItemUpdate,
    CollectionOut,
    CollectionUpdate,
)
from wellbegun.services import collection_service

router = APIRouter(prefix="/collections", tags=["collections"])


@router.get("/", response_model=list[CollectionOut])
def list_collections(category_id: int | None = None, db: Session = Depends(get_db)):
    return collection_service.get_all(db, category_id=category_id)


@router.get("/{collection_id}", response_model=CollectionOut)
def get_collection(collection_id: int, db: Session = Depends(get_db)):
    collection = collection_service.get_by_id(db, collection_id)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    return collection


@router.post("/", response_model=CollectionOut, status_code=201)
def create_collection(data: CollectionCreate, db: Session = Depends(get_db)):
    return collection_service.create(
        db,
        title=data.title,
        category_id=data.category_id,
        description=data.description,
    )


@router.put("/{collection_id}", response_model=CollectionOut)
def update_collection(
    collection_id: int, data: CollectionUpdate, db: Session = Depends(get_db)
):
    updates = data.model_dump(exclude_unset=True)
    collection = collection_service.update(db, collection_id, **updates)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    return collection


@router.delete("/{collection_id}")
def delete_collection(collection_id: int, db: Session = Depends(get_db)):
    if not collection_service.delete(db, collection_id):
        raise HTTPException(status_code=404, detail="Collection not found")
    return {"ok": True}


# --- Lifecycle endpoints ---

@router.post("/{collection_id}/activate", response_model=CollectionOut)
def activate_collection(collection_id: int, db: Session = Depends(get_db)):
    collection = collection_service.activate(db, collection_id)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    return collection


@router.post("/{collection_id}/deactivate", response_model=CollectionOut)
def deactivate_collection(collection_id: int, db: Session = Depends(get_db)):
    collection = collection_service.deactivate(db, collection_id)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    return collection


@router.post("/{collection_id}/archive", response_model=CollectionOut)
def archive_collection(collection_id: int, db: Session = Depends(get_db)):
    collection = collection_service.archive(db, collection_id)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    return collection


@router.post("/{collection_id}/unarchive", response_model=CollectionOut)
def unarchive_collection(collection_id: int, db: Session = Depends(get_db)):
    collection = collection_service.unarchive(db, collection_id)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    return collection


# --- Item endpoints ---

@router.post("/{collection_id}/items", response_model=CollectionItemOut, status_code=201)
def add_item(
    collection_id: int, data: CollectionItemCreate, db: Session = Depends(get_db)
):
    try:
        return collection_service.add_item(
            db,
            collection_id=collection_id,
            member_entity_type=data.member_entity_type,
            member_entity_id=data.member_entity_id,
            position=data.position,
            status=data.status,
            notes=data.notes,
            header=data.header,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.put("/items/{item_id}", response_model=CollectionItemOut)
def update_item(item_id: int, data: CollectionItemUpdate, db: Session = Depends(get_db)):
    updates = data.model_dump(exclude_unset=True)
    try:
        item = collection_service.update_item(db, item_id, **updates)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@router.delete("/items/{item_id}")
def remove_item(item_id: int, db: Session = Depends(get_db)):
    if not collection_service.remove_item(db, item_id):
        raise HTTPException(status_code=404, detail="Item not found")
    return {"ok": True}
