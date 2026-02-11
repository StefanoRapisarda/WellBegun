"""Router for document operations (save/load markdown files)."""

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/documents", tags=["documents"])


class SaveDocumentRequest(BaseModel):
    path: str
    content: str
    title: str | None = None


class DocumentInfo(BaseModel):
    name: str
    path: str
    modified: str


@router.post("/save")
def save_document(request: SaveDocumentRequest) -> dict[str, Any]:
    """Save markdown content to a file."""
    try:
        file_path = Path(request.path).expanduser().resolve()

        # Security check: ensure it's a markdown file
        if not file_path.suffix.lower() in ('.md', '.markdown', '.txt'):
            raise HTTPException(
                status_code=400,
                detail="Only markdown (.md, .markdown) and text (.txt) files are allowed"
            )

        # Create parent directories if needed
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write content
        file_path.write_text(request.content, encoding='utf-8')

        return {
            "success": True,
            "message": f"Saved to {file_path}",
            "path": str(file_path)
        }
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/load")
def load_document(path: str) -> dict[str, Any]:
    """Load markdown content from a file."""
    try:
        file_path = Path(path).expanduser().resolve()

        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")

        if not file_path.is_file():
            raise HTTPException(status_code=400, detail="Path is not a file")

        content = file_path.read_text(encoding='utf-8')

        return {
            "success": True,
            "content": content,
            "title": file_path.stem,
            "path": str(file_path)
        }
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File is not a valid text file")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
def list_documents(path: str = "~") -> dict[str, Any]:
    """List markdown files in a directory."""
    try:
        target_path = Path(path).expanduser().resolve()

        if not target_path.exists():
            raise HTTPException(status_code=404, detail="Directory not found")

        if not target_path.is_dir():
            raise HTTPException(status_code=400, detail="Path is not a directory")

        files: list[dict[str, str]] = []
        directories: list[dict[str, str]] = []

        for item in sorted(target_path.iterdir()):
            if item.name.startswith('.'):
                continue

            try:
                if item.is_dir():
                    directories.append({
                        "name": item.name,
                        "path": str(item),
                        "type": "directory"
                    })
                elif item.suffix.lower() in ('.md', '.markdown', '.txt'):
                    stat = item.stat()
                    from datetime import datetime
                    modified = datetime.fromtimestamp(stat.st_mtime).isoformat()
                    files.append({
                        "name": item.name,
                        "path": str(item),
                        "type": "file",
                        "modified": modified
                    })
            except PermissionError:
                continue

        return {
            "current": str(target_path),
            "parent": str(target_path.parent) if target_path.parent != target_path else None,
            "directories": directories,
            "files": files
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recent")
def get_recent_documents() -> dict[str, Any]:
    """Get recently opened documents from localStorage-synced storage."""
    # This would typically be stored in a database or file
    # For now, return empty list - frontend will manage recent files in localStorage
    return {"recent": []}


class CreateItemRequest(BaseModel):
    path: str
    name: str


@router.post("/create-directory")
def create_directory(request: CreateItemRequest) -> dict[str, Any]:
    """Create a new directory."""
    try:
        parent_path = Path(request.path).expanduser().resolve()
        new_dir = parent_path / request.name

        if new_dir.exists():
            raise HTTPException(status_code=400, detail="Directory already exists")

        new_dir.mkdir(parents=True, exist_ok=False)

        return {
            "success": True,
            "message": f"Created directory: {request.name}",
            "path": str(new_dir)
        }
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/create-file")
def create_file(request: CreateItemRequest) -> dict[str, Any]:
    """Create a new empty markdown file."""
    try:
        parent_path = Path(request.path).expanduser().resolve()

        # Ensure .md extension
        name = request.name
        if not name.lower().endswith(('.md', '.markdown', '.txt')):
            name = f"{name}.md"

        new_file = parent_path / name

        if new_file.exists():
            raise HTTPException(status_code=400, detail="File already exists")

        # Create empty file with a basic template
        new_file.write_text(f"# {new_file.stem}\n\n", encoding='utf-8')

        return {
            "success": True,
            "message": f"Created file: {name}",
            "path": str(new_file)
        }
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
