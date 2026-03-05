from datetime import datetime

from pydantic import BaseModel


class SourceCreate(BaseModel):
    title: str
    description: str | None = None
    author: str | None = None
    content_url: str | None = None
    source_type: str | None = None
    status: str = "to_read"


class SourceUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    author: str | None = None
    content_url: str | None = None
    source_type: str | None = None
    status: str | None = None


class SourceOut(BaseModel):
    id: int
    title: str
    description: str | None = None
    author: str | None = None
    content_url: str | None = None
    source_type: str | None = None
    status: str
    is_active: bool
    is_archived: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
