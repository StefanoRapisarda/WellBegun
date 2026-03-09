from datetime import datetime

from pydantic import BaseModel


class LogCreate(BaseModel):
    title: str
    content: str | None = None
    location: str | None = None
    mood: str | None = None
    weather: str | None = None
    day_theme: str | None = None


class LogUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    location: str | None = None
    mood: str | None = None
    weather: str | None = None
    day_theme: str | None = None


class LogOut(BaseModel):
    id: int
    title: str
    content: str | None = None
    location: str | None = None
    mood: str | None = None
    weather: str | None = None
    day_theme: str | None = None
    is_active: bool
    is_archived: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ActivityCreate(BaseModel):
    log_id: int | None = None
    plan_id: int | None = None

    source_id: int | None = None
    title: str
    description: str | None = None
    duration: int | None = None
    position: int = 0
    header: str | None = None
    status: str = "todo"
    outcome: str | None = None
    activity_date: datetime | None = None


class ActivityUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    duration: int | None = None
    status: str | None = None
    outcome: str | None = None
    plan_id: int | None = None

    source_id: int | None = None
    position: int | None = None
    header: str | None = None
    activity_date: datetime | None = None


class ActivityOut(BaseModel):
    id: int
    log_id: int | None = None
    plan_id: int | None = None

    source_id: int | None = None
    title: str
    description: str | None = None
    duration: int | None = None
    position: int
    header: str | None = None
    status: str
    outcome: str | None = None
    activity_date: datetime | None = None
    is_active: bool
    is_archived: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
