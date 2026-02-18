"""Shared cleanup for board nodes and triples when an entity is deleted."""

from sqlalchemy import or_
from sqlalchemy.orm import Session

from wellbegun.models.board_node import BoardNode
from wellbegun.models.knowledge_triple import KnowledgeTriple


def delete_entity_graph_data(db: Session, entity_type: str, entity_id: int) -> None:
    """Remove board node and all triples for a deleted entity.

    Does NOT commit — caller is responsible for committing the transaction.
    """
    # Delete board node
    node = (
        db.query(BoardNode)
        .filter(BoardNode.entity_type == entity_type, BoardNode.entity_id == entity_id)
        .first()
    )
    if node:
        db.delete(node)

    # Delete all triples where entity is subject or object
    triples = (
        db.query(KnowledgeTriple)
        .filter(
            or_(
                (KnowledgeTriple.subject_type == entity_type)
                & (KnowledgeTriple.subject_id == entity_id),
                (KnowledgeTriple.object_type == entity_type)
                & (KnowledgeTriple.object_id == entity_id),
            )
        )
        .all()
    )
    for t in triples:
        db.delete(t)
