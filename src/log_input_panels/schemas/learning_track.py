from datetime import datetime

from pydantic import BaseModel


class LearningTrackItemCreate(BaseModel):
    source_id: int
    position: int = 0
    status: str = "not_started"
    notes: str | None = None


class LearningTrackItemUpdate(BaseModel):
    position: int | None = None
    status: str | None = None
    notes: str | None = None


class LearningTrackItemOut(BaseModel):
    id: int
    learning_track_id: int
    source_id: int
    position: int
    status: str
    notes: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LearningTrackCreate(BaseModel):
    title: str
    description: str | None = None


class LearningTrackUpdate(BaseModel):
    title: str | None = None
    description: str | None = None


class LearningGoalCreate(BaseModel):
    description: str


class LearningGoalUpdate(BaseModel):
    description: str | None = None
    is_completed: bool | None = None


class LearningGoalOut(BaseModel):
    id: int
    learning_track_id: int
    description: str
    is_completed: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class LearningTrackOut(BaseModel):
    id: int
    title: str
    description: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    items: list[LearningTrackItemOut] = []
    goals: list[LearningGoalOut] = []

    model_config = {"from_attributes": True}
