from datetime import datetime

from sqlalchemy.orm import Session

from log_input_panels.models.board_node import BoardNode


def get_all_nodes(db: Session) -> list[BoardNode]:
    return db.query(BoardNode).order_by(BoardNode.created_at).all()


def upsert_node(
    db: Session, entity_type: str, entity_id: int, x: float, y: float
) -> BoardNode:
    """Create or update a board node position."""
    node = (
        db.query(BoardNode)
        .filter(BoardNode.entity_type == entity_type, BoardNode.entity_id == entity_id)
        .first()
    )
    if node:
        node.x = x
        node.y = y
        node.updated_at = datetime.utcnow()
    else:
        node = BoardNode(entity_type=entity_type, entity_id=entity_id, x=x, y=y)
        db.add(node)
    db.commit()
    db.refresh(node)
    return node


def update_node(
    db: Session,
    node_id: int,
    x: float | None = None,
    y: float | None = None,
    collapsed: bool | None = None,
) -> BoardNode | None:
    node = db.query(BoardNode).filter(BoardNode.id == node_id).first()
    if not node:
        return None
    if x is not None:
        node.x = x
    if y is not None:
        node.y = y
    if collapsed is not None:
        node.collapsed = collapsed
    node.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(node)
    return node


def delete_node(db: Session, entity_type: str, entity_id: int) -> bool:
    node = (
        db.query(BoardNode)
        .filter(BoardNode.entity_type == entity_type, BoardNode.entity_id == entity_id)
        .first()
    )
    if not node:
        return False
    db.delete(node)
    db.commit()
    return True


def bulk_upsert_nodes(
    db: Session, nodes_list: list[dict]
) -> list[BoardNode]:
    """Batch upsert board node positions.

    Each dict in nodes_list should have: entity_type, entity_id, x, y
    """
    results = []
    for data in nodes_list:
        node = (
            db.query(BoardNode)
            .filter(
                BoardNode.entity_type == data["entity_type"],
                BoardNode.entity_id == data["entity_id"],
            )
            .first()
        )
        if node:
            node.x = data["x"]
            node.y = data["y"]
            node.updated_at = datetime.utcnow()
        else:
            node = BoardNode(
                entity_type=data["entity_type"],
                entity_id=data["entity_id"],
                x=data["x"],
                y=data["y"],
            )
            db.add(node)
        results.append(node)
    db.commit()
    for node in results:
        db.refresh(node)
    return results
