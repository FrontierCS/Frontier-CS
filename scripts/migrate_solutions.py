#!/usr/bin/env python3
"""
Migrate solutions from old directory format to new flat file format.

Old format: solutions/{model}_{problem}[_{variant}]/resources/solution.py
New format: solutions/{problem}.{model}[_{variant}].py

Usage:
    python scripts/migrate_solutions.py --dryrun   # Preview changes
    python scripts/migrate_solutions.py            # Execute migration
    python scripts/migrate_solutions.py --delete   # Also delete old directories
"""

import argparse
import re
import shutil
from pathlib import Path

import yaml


def sanitize_problem_name(problem: str) -> str:
    """Convert problem path to flat name (e.g., 'cant_be_late/variant' -> 'cant_be_late_variant')."""
    return problem.replace("/", "_")


def parse_old_solution_dir(dir_path: Path) -> tuple[str, str, int] | None:
    """
    Parse old solution directory to extract (problem, model, variant).

    Returns None if not a valid old-format solution directory.
    """
    config_path = dir_path / "config.yaml"
    solution_path = dir_path / "resources" / "solution.py"

    if not config_path.exists() or not solution_path.exists():
        return None

    # Read problem from config.yaml
    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        problem = config.get("problem")
        if not problem:
            return None
    except Exception:
        return None

    # Sanitize problem name
    problem_flat = sanitize_problem_name(problem)

    # Parse directory name to extract model and variant
    # Format: {model}_{problem_flat} or {model}_{problem_flat}_{variant}
    dir_name = dir_path.name
    variant = 0
    model = None

    # Try to match with variant suffix first (only single digit variants 1-9)
    for v in range(1, 10):
        suffix_with_variant = f"_{problem_flat}_{v}"
        if dir_name.endswith(suffix_with_variant):
            model = dir_name[:-len(suffix_with_variant)]
            variant = v
            break

    # Try without variant suffix
    if model is None:
        suffix = f"_{problem_flat}"
        if dir_name.endswith(suffix):
            model = dir_name[:-len(suffix)]
            variant = 0

    # Fallback: couldn't parse
    if model is None:
        return None

    return (problem_flat, model, variant)


def new_filename(problem: str, model: str, variant: int) -> str:
    """Generate new flat filename."""
    if variant == 0:
        return f"{problem}.{model}.py"
    else:
        return f"{problem}.{model}_{variant}.py"


def main():
    parser = argparse.ArgumentParser(description="Migrate solutions to flat file format")
    parser.add_argument("--dryrun", action="store_true", help="Preview without making changes")
    parser.add_argument("--delete", action="store_true", help="Delete old directories after migration")
    parser.add_argument("--solutions-dir", type=Path, default=Path("solutions"),
                        help="Solutions directory (default: solutions)")
    args = parser.parse_args()

    solutions_dir = args.solutions_dir
    if not solutions_dir.is_dir():
        print(f"Error: {solutions_dir} is not a directory")
        return 1

    # Find all old-format solution directories
    migrations = []
    skipped = []

    for item in sorted(solutions_dir.iterdir()):
        if not item.is_dir():
            continue
        if item.name.startswith("."):
            continue

        parsed = parse_old_solution_dir(item)
        if parsed:
            problem, model, variant = parsed
            new_name = new_filename(problem, model, variant)
            new_path = solutions_dir / new_name
            old_solution = item / "resources" / "solution.py"

            migrations.append({
                "old_dir": item,
                "old_solution": old_solution,
                "new_path": new_path,
                "problem": problem,
                "model": model,
                "variant": variant,
            })
        else:
            # Check if it's already a flat file or unknown format
            if (item / "config.yaml").exists():
                skipped.append((item, "missing resources/solution.py"))
            # else: not an old-format directory, ignore

    # Report
    print(f"Found {len(migrations)} solutions to migrate")
    if skipped:
        print(f"Skipped {len(skipped)} directories (missing solution.py)")

    if not migrations:
        print("Nothing to migrate")
        return 0

    # Check for conflicts
    conflicts = []
    for m in migrations:
        if m["new_path"].exists():
            conflicts.append(m)

    if conflicts:
        print(f"\nWarning: {len(conflicts)} files already exist:")
        for c in conflicts[:10]:
            print(f"  {c['new_path'].name}")
        if len(conflicts) > 10:
            print(f"  ... and {len(conflicts) - 10} more")

    # Preview
    if args.dryrun:
        print("\nDryrun - would migrate:")
        for m in migrations[:20]:
            status = " (EXISTS)" if m["new_path"].exists() else ""
            print(f"  {m['old_dir'].name}/")
            print(f"    -> {m['new_path'].name}{status}")
        if len(migrations) > 20:
            print(f"  ... and {len(migrations) - 20} more")
        return 0

    # Execute migration
    print("\nMigrating...")
    migrated = 0
    errors = []

    for m in migrations:
        try:
            if m["new_path"].exists():
                # Skip existing files
                continue

            # Copy solution file
            shutil.copy2(m["old_solution"], m["new_path"])
            migrated += 1

            # Delete old directory if requested
            if args.delete:
                shutil.rmtree(m["old_dir"])
        except Exception as e:
            errors.append((m["old_dir"], str(e)))

    print(f"\nMigrated: {migrated}")
    if conflicts:
        print(f"Skipped (already exists): {len(conflicts)}")
    if errors:
        print(f"Errors: {len(errors)}")
        for old_dir, err in errors[:5]:
            print(f"  {old_dir}: {err}")

    if args.delete:
        print(f"Deleted {migrated} old directories")
    else:
        print("\nRun with --delete to remove old directories")

    return 0


if __name__ == "__main__":
    exit(main())
