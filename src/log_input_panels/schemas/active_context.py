from pydantic import BaseModel

from log_input_panels.schemas.project import ProjectOut
from log_input_panels.schemas.log import LogOut, ActivityOut
from log_input_panels.schemas.source import SourceOut
from log_input_panels.schemas.actor import ActorOut
from log_input_panels.schemas.reading_list import ReadingListOut


class ActiveContextOut(BaseModel):
    projects: list[ProjectOut]
    logs: list[LogOut]
    activities: list[ActivityOut]
    sources: list[SourceOut]
    actors: list[ActorOut]
    reading_lists: list[ReadingListOut]
