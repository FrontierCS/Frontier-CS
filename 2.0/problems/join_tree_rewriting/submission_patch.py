"""Apply and validate a patch submission.

Copied next to `evaluator.py` in every patch task, because the evaluator is loaded
by path in four places — the judge image, the local docker shim, the task's own
`test_evaluator.py`, and the structural gate's smoke run — and a sibling is the
only location that resolves in all four.

The checks here are the union of what five hand-written evaluators each
implemented separately (vllm, rocksdb, duckdb, nanowm, generals_io_bot). They are
about the *shape* of the diff: size, binary content, where it is allowed to touch.

`allow_paths` is scope control, not a security boundary. It stops a submission
sprawling across a repository and makes review cheap; it does nothing about what a
patch does *inside* a file it is allowed to touch. Forbidden tokens, structural
markers, language restrictions and anything else task-specific stay in the
evaluator, after this returns.
"""

from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_MAX_PATCH_BYTES = 256 * 1024
DEFAULT_MAX_CHANGED_FILES = 50
# `git diff` emits these for content it cannot express as text. Applying one is
# how a submission smuggles a compiled artifact past a source-level review.
BINARY_MARKERS = ("GIT binary patch", "literal 0", "delta 0")
BINARY_FILES_RE = re.compile(r"^Binary files .* differ$", re.M)
CHANGED_FILE_RE = re.compile(r"^\+\+\+ b/(.+)$", re.M)


@dataclass
class PatchResult:
    ok: bool
    message: str = ""
    workdir: Path | None = None
    metrics: dict = field(default_factory=dict)


def changed_files(patch_text: str) -> list[str]:
    """Destination paths the diff writes to, in order of appearance."""
    seen: list[str] = []
    for match in CHANGED_FILE_RE.finditer(patch_text):
        name = match.group(1).strip()
        if name != "/dev/null" and name not in seen:
            seen.append(name)
    return seen


def _within(path: str, allowed: list[str]) -> bool:
    for prefix in allowed:
        prefix = prefix.strip().lstrip("./").rstrip("/")
        if not prefix:
            continue
        if path == prefix or path.startswith(prefix + "/"):
            return True
    return False


def validate_patch(patch_text: str, config: dict) -> tuple[bool, str, dict]:
    """Shape checks, before anything is written to disk. (ok, message, metrics)."""
    submission = (config.get("submission") or {}) if isinstance(config, dict) else {}
    max_bytes = int(submission.get("max_patch_bytes") or DEFAULT_MAX_PATCH_BYTES)
    max_files = int(submission.get("max_changed_files") or DEFAULT_MAX_CHANGED_FILES)
    allow_paths = [str(p) for p in (submission.get("allow_paths") or [])]

    raw = patch_text.encode("utf-8", "replace")
    files = changed_files(patch_text)
    metrics = {
        "patch_bytes": len(raw),
        "patch_sha256": hashlib.sha256(raw).hexdigest(),
        "changed_files": len(files),
        "valid_patch": 0,
    }

    if not patch_text.strip():
        if submission.get("allow_empty"):
            metrics["valid_patch"] = 1
            return True, "empty patch (allowed)", metrics
        return False, "submission is empty", metrics
    if len(raw) > max_bytes:
        return False, f"patch is {len(raw)} bytes, over the {max_bytes} limit", metrics
    if "\x00" in patch_text or any(m in patch_text for m in BINARY_MARKERS) \
            or BINARY_FILES_RE.search(patch_text):
        return False, "patch contains binary content; submit source changes only", metrics
    if not files:
        return False, "patch changes no files (no `+++ b/<path>` header found)", metrics
    if len(files) > max_files:
        return False, f"patch changes {len(files)} files, over the {max_files} limit", metrics
    for name in files:
        if name.startswith("/") or ".." in Path(name).parts:
            return False, f"patch writes outside the tree: {name}", metrics
    if allow_paths:
        outside = [f for f in files if not _within(f, allow_paths)]
        if outside:
            return False, (f"patch touches {', '.join(outside[:5])}, outside the editable "
                           f"surface ({', '.join(allow_paths)})"), metrics

    metrics["valid_patch"] = 1
    return True, "", metrics


def apply_submission_patch(patch_path: str | Path, task_dir: str | Path,
                           config: dict, *, pristine: str | Path | None = None) -> PatchResult:
    """Validate the diff and apply it to a fresh copy of the pristine tree.

    The caller owns `result.workdir` and should clean it up. A rejection is a
    *scored zero*, not an error: return `0.0, 0.0, result.message, result.metrics`
    from the evaluator, which is the convention every task already follows.
    """
    patch_path = Path(patch_path)
    task_dir = Path(task_dir)
    try:
        patch_text = patch_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return PatchResult(False, f"could not read the submission: {exc}")

    ok, message, metrics = validate_patch(patch_text, config)
    if not ok:
        return PatchResult(False, message, metrics=metrics)

    submission = (config.get("submission") or {}) if isinstance(config, dict) else {}
    root = Path(pristine) if pristine else task_dir / "harbor" / "app"
    repo_root = str(submission.get("repo_root") or "/app").strip("/")
    if repo_root and repo_root != "app":
        # `repo_root: /app/duckdb` means the tree lives one level down, the way the
        # hand-written patch tasks lay theirs out.
        root = root / Path(repo_root).relative_to("app") if repo_root.startswith("app/") \
            else root / repo_root
    if not root.is_dir():
        return PatchResult(False, f"no pristine tree at {root}", metrics=metrics)

    workdir = Path(tempfile.mkdtemp(prefix="submission-"))
    tree = workdir / "tree"
    shutil.copytree(root, tree, symlinks=True)
    staged = workdir / "submission.patch"
    staged.write_text(patch_text, encoding="utf-8")

    for args in (["apply", "--check", "--whitespace=nowarn", str(staged)],
                 ["apply", "--whitespace=nowarn", str(staged)]):
        proc = subprocess.run(["git", "-C", str(tree), *args],
                              capture_output=True, text=True, timeout=300)
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout).strip().splitlines()
            shutil.rmtree(workdir, ignore_errors=True)
            return PatchResult(
                False,
                f"patch does not apply: {detail[-1][:200] if detail else 'git apply failed'}",
                metrics=metrics)
    return PatchResult(True, "", workdir=tree, metrics=metrics)
