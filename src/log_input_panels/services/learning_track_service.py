from sqlalchemy.orm import Session, joinedload

from log_input_panels.models.learning_track import LearningGoal, LearningTrack, LearningTrackItem
from log_input_panels.services.tag_service import create_entity_tag, delete_entity_tag, update_entity_tag
from log_input_panels.services.active_context_service import attach_active_context_tags
from log_input_panels.services.graph_cleanup import delete_entity_graph_data


def get_all(db: Session) -> list[LearningTrack]:
    return (
        db.query(LearningTrack)
        .options(joinedload(LearningTrack.items), joinedload(LearningTrack.goals))
        .order_by(LearningTrack.created_at.desc())
        .all()
    )


def get_by_id(db: Session, learning_track_id: int) -> LearningTrack | None:
    return (
        db.query(LearningTrack)
        .options(joinedload(LearningTrack.items), joinedload(LearningTrack.goals))
        .filter(LearningTrack.id == learning_track_id)
        .first()
    )


def create(
    db: Session,
    title: str,
    description: str | None = None,
) -> LearningTrack:
    learning_track = LearningTrack(
        title=title,
        description=description,
    )
    db.add(learning_track)
    db.flush()
    create_entity_tag(db, title, "learning_track", "learning_track", learning_track.id)
    attach_active_context_tags(db, "learning_track", learning_track.id)
    db.commit()
    db.refresh(learning_track)
    return learning_track


def update(db: Session, learning_track_id: int, **kwargs) -> LearningTrack | None:
    learning_track = get_by_id(db, learning_track_id)
    if not learning_track:
        return None
    for key, value in kwargs.items():
        if hasattr(learning_track, key):
            setattr(learning_track, key, value)
    if "title" in kwargs and kwargs["title"] is not None:
        update_entity_tag(db, "learning_track", learning_track_id, kwargs["title"])
    db.commit()
    db.refresh(learning_track)
    return learning_track


def delete(db: Session, learning_track_id: int) -> bool:
    learning_track = get_by_id(db, learning_track_id)
    if not learning_track:
        return False
    delete_entity_tag(db, "learning_track", learning_track_id)
    delete_entity_graph_data(db, "learning_track", learning_track_id)
    db.delete(learning_track)
    db.commit()
    return True


def activate(db: Session, learning_track_id: int) -> LearningTrack | None:
    learning_track = get_by_id(db, learning_track_id)
    if not learning_track:
        return None
    learning_track.is_active = True
    db.commit()
    db.refresh(learning_track)
    return learning_track


def deactivate(db: Session, learning_track_id: int) -> LearningTrack | None:
    learning_track = get_by_id(db, learning_track_id)
    if not learning_track:
        return None
    learning_track.is_active = False
    db.commit()
    db.refresh(learning_track)
    return learning_track


# Item CRUD

def get_items(db: Session, track_id: int) -> list[LearningTrackItem]:
    return (
        db.query(LearningTrackItem)
        .filter(LearningTrackItem.learning_track_id == track_id)
        .order_by(LearningTrackItem.position)
        .all()
    )


def add_item(
    db: Session,
    track_id: int,
    source_id: int,
    position: int = 0,
    status: str = "not_started",
    notes: str | None = None,
) -> LearningTrackItem:
    item = LearningTrackItem(
        learning_track_id=track_id,
        source_id=source_id,
        position=position,
        status=status,
        notes=notes,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_item(db: Session, item_id: int, **kwargs) -> LearningTrackItem | None:
    item = db.query(LearningTrackItem).filter(LearningTrackItem.id == item_id).first()
    if not item:
        return None
    for key, value in kwargs.items():
        if hasattr(item, key):
            setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


def remove_item(db: Session, item_id: int) -> bool:
    item = db.query(LearningTrackItem).filter(LearningTrackItem.id == item_id).first()
    if not item:
        return False
    db.delete(item)
    db.commit()
    return True


# Goal CRUD

def get_goals(db: Session, track_id: int) -> list[LearningGoal]:
    return (
        db.query(LearningGoal)
        .filter(LearningGoal.learning_track_id == track_id)
        .order_by(LearningGoal.created_at)
        .all()
    )


def add_goal(
    db: Session,
    track_id: int,
    description: str,
) -> LearningGoal:
    goal = LearningGoal(
        learning_track_id=track_id,
        description=description,
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal


def update_goal(db: Session, goal_id: int, **kwargs) -> LearningGoal | None:
    goal = db.query(LearningGoal).filter(LearningGoal.id == goal_id).first()
    if not goal:
        return None
    for key, value in kwargs.items():
        if hasattr(goal, key):
            setattr(goal, key, value)
    db.commit()
    db.refresh(goal)
    return goal


def remove_goal(db: Session, goal_id: int) -> bool:
    goal = db.query(LearningGoal).filter(LearningGoal.id == goal_id).first()
    if not goal:
        return False
    db.delete(goal)
    db.commit()
    return True


def toggle_goal(db: Session, goal_id: int) -> LearningGoal | None:
    goal = db.query(LearningGoal).filter(LearningGoal.id == goal_id).first()
    if not goal:
        return None
    goal.is_completed = not goal.is_completed
    db.commit()
    db.refresh(goal)
    return goal
