from datetime import datetime

from pydantic import BaseModel


class ReadingListItemCreate(BaseModel):
    source_id: int
    position: int = 0
    status: str = "unread"
    notes: str | None = None


class ReadingListItemUpdate(BaseModel):
    position: int | None = None
    status: str | None = None
    notes: str | None = None


class ReadingListItemOut(BaseModel):
    id: int
    reading_list_id: int
    source_id: int
    position: int
    status: str
    notes: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReadingListCreate(BaseModel):
    title: str
    description: str | None = None


class ReadingListUpdate(BaseModel):
    title: str | None = None
    description: str | None = None


class ReadingListOut(BaseModel):
    id: int
    title: str
    description: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    items: list[ReadingListItemOut] = []

    model_config = {"from_attributes": True}
