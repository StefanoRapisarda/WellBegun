from datetime import datetime

from pydantic import BaseModel


# --- Triple schemas ---

class TripleCreate(BaseModel):
    subject_type: str
    subject_id: int
    predicate: str
    object_type: str
    object_id: int


class TripleUpdate(BaseModel):
    predicate: str


class TripleOut(BaseModel):
    id: int
    subject_type: str
    subject_id: int
    predicate: str
    object_type: str
    object_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Board node schemas ---

class BoardNodeUpsert(BaseModel):
    entity_type: str
    entity_id: int
    x: float
    y: float


class BoardNodeUpdate(BaseModel):
    x: float | None = None
    y: float | None = None
    collapsed: bool | None = None


class BoardNodeOut(BaseModel):
    id: int
    entity_type: str
    entity_id: int
    x: float
    y: float
    collapsed: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BoardNodeBulkUpsert(BaseModel):
    nodes: list[BoardNodeUpsert]


class PopulateFocusRequest(BaseModel):
    project_ids: list[int] = []
    activity_ids: list[int] = []
