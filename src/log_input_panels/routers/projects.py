from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from log_input_panels.database import get_db
from log_input_panels.schemas.project import ProjectCreate, ProjectOut, ProjectUpdate
from log_input_panels.services import project_service

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("/", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db)):
    return project_service.get_all(db)


@router.post("/deactivate-all")
def deactivate_all_projects(db: Session = Depends(get_db)):
    count = project_service.deactivate_all(db)
    return {"ok": True, "deactivated": count}


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: int, db: Session = Depends(get_db)):
    project = project_service.get_by_id(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("/", response_model=ProjectOut, status_code=201)
def create_project(data: ProjectCreate, db: Session = Depends(get_db)):
    return project_service.create(
        db,
        title=data.title,
        description=data.description,
        status=data.status,
        start_date=data.start_date,
    )


@router.put("/{project_id}", response_model=ProjectOut)
def update_project(project_id: int, data: ProjectUpdate, db: Session = Depends(get_db)):
    updates = data.model_dump(exclude_unset=True)
    project = project_service.update(db, project_id, **updates)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.delete("/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db)):
    if not project_service.delete(db, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    return {"ok": True}


@router.post("/{project_id}/activate", response_model=ProjectOut)
def activate_project(project_id: int, db: Session = Depends(get_db)):
    project = project_service.activate(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("/{project_id}/deactivate", response_model=ProjectOut)
def deactivate_project(project_id: int, db: Session = Depends(get_db)):
    project = project_service.deactivate(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("/{project_id}/archive", response_model=ProjectOut)
def archive_project(project_id: int, db: Session = Depends(get_db)):
    project = project_service.archive(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("/{project_id}/unarchive", response_model=ProjectOut)
def unarchive_project(project_id: int, db: Session = Depends(get_db)):
    project = project_service.unarchive(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project
