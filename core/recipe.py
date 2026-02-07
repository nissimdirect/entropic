"""
Entropic — Recipe System
Recipes are lightweight JSON files (<1KB) that store effect configurations.
They ARE the version history — never deleted.
"""

import json
from pathlib import Path
from datetime import datetime

from core.project import get_project_dir


def _next_recipe_id(project_dir: Path) -> str:
    """Get next sequential recipe ID (zero-padded 3 digits)."""
    recipes = list((project_dir / "recipes").glob("*.json"))
    # Filter out non-recipe files
    ids = []
    for r in recipes:
        try:
            ids.append(int(r.stem.split("-")[0]))
        except (ValueError, IndexError):
            continue
    next_id = max(ids, default=0) + 1
    return f"{next_id:03d}"


def create_recipe(
    project_name: str,
    effects: list[dict],
    name: str | None = None,
    parent: str | None = None,
    notes: str = "",
    audio_map: dict | None = None,
    base: Path | None = None,
) -> dict:
    """Create a new recipe in a project.

    Args:
        project_name: Project to add recipe to.
        effects: List of effect dicts [{"name": "pixelsort", "params": {...}}, ...]
        name: Optional human name (auto-generated from first effect if None).
        parent: Parent recipe ID (for branching).
        notes: Freeform notes.
        audio_map: Audio parameter mapping (for audio-reactive effects).

    Returns:
        The created recipe dict.
    """
    project_dir = get_project_dir(project_name, base)
    recipe_id = _next_recipe_id(project_dir)

    if name is None:
        first_effect = effects[0]["name"] if effects else "empty"
        name = f"{first_effect}"

    recipe = {
        "id": recipe_id,
        "name": name,
        "created": datetime.now().isoformat(),
        "effects": effects,
        "audio_map": audio_map,
        "parent": parent,
        "favorite": False,
        "notes": notes,
    }

    filename = f"{recipe_id}-{name}.json"
    recipe_path = project_dir / "recipes" / filename
    recipe_path.write_text(json.dumps(recipe, indent=2))

    return recipe


def load_recipe(project_name: str, recipe_id: str, base: Path | None = None) -> dict:
    """Load a recipe by ID."""
    project_dir = get_project_dir(project_name, base)
    # Find recipe file matching the ID prefix
    matches = list((project_dir / "recipes").glob(f"{recipe_id}-*.json"))
    if not matches:
        raise FileNotFoundError(f"Recipe {recipe_id} not found in project {project_name}")
    return json.loads(matches[0].read_text())


def list_recipes(project_name: str, base: Path | None = None) -> list[dict]:
    """List all recipes in a project, sorted by ID."""
    project_dir = get_project_dir(project_name, base)
    recipes = []
    for f in sorted((project_dir / "recipes").glob("*.json")):
        try:
            recipes.append(json.loads(f.read_text()))
        except json.JSONDecodeError:
            continue
    return recipes


def branch_recipe(
    project_name: str,
    recipe_id: str,
    param_overrides: dict | None = None,
    new_name: str | None = None,
    base: Path | None = None,
) -> dict:
    """Branch a recipe — copy it with modifications, linking to parent.

    Args:
        project_name: Project name.
        recipe_id: ID of recipe to branch from.
        param_overrides: Dict of {effect_index: {param: value}} to override.
        new_name: Optional name for the branch.

    Returns:
        New recipe dict.
    """
    parent = load_recipe(project_name, recipe_id, base)

    effects = json.loads(json.dumps(parent["effects"]))  # Deep copy

    if param_overrides:
        for idx_str, params in param_overrides.items():
            idx = int(idx_str)
            if 0 <= idx < len(effects):
                effects[idx]["params"].update(params)

    name = new_name or f"{parent['name']}-branch"

    return create_recipe(
        project_name=project_name,
        effects=effects,
        name=name,
        parent=recipe_id,
        notes=f"Branched from {recipe_id}",
        audio_map=parent.get("audio_map"),
        base=base,
    )


def favorite_recipe(project_name: str, recipe_id: str, base: Path | None = None):
    """Toggle favorite status on a recipe."""
    project_dir = get_project_dir(project_name, base)
    matches = list((project_dir / "recipes").glob(f"{recipe_id}-*.json"))
    if not matches:
        raise FileNotFoundError(f"Recipe {recipe_id} not found")

    path = matches[0]
    recipe = json.loads(path.read_text())
    recipe["favorite"] = not recipe.get("favorite", False)
    path.write_text(json.dumps(recipe, indent=2))

    # Copy to/remove from favorites dir
    fav_dir = project_dir / "recipes" / "favorites"
    fav_path = fav_dir / path.name
    if recipe["favorite"]:
        fav_path.write_text(json.dumps(recipe, indent=2))
    elif fav_path.exists():
        fav_path.unlink()

    return recipe


def recipe_tree(project_name: str, base: Path | None = None) -> dict:
    """Build a parent→children tree of all recipes."""
    recipes = list_recipes(project_name, base)
    tree = {}
    for r in recipes:
        rid = r["id"]
        parent = r.get("parent")
        if parent not in tree:
            tree[parent] = []
        tree[parent].append(rid)
    return tree
