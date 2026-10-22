"""
Lazy materialization of generated problem directories.

formal_conjectures problem dirs are generated from the
third_party/formal-conjectures submodule and are not committed (see
research/problems/formal_conjectures/.gitignore). This module regenerates them
transparently on first access: resolving a formal_conjectures problem id
(eval, show) or listing research problems triggers generation when the
directories are missing or were generated from a different submodule commit.
Afterwards everything is served directly from the files.
"""

import hashlib
import subprocess
import sys
from pathlib import Path
from typing import Optional

FC = "formal_conjectures"

# problems_dirs verified current in this process; skip repeat git/stamp checks
_verified = set()


def _submodule_head(repo_root: Path) -> Optional[str]:
    proc = subprocess.run(
        ["git", "-C", str(repo_root / "third_party" / "formal-conjectures"),
         "rev-parse", "HEAD"],
        capture_output=True, text=True,
    )
    return proc.stdout.strip() if proc.returncode == 0 else None


def ensure_formal_conjectures(problems_dir: Path, problem_id: Optional[str] = None) -> None:
    """Generate formal_conjectures problem dirs if missing or stale.

    No-op when: this problems tree has no formal_conjectures generator, the
    requested problem id is not a formal_conjectures one, or generation is
    already up to date with the submodule commit and generator version
    (stamped as "<submodule-head>+<generator-hash>" in
    _generator/.generated-ref by the generator; must stay in sync with
    generation_stamp() there). Failures are reported on stderr but never
    raised — the caller then fails naturally with problem-not-found.
    """
    if problems_dir in _verified:
        return
    if problem_id is not None and not str(problem_id).startswith(FC + "/"):
        return
    fc_root = problems_dir / FC
    generator = fc_root / "_generator" / "generate.py"
    if not generator.is_file():
        return

    repo_root = problems_dir.parents[1]
    submodule = repo_root / "third_party" / "formal-conjectures"
    if not (submodule / "FormalConjectures").is_dir():
        subprocess.run(
            ["git", "submodule", "update", "--init", "third_party/formal-conjectures"],
            cwd=repo_root, capture_output=True,
        )
        if not (submodule / "FormalConjectures").is_dir():
            print(f"[{FC}] submodule not initialized and auto-init failed; "
                  "run: git submodule update --init", file=sys.stderr)
            return

    head = _submodule_head(repo_root)
    ghash = hashlib.sha256(generator.read_bytes()).hexdigest()[:16]
    stamp_file = fc_root / "_generator" / ".generated-ref"
    stamp = stamp_file.read_text(encoding="utf-8").strip() if stamp_file.is_file() else None
    if head is not None and stamp == f"{head}+{ghash}":
        _verified.add(problems_dir)
        return  # up to date; a missing problem id is genuinely unknown

    print(f"[{FC}] materializing problem directories from the submodule...",
          file=sys.stderr)
    proc = subprocess.run(
        [sys.executable, str(generator), "--wipe"],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        print(f"[{FC}] generation failed:\n{proc.stderr}", file=sys.stderr)
        return
    summary = proc.stdout.splitlines()[0] if proc.stdout else ""
    print(f"[{FC}] {summary}", file=sys.stderr)
    _verified.add(problems_dir)
