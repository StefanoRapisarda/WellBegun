from sqlalchemy.orm import Session

from wellbegun.models.collection import Category, CategoryStatus


def get_all(db: Session) -> list[Category]:
    return db.query(Category).order_by(Category.slug).all()


def get_by_id(db: Session, category_id: int) -> Category | None:
    return db.query(Category).filter(Category.id == category_id).first()


def get_by_slug(db: Session, slug: str) -> Category | None:
    return db.query(Category).filter(Category.slug == slug).first()


def create(
    db: Session,
    slug: str,
    display_name: str,
    member_entity_type: str,
) -> Category:
    category = Category(
        slug=slug,
        display_name=display_name,
        member_entity_type=member_entity_type,
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def update(db: Session, category_id: int, **kwargs) -> Category | None:
    category = get_by_id(db, category_id)
    if not category:
        return None
    for key, value in kwargs.items():
        if hasattr(category, key):
            setattr(category, key, value)
    db.commit()
    db.refresh(category)
    return category


def delete(db: Session, category_id: int) -> bool:
    category = get_by_id(db, category_id)
    if not category:
        return False
    db.delete(category)
    db.commit()
    return True


# --- Status CRUD ---

def get_statuses(db: Session, category_id: int) -> list[CategoryStatus]:
    return (
        db.query(CategoryStatus)
        .filter(CategoryStatus.category_id == category_id)
        .order_by(CategoryStatus.position)
        .all()
    )


def add_status(
    db: Session,
    category_id: int,
    value: str,
    position: int = 0,
    is_default: bool = False,
) -> CategoryStatus:
    status = CategoryStatus(
        category_id=category_id,
        value=value,
        position=position,
        is_default=is_default,
    )
    db.add(status)
    db.commit()
    db.refresh(status)
    return status


def update_status(db: Session, status_id: int, **kwargs) -> CategoryStatus | None:
    status = db.query(CategoryStatus).filter(CategoryStatus.id == status_id).first()
    if not status:
        return None
    for key, value in kwargs.items():
        if hasattr(status, key):
            setattr(status, key, value)
    db.commit()
    db.refresh(status)
    return status


def delete_status(db: Session, status_id: int) -> bool:
    status = db.query(CategoryStatus).filter(CategoryStatus.id == status_id).first()
    if not status:
        return False
    db.delete(status)
    db.commit()
    return True


# --- Helpers ---

def get_default_status(db: Session, category_id: int) -> str | None:
    status = (
        db.query(CategoryStatus)
        .filter(CategoryStatus.category_id == category_id, CategoryStatus.is_default.is_(True))
        .first()
    )
    return status.value if status else None


def get_valid_statuses(db: Session, category_id: int) -> set[str]:
    statuses = get_statuses(db, category_id)
    return {s.value for s in statuses}


# --- Seeding ---

def seed_categories(db: Session) -> None:
    """Seed default categories with statuses."""
    # --- reading_list (source) ---
    if not get_by_slug(db, "reading_list"):
        cat = Category(slug="reading_list", display_name="Reading List", member_entity_type="source")
        db.add(cat)
        db.flush()
        for i, (val, is_def) in enumerate([("unread", True), ("reading", False), ("read", False)]):
            db.add(CategoryStatus(category_id=cat.id, value=val, position=i, is_default=is_def))

    # --- plan_activities (activity) ---
    if not get_by_slug(db, "plan_activities"):
        cat = Category(slug="plan_activities", display_name="Plan Activities", member_entity_type="activity")
        db.add(cat)
        db.flush()
        for i, (val, is_def) in enumerate([("todo", True), ("in_progress", False), ("done", False)]):
            db.add(CategoryStatus(category_id=cat.id, value=val, position=i, is_default=is_def))

    # --- plan_sources (source) ---
    if not get_by_slug(db, "plan_sources"):
        cat = Category(slug="plan_sources", display_name="Plan Sources", member_entity_type="source")
        db.add(cat)
        db.flush()

    # --- plan_actors (actor) ---
    if not get_by_slug(db, "plan_actors"):
        cat = Category(slug="plan_actors", display_name="Plan Actors", member_entity_type="actor")
        db.add(cat)
        db.flush()

    # --- plan_items (mixed: activities, sources, actors) ---
    if not get_by_slug(db, "plan_items"):
        cat = Category(slug="plan_items", display_name="Plan Items", member_entity_type="*")
        db.add(cat)
        db.flush()
        for i, (val, is_def) in enumerate([("todo", True), ("in_progress", False), ("done", False)]):
            db.add(CategoryStatus(category_id=cat.id, value=val, position=i, is_default=is_def))

    db.commit()
