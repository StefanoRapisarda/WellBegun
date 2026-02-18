from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from log_input_panels.database import get_db
from log_input_panels.schemas.search import SearchResult
from log_input_panels.services import search_service

router = APIRouter(prefix="/search", tags=["search"])


@router.get("/", response_model=list[SearchResult])
def search_entities(
    q: str | None = None,
    types: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    tag_ids: str | None = None,
    tag_mode: str | None = Query(default="or", pattern="^(or|and)$"),
    include_archived: bool = Query(default=False),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    entity_types = types.split(",") if types else None
    parsed_tag_ids = [int(t) for t in tag_ids.split(",") if t] if tag_ids else None

    return search_service.search(
        db,
        query=q,
        entity_types=entity_types,
        start_date=start_date,
        end_date=end_date,
        tag_ids=parsed_tag_ids,
        tag_mode=tag_mode or "or",
        include_archived=include_archived,
        limit=limit,
        offset=offset,
    )
