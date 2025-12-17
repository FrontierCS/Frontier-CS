"""Solution templates for code generation."""

from pathlib import Path

PREPARE_ENV_TEMPLATE = """#!/usr/bin/env bash
set -euo pipefail
echo "[{solution_name}] No additional environment preparation required."
"""

SOLVE_TEMPLATE = """#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR=$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)
TARGET_DIR="/work/Frontier-CS/execution_env/solution_env"
mkdir -p "$TARGET_DIR"
cp "$SCRIPT_DIR/resources/solution.py" "$TARGET_DIR/solution.py"
echo "[{solution_name}] solution.py staged"
"""

SOLUTION_TEMPLATE = "{generated_code}\n"


def create_solution(repo_root: Path, name: str, code: str) -> Path:
    """Create a solution directory with all necessary files."""
    sol_dir = repo_root / "solutions" / name
    res_dir = sol_dir / "resources"
    res_dir.mkdir(parents=True, exist_ok=True)

    # prepare_env.sh
    prep = sol_dir / "prepare_env.sh"
    prep.write_text(PREPARE_ENV_TEMPLATE.format(solution_name=name))
    prep.chmod(0o755)

    # solve.sh
    solve = sol_dir / "solve.sh"
    solve.write_text(SOLVE_TEMPLATE.format(solution_name=name))
    solve.chmod(0o755)

    # solution.py
    solution = res_dir / "solution.py"
    solution.write_text(SOLUTION_TEMPLATE.format(generated_code=code))

    return sol_dir
