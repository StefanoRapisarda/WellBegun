from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from log_input_panels.config import settings
from sqlalchemy import inspect, text

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
    logs,
    notes,
    plans,
    projects,
    reading_lists,
    scaffolding,
    search,
    sources,
    tags,
    web_proxy,
)
from log_input_panels.services.tag_service import seed_wild_tags


def _run_migrations(engine_ref) -> None:
    """Add missing columns to existing tables (lightweight migration)."""
    insp = inspect(engine_ref)

    source_cols = {c["name"] for c in insp.get_columns("sources")}
    if "author" not in source_cols:
        with engine_ref.begin() as conn:
            conn.execute(text("ALTER TABLE sources ADD COLUMN author VARCHAR(255)"))

    log_cols = {c["name"] for c in insp.get_columns("logs")}
    with engine_ref.begin() as conn:
        if "location" not in log_cols:
            conn.execute(text("ALTER TABLE logs ADD COLUMN location VARCHAR(255)"))
        if "mood" not in log_cols:
            conn.execute(text("ALTER TABLE logs ADD COLUMN mood VARCHAR(10)"))
        if "weather" not in log_cols:
            conn.execute(text("ALTER TABLE logs ADD COLUMN weather VARCHAR(10)"))
        if "day_theme" not in log_cols:
            conn.execute(text("ALTER TABLE logs ADD COLUMN day_theme VARCHAR(10)"))

    if "plans" in insp.get_table_names():
        plan_cols = {c["name"] for c in insp.get_columns("plans")}
        if "is_archived" not in plan_cols:
            with engine_ref.begin() as conn:
                conn.execute(text("ALTER TABLE plans ADD COLUMN is_archived BOOLEAN DEFAULT 0 NOT NULL"))

    tag_cols = {c["name"] for c in insp.get_columns("tags")}
    if "color" not in tag_cols:
        with engine_ref.begin() as conn:
            conn.execute(text("ALTER TABLE tags ADD COLUMN color VARCHAR(7)"))

    # Add header column to plan_items
    if "plan_items" in insp.get_table_names():
        pi_cols = {c["name"] for c in insp.get_columns("plan_items")}
        if "header" not in pi_cols:
            with engine_ref.begin() as conn:
                conn.execute(text("ALTER TABLE plan_items ADD COLUMN header VARCHAR(255)"))

    # Drop learning track tables (entity removed)
    tables = insp.get_table_names()
    if "learning_tracks" in tables:
        with engine_ref.begin() as conn:
            if "learning_goals" in tables:
                conn.execute(text("DROP TABLE learning_goals"))
            if "learning_track_items" in tables:
                conn.execute(text("DROP TABLE learning_track_items"))
            conn.execute(text("DROP TABLE learning_tracks"))
            # Clean up orphaned references
            conn.execute(text("DELETE FROM entity_tags WHERE target_type = 'learning_track'"))
            conn.execute(text("DELETE FROM tags WHERE entity_type = 'learning_track'"))
            conn.execute(text("DELETE FROM knowledge_triples WHERE subject_type = 'learning_track' OR object_type = 'learning_track'"))


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    Base.metadata.create_all(bind=engine)
    _run_migrations(engine)
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
app.include_router(plans.router, prefix="/api")
app.include_router(search.router, prefix="/api")
app.include_router(active_context.router, prefix="/api")
app.include_router(assistant.router, prefix="/api")
app.include_router(scaffolding.router, prefix="/api")
app.include_router(knowledge.router, prefix="/api")
app.include_router(web_proxy.router, prefix="/api")
app.include_router(documents.router)
