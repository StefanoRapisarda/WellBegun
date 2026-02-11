from datetime import datetime

from pydantic import BaseModel


class TagOut(BaseModel):
    id: int
    name: str
    category: str
    full_tag: str
    description: str | None = None
    entity_type: str | None = None
    entity_id: int | None = None
    is_system: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


class WildTagCreate(BaseModel):
    name: str
    description: str | None = None
    category: str = "wild"


class WildTagUpdate(BaseModel):
    description: str | None = None
    category: str | None = None


class MoveCategoryRequest(BaseModel):
    from_category: str
    to_category: str


class AttachDetachRequest(BaseModel):
    tag_id: int
    target_type: str
    target_id: int


class EntityTagOut(BaseModel):
    id: int
    tag_id: int
    target_type: str
    target_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class SyncHashtagsRequest(BaseModel):
    content: str
    target_type: str
    target_id: int
