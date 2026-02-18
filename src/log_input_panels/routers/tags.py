from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from log_input_panels.database import get_db
from log_input_panels.schemas.tag import (
    AttachDetachRequest,
    EntityTagOut,
    MoveCategoryRequest,
    SyncHashtagsRequest,
    TagOut,
    WildTagCreate,
    WildTagUpdate,
)
from log_input_panels.services import tag_service

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("/", response_model=list[TagOut])
def list_tags(db: Session = Depends(get_db)):
    return tag_service.get_all_tags(db)


@router.get("/search", response_model=list[TagOut])
def search_tags(q: str = "", limit: int = 20, db: Session = Depends(get_db)):
    if not q:
        return tag_service.get_all_tags(db)
    return tag_service.search_tags(db, q, limit)


@router.get("/category/{category}", response_model=list[TagOut])
def tags_by_category(category: str, db: Session = Depends(get_db)):
    return tag_service.get_tags_by_category(db, category)


@router.get("/usage-counts")
def get_tag_usage_counts(db: Session = Depends(get_db)):
    """Return {tag_id: usage_count} for tags with at least one entity attachment."""
    return tag_service.get_tag_usage_counts(db)


@router.get("/entity-tags-bulk")
def get_all_entity_tags_bulk(db: Session = Depends(get_db)):
    """Return all entity tags grouped by 'type:id' key in a single request."""
    return tag_service.get_all_entity_tags_bulk(db)


@router.get("/entity/{target_type}/{target_id}", response_model=list[TagOut])
def get_entity_tags(target_type: str, target_id: int, db: Session = Depends(get_db)):
    return tag_service.get_entity_tags(db, target_type, target_id)


@router.get("/links/{entity_type}/{entity_id}")
def get_tag_links(entity_type: str, entity_id: int, db: Session = Depends(get_db)):
    """Get all tag-based relationships for an entity."""
    return tag_service.get_tag_links(db, entity_type, entity_id)


@router.post("/wild", response_model=TagOut)
def create_wild_tag(data: WildTagCreate, db: Session = Depends(get_db)):
    tag = tag_service.create_wild_tag(db, data.name, data.description, data.category, color=data.color)
    db.commit()
    db.refresh(tag)
    return tag


@router.put("/wild/{tag_id}", response_model=TagOut)
def update_wild_tag(tag_id: int, data: WildTagUpdate, db: Session = Depends(get_db)):
    tag = tag_service.update_wild_tag(db, tag_id, data.description, data.category, color=data.color)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    db.commit()
    db.refresh(tag)
    return tag


@router.post("/move-category")
def move_category(data: MoveCategoryRequest, db: Session = Depends(get_db)):
    """Move all non-system tags from one category to another."""
    count = tag_service.move_category_tags(db, data.from_category, data.to_category)
    db.commit()
    return {"ok": True, "moved": count}


@router.delete("/wild/{tag_id}")
def delete_wild_tag(tag_id: int, db: Session = Depends(get_db)):
    if not tag_service.delete_wild_tag(db, tag_id):
        raise HTTPException(status_code=404, detail="Wild tag not found")
    db.commit()
    return {"ok": True}


@router.post("/attach", response_model=EntityTagOut)
def attach_tag(data: AttachDetachRequest, db: Session = Depends(get_db)):
    et = tag_service.attach_tag(db, data.tag_id, data.target_type, data.target_id)
    db.commit()
    db.refresh(et)
    return et


@router.post("/detach")
def detach_tag(data: AttachDetachRequest, db: Session = Depends(get_db)):
    if not tag_service.detach_tag(db, data.tag_id, data.target_type, data.target_id):
        raise HTTPException(status_code=404, detail="Tag attachment not found")
    db.commit()
    return {"ok": True}


@router.post("/sync-hashtags", response_model=list[TagOut])
def sync_hashtags(data: SyncHashtagsRequest, db: Session = Depends(get_db)):
    tags = tag_service.sync_inline_hashtags(db, data.content, data.target_type, data.target_id)
    db.commit()
    return tags
