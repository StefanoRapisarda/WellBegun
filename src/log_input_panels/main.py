from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from log_input_panels.config import settings
from log_input_panels.database import SessionLocal, engine
from log_input_panels.models import Base
from log_input_panels.routers import (
    active_context,
    activities,
    actors,
    assistant,
    documents,
    health,
    knowledge,
    learning_tracks,
    logs,
    notes,
    projects,
    reading_lists,
    scaffolding,
    search,
    sources,
    tags,
    web_proxy,
)
from log_input_panels.services.tag_service import seed_wild_tags


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_wild_tags(db)
    finally:
        db.close()
    yield


app = FastAPI(title="WellBegun", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(tags.router, prefix="/api")
app.include_router(projects.router, prefix="/api")
app.include_router(logs.router, prefix="/api")
app.include_router(notes.router, prefix="/api")
app.include_router(sources.router, prefix="/api")
app.include_router(actors.router, prefix="/api")
app.include_router(activities.router, prefix="/api")
app.include_router(reading_lists.router, prefix="/api")
app.include_router(learning_tracks.router, prefix="/api")
app.include_router(search.router, prefix="/api")
app.include_router(active_context.router, prefix="/api")
app.include_router(assistant.router, prefix="/api")
app.include_router(scaffolding.router, prefix="/api")
app.include_router(knowledge.router, prefix="/api")
app.include_router(web_proxy.router, prefix="/api")
app.include_router(documents.router)
