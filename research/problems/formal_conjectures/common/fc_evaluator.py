"""
Shared evaluator for formal_conjectures problems.

A submission is a single `solution.lean` file that must declare a top-level

    theorem solution : <exact statement of the target conjecture> := <proof>

The evaluator:
  1. Lints the source for constructs that could subvert checking.
  2. Compiles it against the prebuilt formal-conjectures + Mathlib package
     baked into the Docker image at /opt/formal-conjectures.
  3. Runs the trusted CheckDriver.lean, which loads only compiled .oleans
     (never elaborating submission syntax) and verifies that:
       - `solution`'s type is definitionally equal to the conjecture's
         statement, and
       - `solution` depends only on the standard axioms
         (propext, Classical.choice, Quot.sound).

Score contract (parsed by the framework from the last stdout line):
  1.0  proof accepted
  0.0  rejected (compile error / sorry / wrong statement / forbidden axiom)
An exception with no score line signals an infrastructure error.
"""

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

FC_ROOT = Path(os.environ.get("FC_ROOT", "/opt/formal-conjectures"))

# Rejected outright. The trusted driver makes most of these unexploitable
# anyway (it never elaborates submission syntax); this is defense in depth,
# and none are needed for an honest proof.
FORBIDDEN_PATTERNS = [
    (r"\baxiom\b", "axiom declarations are not allowed"),
    (r"\bsorryAx\b", "direct use of sorryAx is not allowed"),
    (r"\bmacro\b|\bmacro_rules\b", "macro definitions are not allowed"),
    (r"\belab\b|\belab_rules\b", "elaborator definitions are not allowed"),
    (r"\bsyntax\b", "syntax definitions are not allowed"),
    (r"\bnotation\b", "notation definitions are not allowed"),
    (r"\binitialize\b", "initializers are not allowed"),
    (r"\brun_cmd\b|\brun_elab\b", "compile-time command execution is not allowed"),
    (r"\bimplemented_by\b|\bextern\b", "native overrides are not allowed"),
    (r"\bnative_decide\b|\bofReduceBool\b|\bofReduceNat\b",
     "native_decide and native reduction axioms are not allowed"),
    (r"\bunsafe\b", "unsafe definitions are not allowed"),
    (r"set_option\s+debug\.", "debug options are not allowed"),
]


def reject(reason: str, detail: str = "") -> None:
    """Print diagnostics to stderr and the 0.0 score to stdout, then exit."""
    print(f"[fc] rejected: {reason}", file=sys.stderr)
    if detail:
        print(detail[-4000:], file=sys.stderr)
    print("0.0")
    sys.exit(0)


def run(cmd: list, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--solution-path", required=True)
    parser.add_argument("--target", required=True, help="Path to target.json")
    args = parser.parse_args()

    target = json.loads(Path(args.target).read_text(encoding="utf-8"))
    module = target["module"]      # list of module name components
    theorem = target["theorem"]    # list of declaration name components

    # Infrastructure sanity: the image must match the ref the problem was
    # generated from, else statements could silently differ. Raise (no score
    # line) so the framework reports ERROR instead of a misleading 0.0.
    expected_ref = target.get("ref")
    actual_ref = os.environ.get("FC_REF", "")
    if not actual_ref:
        proc = run(["git", "describe", "--tags", "--always"], cwd=FC_ROOT)
        actual_ref = proc.stdout.strip()
    if expected_ref and actual_ref and expected_ref != actual_ref:
        raise RuntimeError(
            f"image formal-conjectures ref {actual_ref!r} does not match "
            f"problem ref {expected_ref!r}; rebuild the eval image"
        )

    solution_path = Path(args.solution_path)
    if not solution_path.exists():
        raise FileNotFoundError(f"solution not found: {solution_path}")
    src = solution_path.read_text(encoding="utf-8")

    for pattern, reason in FORBIDDEN_PATTERNS:
        if re.search(pattern, src):
            reject(reason)

    tmp = Path(tempfile.mkdtemp(prefix="fcsol_"))
    (tmp / "FCSolution.lean").write_text(src, encoding="utf-8")

    print("[fc] compiling solution...", file=sys.stderr)
    proc = run(
        ["lake", "env", "lean",
         "--root", str(tmp),
         "-o", str(tmp / "FCSolution.olean"),
         str(tmp / "FCSolution.lean")],
        cwd=FC_ROOT,
    )
    output = proc.stdout + "\n" + proc.stderr
    if proc.returncode != 0:
        reject("solution failed to compile", output)
    if "declaration uses 'sorry'" in output:
        reject("solution uses sorry", output)

    print("[fc] running trusted checker...", file=sys.stderr)
    driver = Path(__file__).resolve().parent / "CheckDriver.lean"
    driver_args = " ".join(shlex.quote(c) for c in [*module, "/", *theorem])
    proc = run(
        ["lake", "env", "bash", "-c",
         f'export LEAN_PATH="$LEAN_PATH:{tmp}"; '
         f"exec lean --root {shlex.quote(str(driver.parent))} "
         f"--run {shlex.quote(str(driver))} {driver_args}"],
        cwd=FC_ROOT,
    )
    if proc.returncode != 0 or "FC_CHECK_OK" not in proc.stdout:
        reject("proof check failed", proc.stdout + "\n" + proc.stderr)

    print("[fc] proof accepted", file=sys.stderr)
    print("1.0")


if __name__ == "__main__":
    main()
