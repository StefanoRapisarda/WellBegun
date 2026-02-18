from datetime import datetime

from pydantic import BaseModel


class ActorCreate(BaseModel):
    full_name: str
    role: str | None = None
    affiliation: str | None = None
    expertise: str | None = None
    notes: str | None = None
    email: str | None = None
    url: str | None = None


class ActorUpdate(BaseModel):
    full_name: str | None = None
    role: str | None = None
    affiliation: str | None = None
    expertise: str | None = None
    notes: str | None = None
    email: str | None = None
    url: str | None = None


class ActorOut(BaseModel):
    id: int
    full_name: str
    role: str | None = None
    affiliation: str | None = None
    expertise: str | None = None
    notes: str | None = None
    email: str | None = None
    url: str | None = None
    is_active: bool
    is_archived: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
