from datetime import datetime

from pydantic import BaseModel

from log_input_panels.schemas.tag import TagOut


class SearchQuery(BaseModel):
    query: str | None = None
    entity_types: list[str] | None = None
    start_date: str | None = None
    end_date: str | None = None
    tag_ids: list[int] | None = None
    limit: int = 50
    offset: int = 0


class SearchResult(BaseModel):
    type: str
    id: int
    title: str
    description: str | None = None
    created_at: datetime
    updated_at: datetime
    tags: list[TagOut] = []

    model_config = {"from_attributes": True}
