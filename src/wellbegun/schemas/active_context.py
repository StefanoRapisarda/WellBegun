from pydantic import BaseModel

from wellbegun.schemas.project import ProjectOut
from wellbegun.schemas.log import LogOut, ActivityOut
from wellbegun.schemas.source import SourceOut
from wellbegun.schemas.actor import ActorOut


class ActiveContextOut(BaseModel):
    projects: list[ProjectOut]
    logs: list[LogOut]
    activities: list[ActivityOut]
    sources: list[SourceOut]
    actors: list[ActorOut]
