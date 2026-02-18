from datetime import datetime

from pydantic import BaseModel


class PlanItemCreate(BaseModel):
    activity_id: int
    position: int = 0
    is_done: bool = False
    notes: str | None = None
    header: str | None = None


class PlanItemUpdate(BaseModel):
    position: int | None = None
    is_done: bool | None = None
    notes: str | None = None
    header: str | None = None


class PlanItemOut(BaseModel):
    id: int
    plan_id: int
    activity_id: int
    position: int
    is_done: bool
    notes: str | None = None
    header: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PlanCreate(BaseModel):
    title: str
    description: str | None = None
    motivation: str | None = None
    outcome: str | None = None
    start_date: str | None = None
    end_date: str | None = None


class PlanUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    motivation: str | None = None
    outcome: str | None = None
    start_date: str | None = None
    end_date: str | None = None


class PlanOut(BaseModel):
    id: int
    title: str
    description: str | None = None
    motivation: str | None = None
    outcome: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    is_active: bool
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    items: list[PlanItemOut] = []

    model_config = {"from_attributes": True}
