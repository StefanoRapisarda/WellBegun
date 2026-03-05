from datetime import datetime

from pydantic import BaseModel


class WorkspaceCreate(BaseModel):
    name: str
    description: str | None = None


class WorkspaceUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class WorkspaceItemCreate(BaseModel):
    entity_type: str
    entity_id: int
    x: float = 0.0
    y: float = 0.0


class WorkspaceItemUpdate(BaseModel):
    x: float | None = None
    y: float | None = None
    collapsed: bool | None = None


class WorkspaceItemBulkUpdate(BaseModel):
    items: list[dict]


class WorkspaceEventCreate(BaseModel):
    event_type: str
    entity_type: str | None = None
    entity_id: int | None = None
    metadata: dict | None = None


class WorkspaceItemOut(BaseModel):
    id: int
    workspace_id: int
    entity_type: str
    entity_id: int
    x: float
    y: float
    collapsed: bool
    added_at: datetime

    model_config = {"from_attributes": True}


class WorkspaceEventOut(BaseModel):
    id: int
    workspace_id: int
    event_type: str
    entity_type: str | None = None
    entity_id: int | None = None
    metadata_json: str | None = None
    timestamp: datetime

    model_config = {"from_attributes": True}


class WorkspaceOut(BaseModel):
    id: int
    name: str
    description: str | None = None
    is_archived: bool
    created_at: datetime
    last_opened_at: datetime
    items: list[WorkspaceItemOut] = []

    model_config = {"from_attributes": True}


class WorkspaceDetailOut(WorkspaceOut):
    events: list[WorkspaceEventOut] = []
