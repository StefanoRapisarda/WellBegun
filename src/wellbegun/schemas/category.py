from datetime import datetime

from pydantic import BaseModel


class CategoryStatusCreate(BaseModel):
    value: str
    position: int = 0
    is_default: bool = False


class CategoryStatusUpdate(BaseModel):
    value: str | None = None
    position: int | None = None
    is_default: bool | None = None


class CategoryStatusOut(BaseModel):
    id: int
    category_id: int
    value: str
    position: int
    is_default: bool

    model_config = {"from_attributes": True}


class CategoryCreate(BaseModel):
    slug: str
    display_name: str
    member_entity_type: str


class CategoryUpdate(BaseModel):
    slug: str | None = None
    display_name: str | None = None
    member_entity_type: str | None = None


class CategoryOut(BaseModel):
    id: int
    slug: str
    display_name: str
    member_entity_type: str
    created_at: datetime
    updated_at: datetime
    statuses: list[CategoryStatusOut] = []

    model_config = {"from_attributes": True}
