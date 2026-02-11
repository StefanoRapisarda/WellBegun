from datetime import datetime

from pydantic import BaseModel


class LogCreate(BaseModel):
    log_type: str
    title: str
    content: str | None = None


class LogUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    log_type: str | None = None


class LogOut(BaseModel):
    id: int
    log_type: str
    title: str
    content: str | None = None
    is_active: bool
    is_archived: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ActivityCreate(BaseModel):
    log_id: int | None = None
    title: str
    description: str | None = None
    duration: int | None = None
    status: str = "todo"


class ActivityUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    duration: int | None = None
    status: str | None = None


class ActivityOut(BaseModel):
    id: int
    log_id: int | None = None
    title: str
    description: str | None = None
    duration: int | None = None
    status: str
    is_active: bool
    is_archived: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
