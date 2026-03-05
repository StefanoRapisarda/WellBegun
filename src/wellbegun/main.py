from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from wellbegun.config import settings
from sqlalchemy import inspect, text

from wellbegun.database import SessionLocal, engine
from wellbegun.models import Base
from wellbegun.routers import (
    active_context,
    activities,
    actors,
    assistant,
    categories,
    coffee,
    collections,
    documents,
    workspaces,
    health,
    journal,
    knowledge,
    logs,
    notes,
    plans,
    projects,

    scaffolding,
    search,
    sources,
    tags,
    web_proxy,
)
from wellbegun.services.tag_service import seed_wild_tags
from wellbegun.services.category_service import seed_categories
from wellbegun.services import llm_service


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
        if "goal" not in plan_cols:
            with engine_ref.begin() as conn:
                conn.execute(text("ALTER TABLE plans ADD COLUMN goal TEXT"))

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

    # --- Phase 1: Add missing columns ---

    # Note: is_active
    note_cols = {c["name"] for c in insp.get_columns("notes")}
    if "is_active" not in note_cols:
        with engine_ref.begin() as conn:
            conn.execute(text("ALTER TABLE notes ADD COLUMN is_active BOOLEAN DEFAULT 0 NOT NULL"))

    # Plan: status
    plan_cols2 = {c["name"] for c in insp.get_columns("plans")}
    if "status" not in plan_cols2:
        with engine_ref.begin() as conn:
            conn.execute(text("ALTER TABLE plans ADD COLUMN status VARCHAR(20) DEFAULT 'planned' NOT NULL"))

    # Source: status
    source_cols2 = {c["name"] for c in insp.get_columns("sources")}
    if "status" not in source_cols2:
        with engine_ref.begin() as conn:
            conn.execute(text("ALTER TABLE sources ADD COLUMN status VARCHAR(20) DEFAULT 'to_read' NOT NULL"))

    # --- Phase 2: Extend Activity for Plan absorption ---

    activity_cols = {c["name"] for c in insp.get_columns("activities")}
    with engine_ref.begin() as conn:
        if "activity_date" not in activity_cols:
            conn.execute(text("ALTER TABLE activities ADD COLUMN activity_date DATETIME"))
        if "plan_id" not in activity_cols:
            conn.execute(text("ALTER TABLE activities ADD COLUMN plan_id INTEGER REFERENCES plans(id) ON DELETE SET NULL"))
        if "reading_list_id" not in activity_cols:
            conn.execute(text("ALTER TABLE activities ADD COLUMN reading_list_id INTEGER"))
        if "source_id" not in activity_cols:
            conn.execute(text("ALTER TABLE activities ADD COLUMN source_id INTEGER REFERENCES sources(id) ON DELETE SET NULL"))
        if "position" not in activity_cols:
            conn.execute(text("ALTER TABLE activities ADD COLUMN position INTEGER DEFAULT 0 NOT NULL"))
        if "header" not in activity_cols:
            conn.execute(text("ALTER TABLE activities ADD COLUMN header VARCHAR(255)"))

    # --- Phase 3: Data migration — PlanItems → Activity rows ---

    # Guard: only run if no Activity already has plan_id set
    with engine_ref.begin() as conn:
        has_plan_activities = conn.execute(
            text("SELECT COUNT(*) FROM activities WHERE plan_id IS NOT NULL")
        ).scalar()
        if has_plan_activities == 0 and "plan_items" in insp.get_table_names():
            rows = conn.execute(text(
                "SELECT pi.plan_id, pi.activity_id, pi.position, pi.is_done, pi.header "
                "FROM plan_items pi"
            )).fetchall()
            for row in rows:
                plan_id, activity_id, position, is_done, header = row
                new_status = "done" if is_done else "todo"
                conn.execute(text(
                    "UPDATE activities SET plan_id = :plan_id, position = :position, "
                    "status = :status, header = :header WHERE id = :activity_id"
                ), {
                    "plan_id": plan_id,
                    "position": position,
                    "status": new_status,
                    "header": header,
                    "activity_id": activity_id,
                })

    # Rename "has expected outcome" → "has outcome" in knowledge triples
    if "knowledge_triples" in insp.get_table_names():
        with engine_ref.begin() as conn:
            conn.execute(text(
                "UPDATE knowledge_triples SET predicate = 'has outcome' "
                "WHERE predicate = 'has expected outcome'"
            ))



    # --- Drop log_type column from logs (migrate values to tags) ---
    log_cols2 = {c["name"] for c in insp.get_columns("logs")}
    if "log_type" in log_cols2:
        with engine_ref.begin() as conn:
            # Collect log_type values that should become tags
            rows = conn.execute(text(
                "SELECT id, log_type FROM logs WHERE log_type IS NOT NULL AND log_type != '' AND log_type != 'diary'"
            )).fetchall()
            tag_map = {"work": "Work", "travel": "Travel", "health": "Health"}
            for row in rows:
                log_id, log_type_val = row
                tag_name = tag_map.get(log_type_val.lower())
                if not tag_name:
                    continue
                # Find or skip the tag — it will be created by seed_default_tags later
                tag_row = conn.execute(text(
                    "SELECT id FROM tags WHERE name = :name AND category = 'log' AND entity_id IS NULL"
                ), {"name": tag_name}).first()
                if not tag_row:
                    # Create the tag now so we can attach it
                    import datetime
                    now = datetime.datetime.utcnow().isoformat()
                    conn.execute(text(
                        "INSERT INTO tags (name, category, full_tag, entity_type, entity_id, is_system, created_at) "
                        "VALUES (:name, 'log', :full_tag, NULL, NULL, 1, :now)"
                    ), {"name": tag_name, "full_tag": f"#log: {tag_name}-{now}", "now": now})
                    tag_row = conn.execute(text(
                        "SELECT id FROM tags WHERE name = :name AND category = 'log' AND entity_id IS NULL"
                    ), {"name": tag_name}).first()
                if tag_row:
                    tag_id = tag_row[0]
                    # Check if already attached
                    existing = conn.execute(text(
                        "SELECT id FROM entity_tags WHERE tag_id = :tag_id AND target_type = 'log' AND target_id = :log_id"
                    ), {"tag_id": tag_id, "log_id": log_id}).first()
                    if not existing:
                        import datetime
                        now = datetime.datetime.utcnow().isoformat()
                        conn.execute(text(
                            "INSERT INTO entity_tags (tag_id, target_type, target_id, created_at) "
                            "VALUES (:tag_id, 'log', :log_id, :now)"
                        ), {"tag_id": tag_id, "log_id": log_id, "now": now})

            # Recreate logs table without log_type
            conn.execute(text("CREATE TABLE logs_backup AS SELECT * FROM logs"))
            conn.execute(text("DROP TABLE logs"))
            conn.execute(text(
                "CREATE TABLE logs ("
                "id INTEGER PRIMARY KEY, "
                "title VARCHAR(255) NOT NULL, "
                "content TEXT, "
                "location VARCHAR(255), "
                "mood VARCHAR(10), "
                "weather VARCHAR(10), "
                "day_theme VARCHAR(10), "
                "is_active BOOLEAN NOT NULL DEFAULT 0, "
                "is_archived BOOLEAN NOT NULL DEFAULT 0, "
                "created_at DATETIME NOT NULL, "
                "updated_at DATETIME NOT NULL)"
            ))
            conn.execute(text(
                "INSERT INTO logs (id, title, content, location, mood, weather, day_theme, "
                "is_active, is_archived, created_at, updated_at) "
                "SELECT id, title, content, location, mood, weather, day_theme, "
                "is_active, is_archived, created_at, updated_at FROM logs_backup"
            ))
            conn.execute(text("DROP TABLE logs_backup"))

    # Drop reading list tables (entity removed — migrated to collections)
    tables = insp.get_table_names()
    if "reading_lists" in tables:
        with engine_ref.begin() as conn:
            # Clean up orphaned references
            conn.execute(text("UPDATE activities SET reading_list_id = NULL WHERE reading_list_id IS NOT NULL"))
            conn.execute(text("DELETE FROM entity_tags WHERE target_type = 'reading_list'"))
            conn.execute(text("DELETE FROM tags WHERE entity_type = 'reading_list'"))
            conn.execute(text("DELETE FROM knowledge_triples WHERE subject_type = 'reading_list' OR object_type = 'reading_list'"))
            if "reading_list_items" in tables:
                conn.execute(text("DROP TABLE reading_list_items"))
            conn.execute(text("DROP TABLE reading_lists"))


def _migrate_plan_collections(db) -> None:
    """Backfill plan→collection links for existing plans.

    Migrates direct plan→activity/source/actor triples to
    plan→collection→entity pattern.  Idempotent (checks for existing
    'has activities/sources/actors' triples before creating).
    """
    from wellbegun.models.plan import Plan
    from wellbegun.models.log import Activity
    from wellbegun.models.knowledge_triple import KnowledgeTriple
    from wellbegun.models.collection import CollectionItem
    from wellbegun.services.plan_service import ensure_plan_collection
    from wellbegun.services import collection_service

    plans = db.query(Plan).all()
    if not plans:
        return

    for plan in plans:
        # 1. Activities with plan_id FK → add to plan's activities collection
        fk_activities = db.query(Activity).filter(Activity.plan_id == plan.id).all()
        if fk_activities:
            # Check if collection already exists
            existing = (
                db.query(KnowledgeTriple)
                .filter(
                    KnowledgeTriple.subject_type == "plan",
                    KnowledgeTriple.subject_id == plan.id,
                    KnowledgeTriple.predicate == "has activities",
                    KnowledgeTriple.object_type == "collection",
                )
                .first()
            )
            if not existing:
                try:
                    coll = ensure_plan_collection(db, plan.id, "activities", "activity")
                    for act in fk_activities:
                        # Check if already in collection
                        exists = (
                            db.query(CollectionItem)
                            .filter(
                                CollectionItem.collection_id == coll.id,
                                CollectionItem.member_entity_type == "activity",
                                CollectionItem.member_entity_id == act.id,
                            )
                            .first()
                        )
                        if not exists:
                            try:
                                collection_service.add_item(
                                    db, coll.id,
                                    member_entity_type="activity",
                                    member_entity_id=act.id,
                                    position=act.position or 0,
                                    status=act.status or "todo",
                                    header=act.header,
                                )
                            except ValueError:
                                pass
                except ValueError:
                    pass

        # 2. Direct plan→source triples ("uses source") → migrate to collection
        source_triples = (
            db.query(KnowledgeTriple)
            .filter(
                KnowledgeTriple.subject_type == "plan",
                KnowledgeTriple.subject_id == plan.id,
                KnowledgeTriple.predicate == "uses source",
                KnowledgeTriple.object_type == "source",
            )
            .all()
        )
        if source_triples:
            try:
                coll = ensure_plan_collection(db, plan.id, "sources", "source")
                for t in source_triples:
                    exists = (
                        db.query(CollectionItem)
                        .filter(
                            CollectionItem.collection_id == coll.id,
                            CollectionItem.member_entity_type == "source",
                            CollectionItem.member_entity_id == t.object_id,
                        )
                        .first()
                    )
                    if not exists:
                        try:
                            collection_service.add_item(
                                db, coll.id,
                                member_entity_type="source",
                                member_entity_id=t.object_id,
                            )
                        except ValueError:
                            pass
                    db.delete(t)
                db.commit()
            except ValueError:
                pass

        # 3. Direct plan→actor triples ("involves actor") → migrate to collection
        actor_triples = (
            db.query(KnowledgeTriple)
            .filter(
                KnowledgeTriple.subject_type == "plan",
                KnowledgeTriple.subject_id == plan.id,
                KnowledgeTriple.predicate == "involves actor",
                KnowledgeTriple.object_type == "actor",
            )
            .all()
        )
        if actor_triples:
            try:
                coll = ensure_plan_collection(db, plan.id, "actors", "actor")
                for t in actor_triples:
                    exists = (
                        db.query(CollectionItem)
                        .filter(
                            CollectionItem.collection_id == coll.id,
                            CollectionItem.member_entity_type == "actor",
                            CollectionItem.member_entity_id == t.object_id,
                        )
                        .first()
                    )
                    if not exists:
                        try:
                            collection_service.add_item(
                                db, coll.id,
                                member_entity_type="actor",
                                member_entity_id=t.object_id,
                            )
                        except ValueError:
                            pass
                    db.delete(t)
                db.commit()
            except ValueError:
                pass

    # 4. Delete remaining direct plan→activity triples ("has activity")
    db.query(KnowledgeTriple).filter(
        KnowledgeTriple.subject_type == "plan",
        KnowledgeTriple.predicate == "has activity",
        KnowledgeTriple.object_type == "activity",
    ).delete(synchronize_session=False)

    # Also clean up "has source" and "assigned to" direct plan triples
    db.query(KnowledgeTriple).filter(
        KnowledgeTriple.subject_type == "plan",
        KnowledgeTriple.predicate == "has source",
        KnowledgeTriple.object_type == "source",
    ).delete(synchronize_session=False)
    db.query(KnowledgeTriple).filter(
        KnowledgeTriple.subject_type == "plan",
        KnowledgeTriple.predicate == "assigned to",
        KnowledgeTriple.object_type == "actor",
    ).delete(synchronize_session=False)

    db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    Base.metadata.create_all(bind=engine)
    _run_migrations(engine)
    db = SessionLocal()
    try:
        seed_wild_tags(db)
        seed_categories(db)
        _migrate_plan_collections(db)
    finally:
        db.close()
    # Non-blocking Ollama health check
    try:
        healthy = await llm_service.check_health()
        if healthy:
            print("[WellBegun] Ollama is reachable")
        else:
            print("[WellBegun] Ollama is not reachable — Journal/Coffee Table features will be unavailable")
    except Exception:
        print("[WellBegun] Ollama health check failed")
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

app.include_router(plans.router, prefix="/api")
app.include_router(search.router, prefix="/api")
app.include_router(active_context.router, prefix="/api")
app.include_router(assistant.router, prefix="/api")
app.include_router(scaffolding.router, prefix="/api")
app.include_router(knowledge.router, prefix="/api")
app.include_router(web_proxy.router, prefix="/api")
app.include_router(journal.router, prefix="/api")
app.include_router(coffee.router, prefix="/api")
app.include_router(categories.router, prefix="/api")
app.include_router(collections.router, prefix="/api")
app.include_router(documents.router)
app.include_router(workspaces.router, prefix="/api")
