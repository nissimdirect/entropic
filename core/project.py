"""
Entropic — Project Management
Handles project creation, status, and directory structure.
"""

import json
import shutil
from pathlib import Path
from datetime import datetime

DEFAULT_PROJECTS_DIR = Path.home() / ".entropic" / "projects"
DEFAULT_DISK_BUDGET = 2 * 1024 * 1024 * 1024  # 2GB


def get_project_dir(name: str, base: Path | None = None) -> Path:
    """Get the path for a project."""
    base = base or DEFAULT_PROJECTS_DIR
    return base / name


def create_project(name: str, source_video: str, base: Path | None = None) -> Path:
    """Create a new Entropic project.

    Args:
        name: Project name (used as directory name).
        source_video: Path to source video file.
        base: Base directory for projects (default ~/.entropic/projects/).

    Returns:
        Path to project directory.
    """
    source = Path(source_video).resolve()
    if not source.exists():
        raise FileNotFoundError(f"Source video not found: {source}")

    project_dir = get_project_dir(name, base)
    if project_dir.exists():
        raise FileExistsError(f"Project already exists: {project_dir}")

    # Create directory structure
    (project_dir / "source").mkdir(parents=True)
    (project_dir / "recipes").mkdir()
    (project_dir / "recipes" / "favorites").mkdir()
    (project_dir / "renders" / "lo").mkdir(parents=True)
    (project_dir / "renders" / "mid").mkdir(parents=True)
    (project_dir / "renders" / "hi").mkdir(parents=True)

    # Symlink source video
    link = project_dir / "source" / source.name
    link.symlink_to(source)

    # Write project metadata
    metadata = {
        "name": name,
        "created": datetime.now().isoformat(),
        "source": str(source),
        "source_name": source.name,
        "disk_budget": DEFAULT_DISK_BUDGET,
        "recipe_count": 0,
    }
    (project_dir / "project.json").write_text(json.dumps(metadata, indent=2))

    return project_dir


def load_project(name: str, base: Path | None = None) -> dict:
    """Load project metadata."""
    project_dir = get_project_dir(name, base)
    meta_path = project_dir / "project.json"
    if not meta_path.exists():
        raise FileNotFoundError(f"Project not found: {name}")
    return json.loads(meta_path.read_text())


def get_source_video(name: str, base: Path | None = None) -> Path:
    """Get the source video path for a project."""
    project_dir = get_project_dir(name, base)
    source_dir = project_dir / "source"
    videos = list(source_dir.iterdir())
    if not videos:
        raise FileNotFoundError(f"No source video in project {name}")
    return videos[0].resolve()


def project_status(name: str, base: Path | None = None) -> dict:
    """Get project status including disk usage."""
    project_dir = get_project_dir(name, base)
    meta = load_project(name, base)

    # Count recipes
    recipes = list((project_dir / "recipes").glob("*.json"))
    favorites = list((project_dir / "recipes" / "favorites").glob("*.json"))

    # Measure disk usage per tier
    def dir_size(path):
        return sum(f.stat().st_size for f in Path(path).rglob("*") if f.is_file())

    lo_size = dir_size(project_dir / "renders" / "lo")
    mid_size = dir_size(project_dir / "renders" / "mid")
    hi_size = dir_size(project_dir / "renders" / "hi")
    total_renders = lo_size + mid_size + hi_size
    budget = meta.get("disk_budget", DEFAULT_DISK_BUDGET)

    return {
        "name": name,
        "source": meta["source_name"],
        "recipes": len(recipes),
        "favorites": len(favorites),
        "renders": {
            "lo": lo_size,
            "mid": mid_size,
            "hi": hi_size,
            "total": total_renders,
        },
        "budget": budget,
        "budget_used_pct": (total_renders / budget * 100) if budget > 0 else 0,
    }


def list_projects(base: Path | None = None) -> list[str]:
    """List all project names."""
    base = base or DEFAULT_PROJECTS_DIR
    if not base.exists():
        return []
    return [d.name for d in base.iterdir() if d.is_dir() and (d / "project.json").exists()]


def _format_size(size_bytes: int) -> str:
    """Format bytes as human-readable string."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f}{unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f}TB"
