#!/usr/bin/env python3
"""
Entropic — Video Glitch Engine
CLI entry point. Also importable as a library.

Usage:
    python entropic.py new myproject --source video.mp4
    python entropic.py apply myproject --effect pixelsort --threshold 0.6
    python entropic.py preview myproject 001
    python entropic.py render myproject 001 --quality hi
    python entropic.py history myproject
    python entropic.py list-effects
    python entropic.py ui
"""

import sys
import os
import argparse

# Add project root to path so imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.project import create_project, project_status, list_projects, get_source_video
from core.recipe import (
    create_recipe, load_recipe, list_recipes,
    branch_recipe, favorite_recipe, recipe_tree,
)
from core.preview import render_recipe, preview_frame, render_sample_frames
from effects import list_effects, EFFECTS


def cmd_new(args):
    """Create a new project."""
    path = create_project(args.name, args.source)
    print(f"Created project: {args.name}")
    print(f"  Location: {path}")
    print(f"  Source: {args.source}")


def cmd_apply(args):
    """Apply an effect and create a recipe."""
    # Build params from extra args
    params = {}
    if args.params:
        for p in args.params:
            key, val = p.split("=", 1)
            # Try to parse as number or tuple
            try:
                val = eval(val)
            except Exception:
                pass
            params[key] = val

    effects = [{"name": args.effect, "params": params}]
    recipe = create_recipe(args.project, effects, name=args.name)
    print(f"Created recipe {recipe['id']}: {recipe['name']}")

    # Auto-render lo-res preview
    print("Rendering lo-res preview...")
    output = render_recipe(args.project, recipe["id"], quality="lo")
    print(f"Preview: {output}")

    # Open preview
    if sys.platform == "darwin":
        os.system(f'open "{output}"')


def cmd_preview(args):
    """Preview a single frame from a recipe."""
    path = preview_frame(args.project, args.recipe_id, frame_number=args.frame)
    print(f"Preview: {path}")
    if sys.platform == "darwin":
        os.system(f'open "{path}"')


def cmd_render(args):
    """Render a recipe at specified quality."""
    print(f"Rendering recipe {args.recipe_id} at {args.quality} quality...")
    output = render_recipe(args.project, args.recipe_id, quality=args.quality)
    print(f"Output: {output}")
    size_mb = output.stat().st_size / (1024 * 1024)
    print(f"Size: {size_mb:.1f}MB")


def cmd_history(args):
    """Show recipe history for a project."""
    recipes = list_recipes(args.project)
    if not recipes:
        print("No recipes yet. Use 'entropic apply' to create one.")
        return
    tree = recipe_tree(args.project)
    for r in recipes:
        fav = " *" if r.get("favorite") else ""
        parent = f" (from {r['parent']})" if r.get("parent") else ""
        effects_str = " → ".join(e["name"] for e in r["effects"])
        print(f"  {r['id']}{fav}: {r['name']} [{effects_str}]{parent}")


def cmd_status(args):
    """Show project status."""
    status = project_status(args.project)
    print(f"Project: {status['name']}")
    print(f"  Source: {status['source']}")
    print(f"  Recipes: {status['recipes']} ({status['favorites']} favorites)")
    total = status["renders"]["total"]
    budget = status["budget"]
    pct = status["budget_used_pct"]
    print(f"  Renders: {total / 1024 / 1024:.1f}MB / {budget / 1024 / 1024 / 1024:.1f}GB ({pct:.0f}%)")


def cmd_favorite(args):
    """Toggle favorite on a recipe."""
    recipe = favorite_recipe(args.project, args.recipe_id)
    state = "favorited" if recipe["favorite"] else "unfavorited"
    print(f"Recipe {args.recipe_id}: {state}")


def cmd_branch(args):
    """Branch a recipe with modifications."""
    overrides = {}
    if args.params:
        for p in args.params:
            key, val = p.split("=", 1)
            try:
                val = eval(val)
            except Exception:
                pass
            overrides["0"] = overrides.get("0", {})
            overrides["0"][key] = val

    recipe = branch_recipe(args.project, args.recipe_id, param_overrides=overrides, new_name=args.name)
    print(f"Branched: {recipe['id']} from {args.recipe_id}")


def cmd_list_effects(args):
    """List all available effects."""
    effects = list_effects()
    print("Available effects:")
    for e in effects:
        params_str = ", ".join(f"{k}={v}" for k, v in e["params"].items())
        print(f"  {e['name']:15s} — {e['description']}")
        print(f"  {'':15s}   Params: {params_str}")


def cmd_list_projects(args):
    """List all projects."""
    projects = list_projects()
    if not projects:
        print("No projects. Use 'entropic new <name> --source video.mp4' to create one.")
        return
    for p in projects:
        print(f"  {p}")


def cmd_ui(args):
    """Launch the DAW-style visual interface."""
    from server import start
    start()


def main():
    parser = argparse.ArgumentParser(
        prog="entropic",
        description="Entropic — Video Glitch Engine by PopChaos Labs",
    )
    sub = parser.add_subparsers(dest="command")

    # new
    p = sub.add_parser("new", help="Create a new project")
    p.add_argument("name", help="Project name")
    p.add_argument("--source", required=True, help="Path to source video")

    # apply
    p = sub.add_parser("apply", help="Apply an effect (creates recipe + lo-res preview)")
    p.add_argument("project", help="Project name")
    p.add_argument("--effect", required=True, help="Effect name")
    p.add_argument("--name", help="Recipe name (auto-generated if omitted)")
    p.add_argument("--params", nargs="*", help="Effect params as key=value pairs")

    # preview
    p = sub.add_parser("preview", help="Preview a single frame")
    p.add_argument("project", help="Project name")
    p.add_argument("recipe_id", help="Recipe ID")
    p.add_argument("--frame", type=int, default=0, help="Frame number")

    # render
    p = sub.add_parser("render", help="Render a recipe at specified quality")
    p.add_argument("project", help="Project name")
    p.add_argument("recipe_id", help="Recipe ID")
    p.add_argument("--quality", choices=["lo", "mid", "hi"], default="mid")

    # history
    p = sub.add_parser("history", help="Show recipe history")
    p.add_argument("project", help="Project name")

    # status
    p = sub.add_parser("status", help="Show project status")
    p.add_argument("project", help="Project name")

    # favorite
    p = sub.add_parser("favorite", help="Toggle favorite on a recipe")
    p.add_argument("project", help="Project name")
    p.add_argument("recipe_id", help="Recipe ID")

    # branch
    p = sub.add_parser("branch", help="Branch a recipe with modifications")
    p.add_argument("project", help="Project name")
    p.add_argument("recipe_id", help="Recipe ID to branch from")
    p.add_argument("--name", help="Name for the branch")
    p.add_argument("--params", nargs="*", help="Param overrides as key=value pairs")

    # list-effects
    sub.add_parser("list-effects", help="List all available effects")

    # projects
    sub.add_parser("projects", help="List all projects")

    # ui
    sub.add_parser("ui", help="Launch Gradio visual interface")

    args = parser.parse_args()

    commands = {
        "new": cmd_new,
        "apply": cmd_apply,
        "preview": cmd_preview,
        "render": cmd_render,
        "history": cmd_history,
        "status": cmd_status,
        "favorite": cmd_favorite,
        "branch": cmd_branch,
        "list-effects": cmd_list_effects,
        "projects": cmd_list_projects,
        "ui": cmd_ui,
    }

    if args.command in commands:
        try:
            commands[args.command](args)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
