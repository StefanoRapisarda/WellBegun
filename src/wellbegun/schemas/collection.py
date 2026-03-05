from datetime import datetime

from pydantic import BaseModel


class CollectionItemCreate(BaseModel):
    member_entity_type: str
    member_entity_id: int
    position: int = 0
    status: str | None = None
    notes: str | None = None
    header: str | None = None


class CollectionItemUpdate(BaseModel):
    position: int | None = None
    status: str | None = None
    notes: str | None = None
    header: str | None = None


class CollectionItemOut(BaseModel):
    id: int
    collection_id: int
    member_entity_type: str
    member_entity_id: int
    position: int
    status: str | None = None
    notes: str | None = None
    header: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CollectionCreate(BaseModel):
    title: str
    category_id: int
    description: str | None = None


class CollectionUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    category_id: int | None = None


class CollectionOut(BaseModel):
    id: int
    entity_type: str
    title: str
    description: str | None = None
    category_id: int
    is_active: bool
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    items: list[CollectionItemOut] = []

    model_config = {"from_attributes": True}
