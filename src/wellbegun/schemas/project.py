from datetime import datetime

from pydantic import BaseModel


class ProjectCreate(BaseModel):
    title: str
    description: str | None = None
    status: str = "in_progress"
    start_date: datetime | None = None


class ProjectUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    start_date: datetime | None = None


class ProjectOut(BaseModel):
    id: int
    title: str
    description: str | None = None
    status: str
    is_active: bool
    is_archived: bool
    start_date: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
