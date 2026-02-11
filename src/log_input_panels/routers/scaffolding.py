import json
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/scaffolding", tags=["scaffolding"])

# Templates are stored in a JSON file in the data directory
TEMPLATES_DIR = Path(__file__).parent.parent.parent.parent / "data" / "scaffolding"
TEMPLATES_FILE = TEMPLATES_DIR / "templates.json"

# Default templates bundled with the application
DEFAULT_TEMPLATES = [
    {
        "name": "Python Package",
        "description": "Standard Python package structure with tests and docs",
        "creator": "System",
        "version": "1.0.0",
        "isCustom": False,
        "metadata": {"author": "", "projectName": "", "description": ""},
        "tree": [
            {
                "id": "1",
                "name": "src",
                "type": "directory",
                "description": "Source code directory",
                "content": "",
                "children": [
                    {
                        "id": "2",
                        "name": "__init__.py",
                        "type": "file",
                        "description": "Package initialization",
                        "content": '"""Package docstring."""\n\n__version__ = "0.1.0"\n',
                        "children": [],
                        "expanded": False,
                    },
                    {
                        "id": "3",
                        "name": "main.py",
                        "type": "file",
                        "description": "Main entry point",
                        "content": '"""Main module."""\n\n\ndef main() -> None:\n    """Entry point."""\n    pass\n\n\nif __name__ == "__main__":\n    main()\n',
                        "children": [],
                        "expanded": False,
                    },
                ],
                "expanded": True,
            },
            {
                "id": "4",
                "name": "tests",
                "type": "directory",
                "description": "Test suite",
                "content": "",
                "children": [
                    {
                        "id": "5",
                        "name": "__init__.py",
                        "type": "file",
                        "description": "",
                        "content": "",
                        "children": [],
                        "expanded": False,
                    },
                    {
                        "id": "6",
                        "name": "test_main.py",
                        "type": "file",
                        "description": "Tests for main module",
                        "content": '"""Tests for main module."""\n\n\ndef test_placeholder() -> None:\n    """Placeholder test."""\n    assert True\n',
                        "children": [],
                        "expanded": False,
                    },
                ],
                "expanded": True,
            },
            {
                "id": "7",
                "name": "pyproject.toml",
                "type": "file",
                "description": "Project configuration",
                "content": '[project]\nname = "myproject"\nversion = "0.1.0"\ndescription = ""\nreadme = "README.md"\nrequires-python = ">=3.10"\n\n[build-system]\nrequires = ["hatchling"]\nbuild-backend = "hatchling.build"\n',
                "children": [],
                "expanded": False,
            },
            {
                "id": "8",
                "name": ".gitignore",
                "type": "file",
                "description": "Git ignore patterns",
                "content": "__pycache__/\n*.py[cod]\n*$py.class\n.env\n.venv/\nvenv/\ndist/\nbuild/\n*.egg-info/\n.pytest_cache/\n.mypy_cache/\n",
                "children": [],
                "expanded": False,
            },
        ],
    },
    {
        "name": "SvelteKit Project",
        "description": "SvelteKit project with TypeScript and basic structure",
        "creator": "System",
        "version": "1.0.0",
        "isCustom": False,
        "metadata": {"author": "", "projectName": "", "description": ""},
        "tree": [
            {
                "id": "1",
                "name": "src",
                "type": "directory",
                "description": "Source code",
                "content": "",
                "children": [
                    {
                        "id": "2",
                        "name": "routes",
                        "type": "directory",
                        "description": "Page routes",
                        "content": "",
                        "children": [
                            {
                                "id": "3",
                                "name": "+page.svelte",
                                "type": "file",
                                "description": "Home page",
                                "content": "<script lang=\"ts\">\n\tlet count = $state(0);\n</script>\n\n<main>\n\t<h1>Welcome</h1>\n\t<button onclick={() => count++}>\n\t\tCount: {count}\n\t</button>\n</main>\n",
                                "children": [],
                                "expanded": False,
                            },
                            {
                                "id": "4",
                                "name": "+layout.svelte",
                                "type": "file",
                                "description": "Root layout",
                                "content": "<script lang=\"ts\">\n\tlet { children } = $props();\n</script>\n\n<div class=\"app\">\n\t{@render children()}\n</div>\n\n<style>\n\t.app {\n\t\tmin-height: 100vh;\n\t}\n</style>\n",
                                "children": [],
                                "expanded": False,
                            },
                        ],
                        "expanded": True,
                    },
                    {
                        "id": "5",
                        "name": "lib",
                        "type": "directory",
                        "description": "Shared library code",
                        "content": "",
                        "children": [
                            {
                                "id": "6",
                                "name": "components",
                                "type": "directory",
                                "description": "Reusable components",
                                "content": "",
                                "children": [],
                                "expanded": True,
                            },
                        ],
                        "expanded": True,
                    },
                    {
                        "id": "7",
                        "name": "app.html",
                        "type": "file",
                        "description": "HTML template",
                        "content": '<!doctype html>\n<html lang="en">\n\t<head>\n\t\t<meta charset="utf-8" />\n\t\t<meta name="viewport" content="width=device-width, initial-scale=1" />\n\t\t%sveltekit.head%\n\t</head>\n\t<body data-sveltekit-preload-data="hover">\n\t\t<div style="display: contents">%sveltekit.body%</div>\n\t</body>\n</html>\n',
                        "children": [],
                        "expanded": False,
                    },
                ],
                "expanded": True,
            },
            {
                "id": "8",
                "name": "static",
                "type": "directory",
                "description": "Static assets",
                "content": "",
                "children": [],
                "expanded": True,
            },
            {
                "id": "9",
                "name": "svelte.config.js",
                "type": "file",
                "description": "Svelte configuration",
                "content": "import adapter from '@sveltejs/adapter-auto';\nimport { vitePreprocess } from '@sveltejs/vite-plugin-svelte';\n\nexport default {\n\tpreprocess: vitePreprocess(),\n\tkit: {\n\t\tadapter: adapter()\n\t}\n};\n",
                "children": [],
                "expanded": False,
            },
            {
                "id": "10",
                "name": ".gitignore",
                "type": "file",
                "description": "Git ignore patterns",
                "content": "node_modules/\n.svelte-kit/\nbuild/\n.env\n.env.*\n!.env.example\n",
                "children": [],
                "expanded": False,
            },
        ],
    },
    {
        "name": "FastAPI Project",
        "description": "FastAPI backend with SQLAlchemy and standard structure",
        "creator": "System",
        "version": "1.0.0",
        "isCustom": False,
        "metadata": {"author": "", "projectName": "", "description": ""},
        "tree": [
            {
                "id": "1",
                "name": "src",
                "type": "directory",
                "description": "Source code",
                "content": "",
                "children": [
                    {
                        "id": "2",
                        "name": "app",
                        "type": "directory",
                        "description": "Application package",
                        "content": "",
                        "children": [
                            {
                                "id": "3",
                                "name": "__init__.py",
                                "type": "file",
                                "description": "",
                                "content": "",
                                "children": [],
                                "expanded": False,
                            },
                            {
                                "id": "4",
                                "name": "main.py",
                                "type": "file",
                                "description": "FastAPI app entry point",
                                "content": 'from fastapi import FastAPI\n\napp = FastAPI(title="My API")\n\n\n@app.get("/health")\ndef health_check():\n    return {"status": "ok"}\n',
                                "children": [],
                                "expanded": False,
                            },
                            {
                                "id": "5",
                                "name": "routers",
                                "type": "directory",
                                "description": "API routers",
                                "content": "",
                                "children": [
                                    {
                                        "id": "6",
                                        "name": "__init__.py",
                                        "type": "file",
                                        "description": "",
                                        "content": "",
                                        "children": [],
                                        "expanded": False,
                                    },
                                ],
                                "expanded": True,
                            },
                            {
                                "id": "7",
                                "name": "models",
                                "type": "directory",
                                "description": "SQLAlchemy models",
                                "content": "",
                                "children": [
                                    {
                                        "id": "8",
                                        "name": "__init__.py",
                                        "type": "file",
                                        "description": "",
                                        "content": "",
                                        "children": [],
                                        "expanded": False,
                                    },
                                ],
                                "expanded": True,
                            },
                        ],
                        "expanded": True,
                    },
                ],
                "expanded": True,
            },
            {
                "id": "9",
                "name": "tests",
                "type": "directory",
                "description": "Test suite",
                "content": "",
                "children": [
                    {
                        "id": "10",
                        "name": "__init__.py",
                        "type": "file",
                        "description": "",
                        "content": "",
                        "children": [],
                        "expanded": False,
                    },
                ],
                "expanded": True,
            },
            {
                "id": "11",
                "name": "pyproject.toml",
                "type": "file",
                "description": "Project configuration",
                "content": '[project]\nname = "myproject"\nversion = "0.1.0"\nrequires-python = ">=3.10"\ndependencies = [\n    "fastapi>=0.100.0",\n    "uvicorn[standard]",\n    "sqlalchemy>=2.0.0",\n]\n\n[project.optional-dependencies]\ndev = [\n    "pytest",\n    "httpx",\n]\n',
                "children": [],
                "expanded": False,
            },
        ],
    },
]


class TreeNode(BaseModel):
    id: str
    name: str
    type: str
    description: str
    content: str
    children: list["TreeNode"]
    expanded: bool


class CreateProjectRequest(BaseModel):
    outputPath: str
    projectName: str
    tree: list[TreeNode]
    readme: str


class TemplateMetadata(BaseModel):
    author: str = ""
    projectName: str = ""
    description: str = ""


class SaveTemplateRequest(BaseModel):
    name: str
    description: str
    creator: str
    version: str
    tree: list[TreeNode]
    metadata: TemplateMetadata


def ensure_templates_dir() -> None:
    """Ensure the templates directory exists."""
    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)


def load_custom_templates() -> list[dict[str, Any]]:
    """Load custom templates from the JSON file."""
    ensure_templates_dir()
    if not TEMPLATES_FILE.exists():
        return []
    try:
        with open(TEMPLATES_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def save_custom_templates(templates: list[dict[str, Any]]) -> None:
    """Save custom templates to the JSON file."""
    ensure_templates_dir()
    with open(TEMPLATES_FILE, "w") as f:
        json.dump(templates, f, indent=2)


def create_tree_structure(base_path: Path, nodes: list[dict[str, Any]]) -> None:
    """Recursively create directory tree structure."""
    for node in nodes:
        node_path = base_path / node["name"]
        if node["type"] == "directory":
            node_path.mkdir(parents=True, exist_ok=True)
            if node.get("children"):
                create_tree_structure(node_path, node["children"])
        else:
            # File
            node_path.parent.mkdir(parents=True, exist_ok=True)
            content = node.get("content", "")
            node_path.write_text(content)


@router.get("/templates")
def list_templates() -> list[dict[str, Any]]:
    """Get all available templates (default + custom)."""
    custom = load_custom_templates()
    return DEFAULT_TEMPLATES + custom


@router.post("/templates")
def save_template(data: SaveTemplateRequest) -> dict[str, Any]:
    """Save a new custom template."""
    custom = load_custom_templates()

    # Check for duplicate names
    existing_names = {t["name"] for t in custom} | {t["name"] for t in DEFAULT_TEMPLATES}
    if data.name in existing_names:
        raise HTTPException(status_code=400, detail="A template with this name already exists")

    new_template = {
        "name": data.name,
        "description": data.description,
        "creator": data.creator,
        "version": data.version,
        "tree": [node.model_dump() for node in data.tree],
        "metadata": data.metadata.model_dump(),
        "isCustom": True,
    }

    custom.append(new_template)
    save_custom_templates(custom)

    return {"success": True, "message": "Template saved successfully"}


@router.delete("/templates/{template_name}")
def delete_template(template_name: str) -> dict[str, Any]:
    """Delete a custom template."""
    # Check if it's a default template
    if any(t["name"] == template_name for t in DEFAULT_TEMPLATES):
        raise HTTPException(status_code=400, detail="Cannot delete default templates")

    custom = load_custom_templates()
    original_count = len(custom)
    custom = [t for t in custom if t["name"] != template_name]

    if len(custom) == original_count:
        raise HTTPException(status_code=404, detail="Template not found")

    save_custom_templates(custom)
    return {"success": True, "message": "Template deleted successfully"}


@router.post("/create")
def create_project(data: CreateProjectRequest) -> dict[str, Any]:
    """Create a project structure on the filesystem."""
    output_path = Path(data.outputPath).expanduser().resolve()

    # Validate output path
    if not output_path.parent.exists():
        raise HTTPException(
            status_code=400,
            detail=f"Parent directory does not exist: {output_path.parent}",
        )

    # Create project directory
    project_path = output_path / data.projectName
    if project_path.exists():
        raise HTTPException(
            status_code=400,
            detail=f"Directory already exists: {project_path}",
        )

    try:
        project_path.mkdir(parents=True)

        # Create the tree structure
        tree_data = [node.model_dump() for node in data.tree]
        create_tree_structure(project_path, tree_data)

        # Create README
        readme_path = project_path / "README.md"
        readme_path.write_text(data.readme)

        return {
            "success": True,
            "message": f"Project created successfully at {project_path}",
            "path": str(project_path),
        }
    except PermissionError:
        raise HTTPException(
            status_code=403,
            detail="Permission denied. Cannot create project at this location.",
        )
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Failed to create project: {e}")


@router.get("/list-directories")
def list_directories(path: str = "~") -> dict[str, Any]:
    """List directories at a given path for the web-based directory browser."""
    try:
        # Expand user home directory and resolve path
        target_path = Path(path).expanduser().resolve()

        if not target_path.exists():
            raise HTTPException(status_code=404, detail=f"Path does not exist: {path}")

        if not target_path.is_dir():
            raise HTTPException(status_code=400, detail=f"Path is not a directory: {path}")

        # List only directories, skip hidden and inaccessible ones
        directories = []
        try:
            for item in sorted(target_path.iterdir()):
                if item.is_dir() and not item.name.startswith('.'):
                    try:
                        # Check if we can access it
                        list(item.iterdir())
                        directories.append({
                            "name": item.name,
                            "path": str(item),
                        })
                    except PermissionError:
                        # Skip directories we can't access
                        pass
        except PermissionError:
            raise HTTPException(status_code=403, detail=f"Permission denied: {path}")

        # Get parent path (if not at root)
        parent_path = str(target_path.parent) if target_path.parent != target_path else None

        return {
            "current": str(target_path),
            "parent": parent_path,
            "directories": directories,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list directories: {e}")
