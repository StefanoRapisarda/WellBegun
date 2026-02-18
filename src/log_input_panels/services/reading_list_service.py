from sqlalchemy.orm import Session, joinedload

from log_input_panels.models.reading_list import ReadingList, ReadingListItem
from log_input_panels.services.tag_service import create_entity_tag, delete_entity_tag, update_entity_tag
from log_input_panels.services.graph_cleanup import delete_entity_graph_data


def get_all(db: Session) -> list[ReadingList]:
    return (
        db.query(ReadingList)
        .options(joinedload(ReadingList.items))
        .order_by(ReadingList.created_at.desc())
        .all()
    )


def get_by_id(db: Session, reading_list_id: int) -> ReadingList | None:
    return (
        db.query(ReadingList)
        .options(joinedload(ReadingList.items))
        .filter(ReadingList.id == reading_list_id)
        .first()
    )


def create(
    db: Session,
    title: str,
    description: str | None = None,
) -> ReadingList:
    reading_list = ReadingList(
        title=title,
        description=description,
    )
    db.add(reading_list)
    db.flush()
    create_entity_tag(db, title, "reading_list", "reading_list", reading_list.id)
    db.commit()
    db.refresh(reading_list)
    return reading_list


def update(db: Session, reading_list_id: int, **kwargs) -> ReadingList | None:
    reading_list = get_by_id(db, reading_list_id)
    if not reading_list:
        return None
    for key, value in kwargs.items():
        if hasattr(reading_list, key):
            setattr(reading_list, key, value)
    if "title" in kwargs and kwargs["title"] is not None:
        update_entity_tag(db, "reading_list", reading_list_id, kwargs["title"])
    db.commit()
    db.refresh(reading_list)
    return reading_list


def delete(db: Session, reading_list_id: int) -> bool:
    reading_list = get_by_id(db, reading_list_id)
    if not reading_list:
        return False
    delete_entity_tag(db, "reading_list", reading_list_id)
    delete_entity_graph_data(db, "reading_list", reading_list_id)
    db.delete(reading_list)
    db.commit()
    return True


def activate(db: Session, reading_list_id: int) -> ReadingList | None:
    reading_list = get_by_id(db, reading_list_id)
    if not reading_list:
        return None
    reading_list.is_active = True
    db.commit()
    db.refresh(reading_list)
    return reading_list


def deactivate(db: Session, reading_list_id: int) -> ReadingList | None:
    reading_list = get_by_id(db, reading_list_id)
    if not reading_list:
        return None
    reading_list.is_active = False
    db.commit()
    db.refresh(reading_list)
    return reading_list


# Item CRUD

def get_items(db: Session, list_id: int) -> list[ReadingListItem]:
    return (
        db.query(ReadingListItem)
        .filter(ReadingListItem.reading_list_id == list_id)
        .order_by(ReadingListItem.position)
        .all()
    )


def add_item(
    db: Session,
    list_id: int,
    source_id: int,
    position: int = 0,
    status: str = "unread",
    notes: str | None = None,
) -> ReadingListItem:
    item = ReadingListItem(
        reading_list_id=list_id,
        source_id=source_id,
        position=position,
        status=status,
        notes=notes,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_item(db: Session, item_id: int, **kwargs) -> ReadingListItem | None:
    item = db.query(ReadingListItem).filter(ReadingListItem.id == item_id).first()
    if not item:
        return None
    for key, value in kwargs.items():
        if hasattr(item, key):
            setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


def remove_item(db: Session, item_id: int) -> bool:
    item = db.query(ReadingListItem).filter(ReadingListItem.id == item_id).first()
    if not item:
        return False
    db.delete(item)
    db.commit()
    return True
