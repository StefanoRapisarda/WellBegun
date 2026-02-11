from datetime import datetime

from sqlalchemy.orm import Session

from log_input_panels.models.project import Project
from log_input_panels.services.tag_service import create_entity_tag, delete_entity_tag, update_entity_tag
from log_input_panels.services.graph_cleanup import delete_entity_graph_data


def get_all(db: Session) -> list[Project]:
    return db.query(Project).order_by(Project.created_at.desc()).all()


def get_by_id(db: Session, project_id: int) -> Project | None:
    return db.query(Project).filter(Project.id == project_id).first()


def create(
    db: Session,
    title: str,
    description: str | None = None,
    status: str = "active",
    start_date: datetime | None = None,
) -> Project:
    project = Project(
        title=title,
        description=description,
        status=status,
        start_date=start_date,
    )
    db.add(project)
    db.flush()
    create_entity_tag(db, title, "project", "project", project.id)
    from log_input_panels.services.active_context_service import attach_active_context_tags
    attach_active_context_tags(db, "project", project.id)
    db.commit()
    db.refresh(project)
    return project


def update(
    db: Session,
    project_id: int,
    **kwargs,
) -> Project | None:
    project = get_by_id(db, project_id)
    if not project:
        return None
    for key, value in kwargs.items():
        if hasattr(project, key):
            setattr(project, key, value)
    if "title" in kwargs and kwargs["title"] is not None:
        update_entity_tag(db, "project", project_id, kwargs["title"])
    db.commit()
    db.refresh(project)
    return project


def delete(db: Session, project_id: int) -> bool:
    project = get_by_id(db, project_id)
    if not project:
        return False
    delete_entity_tag(db, "project", project_id)
    delete_entity_graph_data(db, "project", project_id)
    db.delete(project)
    db.commit()
    return True


def activate(db: Session, project_id: int) -> Project | None:
    project = get_by_id(db, project_id)
    if not project:
        return None
    project.is_active = True
    db.commit()
    db.refresh(project)
    return project


def deactivate(db: Session, project_id: int) -> Project | None:
    project = get_by_id(db, project_id)
    if not project:
        return None
    project.is_active = False
    db.commit()
    db.refresh(project)
    return project


def deactivate_all(db: Session) -> int:
    count = db.query(Project).filter(Project.is_active == True).update({"is_active": False})
    db.commit()
    return count


def archive(db: Session, project_id: int) -> Project | None:
    project = get_by_id(db, project_id)
    if not project:
        return None
    project.is_archived = True
    db.commit()
    db.refresh(project)
    return project


def unarchive(db: Session, project_id: int) -> Project | None:
    project = get_by_id(db, project_id)
    if not project:
        return None
    project.is_archived = False
    db.commit()
    db.refresh(project)
    return project
