from datetime import datetime

from pydantic import BaseModel


class PlanCreate(BaseModel):
    title: str
    description: str | None = None
    motivation: str | None = None
    outcome: str | None = None
    goal: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    status: str = "planned"


class PlanUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    motivation: str | None = None
    outcome: str | None = None
    goal: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    status: str | None = None


class PlanCollectionCreate(BaseModel):
    title: str


class PlanActivityGroupAdd(BaseModel):
    activity_id: int
    header: str


class PlanRoleNoteCreate(BaseModel):
    role: str          # "motivation" | "goal" | "outcome"
    content: str


class PlanRoleNoteOut(BaseModel):
    note_id: int
    role: str
    title: str
    content: str | None


class PlanTypedCollectionCreate(BaseModel):
    title: str
    member_type: str  # "activity" | "source" | "actor"


class PlanOut(BaseModel):
    id: int
    title: str
    description: str | None = None
    motivation: str | None = None
    outcome: str | None = None
    goal: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    status: str
    is_active: bool
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    activities: list["ActivityOut"] = []

    model_config = {"from_attributes": True}


# Avoid circular import — ActivityOut is resolved at validation time
from wellbegun.schemas.log import ActivityOut  # noqa: E402, F401

PlanOut.model_rebuild()
