#!/usr/bin/env python3
"""
Entropic Packages — Challenger Prototype
=========================================
Same engine, different interface. Instead of individual effects,
you pick PACKAGES (curated bundles) and RECIPES within them.

This makes UAT easier because:
  - "analog-decay / worn-tape is broken" → pinpoints exact config
  - Each recipe has KNOWN expected output
  - Test matrix: 7 packages × 4-5 recipes × N test videos

Usage:
    python entropic_packages.py list
    python entropic_packages.py explore analog-decay
    python entropic_packages.py apply myproject --package analog-decay --recipe worn-tape
    python entropic_packages.py batch myproject --package analog-decay
    python entropic_packages.py matrix myproject   (runs ALL packages × ALL recipes)

Same rendering engine as entropic.py — just a different way to select effects.
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from packages import list_packages, get_package, get_recipe, list_package_recipes, PACKAGES
from core.project import create_project, get_source_video, list_projects
from core.recipe import create_recipe
from core.preview import render_recipe
from core.safety import preflight

__version__ = "0.1.0"


def cmd_list(args):
    """List all available packages."""
    pkgs = list_packages()
    print(f"\n  ENTROPIC PACKAGES ({len(pkgs)} available)")
    print(f"  {'=' * 60}")
    for pkg in pkgs:
        print(f"\n  {pkg['key']}")
        print(f"    {pkg['name']} — {pkg['recipe_count']} recipes")
        print(f"    {pkg['description'][:80]}")
        print(f"    Effects: {', '.join(pkg['effects_used'][:5])}...")
    print(f"\n  Use 'explore <package>' to see recipes inside.\n")


def cmd_explore(args):
    """Show all recipes in a package."""
    pkg = get_package(args.package)
    if not pkg:
        available = ", ".join(PACKAGES.keys())
        print(f"Unknown package: {args.package}")
        print(f"Available: {available}")
        return

    recipes = list_package_recipes(args.package)
    print(f"\n  {pkg['name'].upper()}")
    print(f"  {pkg['description']}")
    print(f"  {'—' * 60}")
    print(f"  Effects available: {', '.join(pkg['effects_used'])}")
    print(f"\n  RECIPES ({len(recipes)}):")
    print(f"  {'—' * 60}")

    for r in recipes:
        effects_str = " → ".join(e["name"] for e in r["effects"])
        print(f"\n    {r['key']}")
        print(f"      {r['name']} — {r['description']}")
        print(f"      Chain: {effects_str}")
        for e in r["effects"]:
            params_str = ", ".join(f"{k}={v}" for k, v in e["params"].items())
            print(f"        {e['name']}: {params_str}")
    print()


def cmd_apply(args):
    """Apply a package recipe to a project."""
    pkg = get_package(args.package)
    if not pkg:
        available = ", ".join(PACKAGES.keys())
        print(f"Unknown package: {args.package}. Available: {available}")
        return

    recipe_data = get_recipe(args.package, args.recipe)
    if not recipe_data:
        available = ", ".join(pkg["recipes"].keys())
        print(f"Unknown recipe: {args.recipe}. Available in {args.package}: {available}")
        return

    # Create recipe with package--recipe naming (no / in filenames)
    recipe_name = f"{args.package}--{args.recipe}"
    recipe = create_recipe(args.project, recipe_data["effects"], name=recipe_name)
    print(f"Applied: {pkg['name']} / {recipe_data['name']}")
    print(f"  Recipe ID: {recipe['id']}")
    print(f"  Description: {recipe_data['description']}")
    effects_str = " → ".join(e["name"] for e in recipe_data["effects"])
    print(f"  Chain: {effects_str}")

    # Auto-render lo-res preview
    quality = getattr(args, "quality", "lo")
    print(f"\nRendering {quality} preview...")
    output = render_recipe(args.project, recipe["id"], quality=quality)
    print(f"Output: {output}")

    if sys.platform == "darwin":
        import subprocess
        subprocess.run(["open", str(output)])


def cmd_batch(args):
    """Render ALL recipes in a package for comparison."""
    pkg = get_package(args.package)
    if not pkg:
        available = ", ".join(PACKAGES.keys())
        print(f"Unknown package: {args.package}. Available: {available}")
        return

    recipes = list_package_recipes(args.package)
    quality = getattr(args, "quality", "lo")
    print(f"\n  BATCH: {pkg['name']} ({len(recipes)} recipes at {quality} quality)")
    print(f"  {'=' * 60}")

    results = []
    for r in recipes:
        recipe_name = f"{args.package}--{r['key']}"
        print(f"\n  Rendering: {r['name']}...")
        recipe = create_recipe(args.project, r["effects"], name=recipe_name)
        try:
            output = render_recipe(args.project, recipe["id"], quality=quality)
            size_mb = output.stat().st_size / (1024 * 1024)
            results.append({"name": r["name"], "id": recipe["id"], "output": str(output), "size_mb": size_mb, "status": "OK"})
            print(f"    ✓ {output} ({size_mb:.1f}MB)")
        except Exception as e:
            results.append({"name": r["name"], "id": recipe["id"], "output": None, "size_mb": 0, "status": f"FAIL: {e}"})
            print(f"    ✗ FAILED: {e}")

    print(f"\n  {'=' * 60}")
    print(f"  BATCH RESULTS: {args.package}")
    print(f"  {'—' * 60}")
    ok = sum(1 for r in results if r["status"] == "OK")
    fail = len(results) - ok
    for r in results:
        status = "✓" if r["status"] == "OK" else "✗"
        print(f"    {status} {r['name']:25s} [{r['id']}] {r['size_mb']:.1f}MB  {r['status']}")
    print(f"\n  Total: {ok} passed, {fail} failed out of {len(results)}")
    print()


def cmd_matrix(args):
    """Run ALL packages × ALL recipes. Full test matrix."""
    quality = getattr(args, "quality", "lo")
    total_recipes = sum(len(pkg["recipes"]) for pkg in PACKAGES.values())
    print(f"\n  FULL MATRIX: {len(PACKAGES)} packages × {total_recipes} total recipes")
    print(f"  Quality: {quality}")
    print(f"  {'=' * 60}")

    all_results = {}
    for pkg_key, pkg in PACKAGES.items():
        print(f"\n  --- {pkg['name']} ---")
        all_results[pkg_key] = []
        for recipe_key, recipe_data in pkg["recipes"].items():
            recipe_name = f"{pkg_key}--{recipe_key}"
            print(f"    Rendering: {recipe_name}...", end=" ", flush=True)
            recipe = create_recipe(args.project, recipe_data["effects"], name=recipe_name)
            try:
                output = render_recipe(args.project, recipe["id"], quality=quality)
                size_mb = output.stat().st_size / (1024 * 1024)
                all_results[pkg_key].append({"key": recipe_key, "status": "OK", "size_mb": size_mb})
                print(f"✓ ({size_mb:.1f}MB)")
            except Exception as e:
                all_results[pkg_key].append({"key": recipe_key, "status": f"FAIL", "size_mb": 0})
                print(f"✗ ({e})")

    # Summary table
    print(f"\n  {'=' * 60}")
    print(f"  MATRIX SUMMARY")
    print(f"  {'=' * 60}")
    print(f"  {'Package':25s} {'Pass':>6s} {'Fail':>6s} {'Total':>6s}")
    print(f"  {'—' * 50}")
    total_ok = 0
    total_fail = 0
    for pkg_key, results in all_results.items():
        ok = sum(1 for r in results if r["status"] == "OK")
        fail = len(results) - ok
        total_ok += ok
        total_fail += fail
        status = "✓" if fail == 0 else "✗"
        print(f"  {status} {pkg_key:23s} {ok:6d} {fail:6d} {len(results):6d}")
    print(f"  {'—' * 50}")
    print(f"  {'TOTAL':25s} {total_ok:6d} {total_fail:6d} {total_ok + total_fail:6d}")
    print()


def main():
    parser = argparse.ArgumentParser(
        prog="entropic-packages",
        description="Entropic Packages — Challenger Prototype (package-based workflow)",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command")

    # list
    sub.add_parser("list", help="List all available packages")

    # explore
    p = sub.add_parser("explore", help="Show all recipes in a package")
    p.add_argument("package", help="Package key (e.g. analog-decay)")

    # apply
    p = sub.add_parser("apply", help="Apply a package recipe to a project")
    p.add_argument("project", help="Project name")
    p.add_argument("--package", required=True, help="Package key")
    p.add_argument("--recipe", required=True, help="Recipe key within the package")
    p.add_argument("--quality", choices=["lo", "mid", "hi"], default="lo")

    # batch
    p = sub.add_parser("batch", help="Render ALL recipes in a package")
    p.add_argument("project", help="Project name")
    p.add_argument("--package", required=True, help="Package key")
    p.add_argument("--quality", choices=["lo", "mid", "hi"], default="lo")

    # matrix
    p = sub.add_parser("matrix", help="Run ALL packages × ALL recipes (full test)")
    p.add_argument("project", help="Project name")
    p.add_argument("--quality", choices=["lo", "mid", "hi"], default="lo")

    args = parser.parse_args()

    commands = {
        "list": cmd_list,
        "explore": cmd_explore,
        "apply": cmd_apply,
        "batch": cmd_batch,
        "matrix": cmd_matrix,
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
