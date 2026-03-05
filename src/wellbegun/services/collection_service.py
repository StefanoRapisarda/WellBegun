from sqlalchemy.orm import Session, joinedload

from wellbegun.models.collection import Collection, CollectionItem
from wellbegun.services import category_service
from wellbegun.services.tag_service import create_entity_tag, delete_entity_tag, update_entity_tag
from wellbegun.services.graph_cleanup import delete_entity_graph_data
from wellbegun.services.structural_relations import get_structural_predicate


def get_all(db: Session, category_id: int | None = None) -> list[Collection]:
    q = (
        db.query(Collection)
        .options(joinedload(Collection.items))
        .order_by(Collection.created_at.desc())
    )
    if category_id is not None:
        q = q.filter(Collection.category_id == category_id)
    return q.all()


def get_by_id(db: Session, collection_id: int) -> Collection | None:
    return (
        db.query(Collection)
        .options(joinedload(Collection.items))
        .filter(Collection.id == collection_id)
        .first()
    )


def create(
    db: Session,
    title: str,
    category_id: int,
    description: str | None = None,
) -> Collection:
    collection = Collection(
        title=title,
        category_id=category_id,
        description=description,
    )
    db.add(collection)
    db.flush()
    create_entity_tag(db, title, "collection", "collection", collection.id)
    db.commit()
    db.refresh(collection)
    return collection


def update(db: Session, collection_id: int, **kwargs) -> Collection | None:
    collection = get_by_id(db, collection_id)
    if not collection:
        return None
    for key, value in kwargs.items():
        if hasattr(collection, key):
            setattr(collection, key, value)
    if "title" in kwargs and kwargs["title"] is not None:
        update_entity_tag(db, "collection", collection_id, kwargs["title"])
    db.commit()
    db.refresh(collection)
    return collection


def delete(db: Session, collection_id: int) -> bool:
    collection = get_by_id(db, collection_id)
    if not collection:
        return False
    delete_entity_tag(db, "collection", collection_id)
    delete_entity_graph_data(db, "collection", collection_id)
    db.delete(collection)
    db.commit()
    return True


def activate(db: Session, collection_id: int) -> Collection | None:
    collection = get_by_id(db, collection_id)
    if not collection:
        return None
    collection.is_active = True
    db.commit()
    db.refresh(collection)
    return collection


def deactivate(db: Session, collection_id: int) -> Collection | None:
    collection = get_by_id(db, collection_id)
    if not collection:
        return None
    collection.is_active = False
    db.commit()
    db.refresh(collection)
    return collection


def archive(db: Session, collection_id: int) -> Collection | None:
    collection = get_by_id(db, collection_id)
    if not collection:
        return None
    collection.is_archived = True
    collection.is_active = False
    db.commit()
    db.refresh(collection)
    return collection


def unarchive(db: Session, collection_id: int) -> Collection | None:
    collection = get_by_id(db, collection_id)
    if not collection:
        return None
    collection.is_archived = False
    db.commit()
    db.refresh(collection)
    return collection


# --- Item CRUD ---

def add_item(
    db: Session,
    collection_id: int,
    member_entity_type: str,
    member_entity_id: int,
    position: int = 0,
    status: str | None = None,
    notes: str | None = None,
    header: str | None = None,
) -> CollectionItem:
    collection = get_by_id(db, collection_id)
    if not collection:
        raise ValueError("Collection not found")

    category = category_service.get_by_id(db, collection.category_id)
    if not category:
        raise ValueError("Category not found")

    # Auto-upgrade category to wildcard when receiving a mismatched entity type
    if category.member_entity_type != "*" and member_entity_type != category.member_entity_type:
        wildcard = category_service.get_by_slug(db, "plan_items")
        if wildcard:
            collection.category_id = wildcard.id
            db.flush()
            category = wildcard

    # Validate/assign status (only for entity types that use statuses, e.g. activities)
    valid_statuses = category_service.get_valid_statuses(db, category.id)
    if valid_statuses and member_entity_type == "activity":
        if status is None:
            status = category_service.get_default_status(db, category.id)
        elif status not in valid_statuses:
            raise ValueError(
                f"Invalid status '{status}'. Valid statuses: {', '.join(sorted(valid_statuses))}"
            )

    item = CollectionItem(
        collection_id=collection_id,
        member_entity_type=member_entity_type,
        member_entity_id=member_entity_id,
        position=position,
        status=status,
        notes=notes,
        header=header,
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    # Create "contains" knowledge triple to keep graph in sync
    from wellbegun.services import knowledge_service
    predicate = get_structural_predicate("collection", member_entity_type)
    knowledge_service.create_triple(
        db,
        subject_type="collection",
        subject_id=collection_id,
        predicate=predicate,
        object_type=member_entity_type,
        object_id=member_entity_id,
    )

    return item


def update_item(db: Session, item_id: int, **kwargs) -> CollectionItem | None:
    item = db.query(CollectionItem).filter(CollectionItem.id == item_id).first()
    if not item:
        return None

    # Validate status if being updated
    if "status" in kwargs and kwargs["status"] is not None:
        collection = get_by_id(db, item.collection_id)
        if collection:
            valid_statuses = category_service.get_valid_statuses(db, collection.category_id)
            if valid_statuses and kwargs["status"] not in valid_statuses:
                raise ValueError(
                    f"Invalid status '{kwargs['status']}'. "
                    f"Valid statuses: {', '.join(sorted(valid_statuses))}"
                )

    for key, value in kwargs.items():
        if hasattr(item, key):
            setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


def remove_item(db: Session, item_id: int) -> bool:
    item = db.query(CollectionItem).filter(CollectionItem.id == item_id).first()
    if not item:
        return False

    # Delete the "contains" knowledge triple to keep graph in sync
    from wellbegun.services import knowledge_service
    from wellbegun.models.knowledge_triple import KnowledgeTriple
    predicate = get_structural_predicate("collection", item.member_entity_type)
    triple = (
        db.query(KnowledgeTriple)
        .filter(
            KnowledgeTriple.subject_type == "collection",
            KnowledgeTriple.subject_id == item.collection_id,
            KnowledgeTriple.object_type == item.member_entity_type,
            KnowledgeTriple.object_id == item.member_entity_id,
            KnowledgeTriple.predicate == predicate,
        )
        .first()
    )
    if triple:
        db.delete(triple)

    db.delete(item)
    db.commit()
    return True
