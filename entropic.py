#!/usr/bin/env python3
"""
Entropic — Video Glitch Engine
CLI entry point. Also importable as a library.

Usage:
    python entropic.py new myproject --source video.mp4
    python entropic.py apply myproject --effect pixelsort --threshold 0.6
    python entropic.py apply myproject --effect invert --region center --feather 10
    python entropic.py preview myproject 001
    python entropic.py render myproject 001 --quality hi
    python entropic.py history myproject
    python entropic.py list-effects
    python entropic.py ui
"""

import sys
import os
import re
import subprocess
import argparse

# Add project root to path so imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.project import create_project, project_status, list_projects, get_source_video
from core.recipe import (
    create_recipe, load_recipe, list_recipes,
    branch_recipe, favorite_recipe, recipe_tree,
)
from core.preview import render_recipe, preview_frame, render_sample_frames
from core.safety import preflight, SafetyError
from effects import list_effects, search_effects, list_categories, EFFECTS, CATEGORIES

__version__ = "0.2.0"

MAX_NAME_LEN = 100
MAX_SEARCH_LEN = 200


def _sanitize_name(name: str) -> str:
    """Sanitize user-provided names for safe filesystem use."""
    if not name:
        return name
    safe = re.sub(r'[^\w\s-]', '_', name)
    safe = safe.strip()[:MAX_NAME_LEN]
    if not safe or safe in ('.', '..'):
        print(f"Invalid name: {name}", file=sys.stderr)
        sys.exit(1)
    return safe


def _parse_param_value(val: str):
    """Safely parse a CLI parameter value (number, tuple, or string)."""
    # Tuple: "(10, 0)" → (10, 0)
    if val.startswith('(') and val.endswith(')'):
        parts = val.strip('()').split(',')
        if len(parts) > 10:
            raise ValueError(f"Tuple too long (max 10 elements): {val}")
        parsed = []
        for p in parts:
            p = p.strip()
            if not p:
                raise ValueError(f"Empty tuple element in: {val}")
            f = float(p)
            if f != f or f == float('inf') or f == float('-inf'):
                raise ValueError(f"NaN/Inf not allowed: {val}")
            parsed.append(f)
        return tuple(parsed)

    # Reject NaN/Inf as standalone strings
    if val.lower().strip() in ('nan', 'inf', '-inf', '+inf', 'infinity', '-infinity'):
        raise ValueError(f"NaN/Inf not allowed: {val}")

    # Float
    if '.' in val or 'e' in val.lower():
        f = float(val)
        if f != f or f == float('inf') or f == float('-inf'):
            raise ValueError(f"NaN/Inf not allowed: {val}")
        return f

    # Integer
    try:
        return int(val)
    except (ValueError, TypeError):
        return val  # Keep as string


def cmd_new(args):
    """Create a new project."""
    args.name = _sanitize_name(args.name)
    # Preflight: validate source video before creating project
    info = preflight(args.source)
    print(f"Source validated: {info['size_mb']:.1f}MB {info['extension']}")
    path = create_project(args.name, args.source)
    print(f"Created project: {args.name}")
    print(f"  Location: {path}")
    print(f"  Source: {args.source}")


def cmd_apply(args):
    """Apply an effect and create a recipe."""
    # Validate effect name before proceeding
    if args.effect not in EFFECTS:
        matches = [n for n in EFFECTS if args.effect in n]
        if matches:
            print(f"Unknown effect: {args.effect}. Did you mean: {', '.join(matches)}?")
        else:
            print(f"Unknown effect: {args.effect}. Use 'entropic list-effects' to see all.")
        return

    # Show param hints when no --params given
    if not args.params:
        entry = EFFECTS[args.effect]
        params_str = ", ".join(f"{k}={v}" for k, v in entry["params"].items())
        print(f"Using defaults: {params_str}")

    # Build params from extra args
    params = {}
    if args.params:
        for p in args.params:
            key, val = p.split("=", 1)
            try:
                val = _parse_param_value(val)
            except ValueError as e:
                print(f"Invalid param {key}: {e}", file=sys.stderr)
                return
            params[key] = val

    # Region support
    if args.region:
        params["region"] = args.region
    if args.feather:
        if not args.region:
            print("Note: --feather has no effect without --region. "
                  "Feather controls edge blending for region selections.", file=sys.stderr)
        params["feather"] = args.feather

    if args.name:
        args.name = _sanitize_name(args.name)
    effects = [{"name": args.effect, "params": params}]
    recipe = create_recipe(args.project, effects, name=args.name)
    print(f"Created recipe {recipe['id']}: {recipe['name']}")

    # Region feedback
    if args.region:
        from core.region import parse_region, REGION_PRESETS
        try:
            source = get_source_video(args.project)
            # Get frame dimensions from source
            import cv2
            cap = cv2.VideoCapture(str(source))
            frame_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            frame_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cap.release()
            rx, ry, rw, rh = parse_region(args.region, frame_h, frame_w)
            pct = (rw * rh) / (frame_w * frame_h) * 100
            label = f"preset '{args.region}'" if args.region in REGION_PRESETS else f"'{args.region}'"
            print(f"  Region: {label} ({rx},{ry} to {rx+rw},{ry+rh} — {rw}x{rh}px, {pct:.0f}% of frame)")
            if args.feather:
                print(f"  Feather: {args.feather}px (smooth edge blend)")
        except Exception:
            pass  # Don't fail if we can't resolve — the effect will still work

    # Auto-render lo-res preview
    print("Rendering lo-res preview...")
    output = render_recipe(args.project, recipe["id"], quality="lo")
    print(f"Preview: {output}")

    # Open preview
    if sys.platform == "darwin":
        subprocess.run(["open", str(output)])


def cmd_preview(args):
    """Preview a single frame from a recipe."""
    path = preview_frame(args.project, args.recipe_id, frame_number=args.frame)
    print(f"Preview: {path}")
    if sys.platform == "darwin":
        subprocess.run(["open", str(path)])


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
    if args.name:
        args.name = _sanitize_name(args.name)
    overrides = {}
    if args.params:
        for p in args.params:
            key, val = p.split("=", 1)
            try:
                val = _parse_param_value(val)
            except ValueError as e:
                print(f"Invalid param {key}: {e}", file=sys.stderr)
                return
            overrides["0"] = overrides.get("0", {})
            overrides["0"][key] = val

    recipe = branch_recipe(args.project, args.recipe_id, param_overrides=overrides, new_name=args.name)
    print(f"Branched: {recipe['id']} from {args.recipe_id}")


def cmd_list_presets(args):
    """List all available region presets."""
    from core.region import list_presets, REGION_PRESETS
    presets = list_presets()
    print(f"\n  Region Presets ({len(presets)} available)")
    print(f"  {'—' * 50}")
    for name in sorted(presets):
        x, y, w, h = REGION_PRESETS[name]
        print(f"    {name:20s}  x={x}, y={y}, w={w}, h={h}")
    print(f"\n  Usage: --region <preset_name>")
    print(f"  Custom: --region 'x,y,w,h' (pixels or 0-1 percent)")
    print(f"  Feather: --feather <px> (smooth edge blend)\n")


def cmd_list_effects(args):
    """List all available effects, grouped by category."""
    category_filter = getattr(args, "category", None)
    compact = getattr(args, "compact", False)

    if category_filter:
        effects = list_effects(category=category_filter)
        if not effects:
            valid = ", ".join(list_categories())
            print(f"Unknown category: {category_filter}. Available: {valid}")
            return
        print(f"\n  {CATEGORIES.get(category_filter, category_filter.upper())} ({len(effects)} effects)")
        print(f"  {'—' * 50}")
        for e in effects:
            print(f"    {e['name']:15s} — {e['description']}")
            if not compact:
                params_str = ", ".join(f"{k}={v}" for k, v in e["params"].items())
                print(f"    {'':15s}   Params: {params_str}")
        print()
        return

    # Group by category
    total = 0
    for cat_key, cat_label in CATEGORIES.items():
        effects = list_effects(category=cat_key)
        if not effects:
            continue
        total += len(effects)
        print(f"\n  {cat_label} ({len(effects)})")
        print(f"  {'—' * 50}")
        for e in effects:
            print(f"    {e['name']:15s} — {e['description']}")
            if not compact:
                params_str = ", ".join(f"{k}={v}" for k, v in e["params"].items())
                print(f"    {'':15s}   Params: {params_str}")

    print(f"\n  Total: {total} effects across {len(CATEGORIES)} categories")
    print(f"  Use --category <name> to filter. Use --compact for names only.")
    print(f"  Use 'entropic info <effect>' for details.\n")


def cmd_info(args):
    """Show detailed info about a single effect."""
    name = args.effect_name
    if name not in EFFECTS:
        # Fuzzy match attempt
        matches = [n for n in EFFECTS if name in n]
        if matches:
            print(f"Unknown effect: {name}. Did you mean: {', '.join(matches)}?")
        else:
            print(f"Unknown effect: {name}. Use 'entropic list-effects' to see all.")
        return

    entry = EFFECTS[name]
    cat = entry.get("category", "other")
    print(f"\n  {name}")
    print(f"  {'—' * 40}")
    print(f"  Category:    {CATEGORIES.get(cat, cat).upper()}")
    print(f"  Description: {entry['description']}")
    print(f"\n  Parameters:")
    for k, v in entry["params"].items():
        print(f"    {k:20s} = {v}")
    print(f"\n  All effects support 'mix' param (0.0-1.0) for dry/wet blend.")
    print(f"  All effects support --region and --feather for spatial targeting.")
    print(f"  Use 'entropic list-presets' to see region presets.")
    print(f"\n  Example:")
    params_example = " ".join(f"--params {k}={v}" for k, v in list(entry["params"].items())[:2])
    print(f"    entropic apply myproject --effect {name} {params_example}")
    print(f"    entropic apply myproject --effect {name} --region center --feather 10")
    print()


def cmd_search(args):
    """Search effects by name or description."""
    results = search_effects(args.query)
    if not results:
        print(f"No effects matching '{args.query}'.")
        return
    print(f"\n  Results for '{args.query}' ({len(results)} found):")
    print(f"  {'—' * 50}")
    for e in results:
        cat = CATEGORIES.get(e["category"], e["category"]).upper()
        print(f"    {e['name']:15s} [{cat:10s}] — {e['description']}")
    print()


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


def cmd_datamosh_ui(args):
    """Launch the Real Datamosh native desktop app."""
    from datamosh_gui import main as launch_datamosh
    launch_datamosh()


def main():
    parser = argparse.ArgumentParser(
        prog="entropic",
        description="Entropic — Video Glitch Engine by PopChaos Labs",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command")

    # new
    p = sub.add_parser("new", help="Create a new project")
    p.add_argument("name", help="Project name")
    p.add_argument("--source", required=True, help="Path to source video")

    # apply
    p = sub.add_parser("apply", help="Apply an effect (supports --region for spatial targeting)")
    p.add_argument("project", help="Project name")
    p.add_argument("--effect", required=True, help="Effect name")
    p.add_argument("--name", help="Recipe name (auto-generated if omitted)")
    p.add_argument("--params", nargs="*", help="Effect params as key=value pairs")
    p.add_argument("--region", help="Apply effect to region only: 'x,y,w,h' (pixels or 0-1 percent) or preset name (center, top-half, etc.)")
    p.add_argument("--feather", type=int, default=0, help="Region edge feather radius in pixels (0 = hard edge)")

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
    p = sub.add_parser("list-effects", help="List all available effects")
    p.add_argument("--category", choices=list_categories(), help="Filter by category")
    p.add_argument("--compact", action="store_true", help="Compact view (names only)")

    # info
    p = sub.add_parser("info", help="Show detailed info about an effect")
    p.add_argument("effect_name", help="Effect name")

    # search
    p = sub.add_parser("search", help="Search effects by name or description")
    p.add_argument("query", help="Search term")

    # list-presets
    sub.add_parser("list-presets", help="List all region presets")

    # projects
    sub.add_parser("projects", help="List all projects")

    # ui
    sub.add_parser("ui", help="Launch Gradio visual interface")

    # datamosh-ui
    sub.add_parser("datamosh", help="Launch Real Datamosh native desktop app")

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
        "list-presets": cmd_list_presets,
        "info": cmd_info,
        "search": cmd_search,
        "projects": cmd_list_projects,
        "ui": cmd_ui,
        "datamosh": cmd_datamosh_ui,
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
