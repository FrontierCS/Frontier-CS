"""End-to-end Stats-CEB evaluator for join-tree rewriting."""

from __future__ import annotations

import ast
import csv
import hashlib
import json
import math
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

TASK_DIR = Path(__file__).resolve().parent
if str(TASK_DIR) not in sys.path:
    sys.path.insert(0, str(TASK_DIR))
from submission_patch import apply_submission_patch


JUDGE_DIR = TASK_DIR / "judge"
EDITABLE = "2phase_nsa/binary_plan/rewrite_policy.py"
CONFIG = {
    "submission": {
        "kind": "patch",
        "path": "/app/solution.patch",
        "repo_root": "/app",
        "allow_paths": [EDITABLE],
        "allow_empty": True,
        "max_changed_files": 1,
        "max_patch_bytes": 65536,
    }
}
REPETITIONS = 5
ENGINE_TIMEOUT_SECONDS = 120
PLAN_TIMEOUT_SECONDS = 30
FORBIDDEN_CALLS = {
    "open", "exec", "eval", "compile", "input", "breakpoint", "__import__",
    "globals", "locals", "vars", "getattr", "setattr", "delattr",
}
FORBIDDEN_TEXT = ("/proc", "/sys", "frontier_submission", "plan_builder", "evaluator.py")
ALLOWED_IMPORT_ROOTS = {"typing", "binary_plan"}


def _suite_name() -> str:
    return "final" if os.environ.get("FRONTIER_SUBMISSION_ROLE") == "final" else "dev"


def _source_policy(tree: Path) -> tuple[bool, str]:
    try:
        source = (tree / EDITABLE).read_text(encoding="utf-8")
        parsed = ast.parse(source)
    except (OSError, SyntaxError, UnicodeError):
        return False, "the editable module is not valid Python source"
    lowered = source.lower()
    if any(fragment in lowered for fragment in FORBIDDEN_TEXT):
        return False, "the rewrite module inspects judge infrastructure"
    has_entry = False
    for node in ast.walk(parsed):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [alias.name for alias in node.names] if isinstance(node, ast.Import) else [node.module or ""]
            for name in names:
                root = name.lstrip(".").split(".", 1)[0]
                if root not in ALLOWED_IMPORT_ROOTS:
                    return False, f"import of {root or 'an unknown module'} is not allowed"
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_CALLS:
            return False, f"call to {node.func.id} is not allowed"
        if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            return False, "dunder attribute access is not allowed"
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "rewrite_plan":
            has_entry = True
    return (True, "") if has_entry else (False, "rewrite_plan(plan) is missing")


def _reference_case_gains(suite: str) -> dict[str, float]:
    """The artifact's own recorded BinaryJoin/Yannakakis ratio, per case.

    Keyed by `(suite, query)` now that the two suites draw from three different
    benchmarks and both renumber their cases from 1. Keying on the query id alone
    silently mixed a dev case with the final case of the same number.
    """
    wanted = {p.stem for p in (JUDGE_DIR / "workloads" / suite).glob("*.json")}
    values: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    with (JUDGE_DIR / "upstream" / "timings_revision.csv").open(newline="") as handle:
        for row in csv.DictReader(handle):
            if row["query"] in wanted and row.get("suite", suite) == suite:
                values[row["query"]][row["method"]].append(float(row["duration(µs)"]))
    gains = {}
    for query in wanted:
        binary = statistics.median(values[query]["BinaryJoin"])
        yann = statistics.median(values[query]["Yannakakis"])
        gains[query] = binary / yann
    if gains.keys() != wanted:
        raise RuntimeError("reference timing calibration is incomplete")
    return gains


# 100 points is SCORE_DECADES orders of magnitude of aggregate gain over the
# binary join plan the optimiser produced. One decade: the withheld method's own
# recorded gain is 1.30 on the feedback suite and 1.43 on the graded one, so the
# ceiling stays far above anything this workload has been shown to reach.
SCORE_DECADES = 1.0


def _case_score(gain: float) -> float:
    """One query's score: zero at the binary plan, the full scale at 10x."""
    return min(100.0, max(0.0, (100.0 / SCORE_DECADES) * math.log10(max(1e-12, gain))))


def _score_gains(gains: dict[str, float], total_cases: int | None = None) -> tuple[float, float]:
    """Mean of the per-query scores; queries that produced no result score zero.

    Each query is measured on its own, so one that the policy could not rewrite
    inside its own time budget takes a zero for itself and leaves the others
    alone. Aggregating the *gains* geometrically could not express that — one
    failed query drove the product to the floor and the whole submission with it,
    which is how a solution that rewrote nine of eleven plans scored 0 against a
    reference of 11.

    Zero is the binary join plan; every 10x on a query is the full scale. The
    score is not rounded: whole points were coarse enough to hide a 4% change in
    aggregate gain, and with per-query scoring the mean of nineteen or twenty
    values carries real resolution below the point.

    It was `100 * G / (1 + G)`, which pays 50 of 100 for an aggregate gain of 1 —
    that is, for a rewrite that runs exactly as fast as the plan it was handed.
    Half the range was collected for producing any lowerable tree, the withheld
    method sat at 62, and the best agent on record at 64: the whole contest lived
    in fourteen points, and a genuine 10% speedup was worth two of them.

    Whole-point rounding is kept — sub-point timing differences are noise on this
    workload — but it now resolves about 2.3% of aggregate gain rather than 4.2%.
    """
    n = total_cases if total_cases else len(gains)
    if n <= 0:
        return 0.0, 0.0
    raw_score = sum(_case_score(v) for v in gains.values()) / n
    aggregate = (math.exp(sum(math.log(max(1e-12, v)) for v in gains.values()) / len(gains))
                 if gains else 0.0)
    return float(raw_score), aggregate


def _required_metrics(candidate: float, reference: float, **extra) -> dict:
    tolerance = 1e-9 * max(1.0, abs(reference))
    result = {
        "beats_reference": 1 if candidate >= reference - tolerance else 0,
        "reference_score": reference,
        "margin": candidate - reference,
    }
    result.update(extra)
    return result


def _apply_patch(path: str | Path):
    applied = apply_submission_patch(path, TASK_DIR, CONFIG)
    if not applied.ok and applied.metrics.get("valid_patch") == 1 and applied.metrics.get("patch_bytes") == 0:
        owner = Path(tempfile.mkdtemp(prefix="submission-empty-"))
        tree = owner / "tree"
        shutil.copytree(TASK_DIR / "harbor" / "app", tree, symlinks=True)
        return True, "", tree, applied.metrics
    if not applied.ok or applied.workdir is None:
        return False, applied.message, None, applied.metrics
    return True, "", applied.workdir, applied.metrics


def _build_plans(tree: Path, workloads: Path, output: Path) -> tuple[bool, str, dict[str, str]]:
    """Rewrite and lower each query in its own process, with its own timeout.

    One process over the whole suite meant one slow query zeroed the submission.
    That is the wrong reading of a failed rewrite: a policy that cannot transform
    a plan leaves the optimiser's binary plan in place and the query runs at the
    binary plan's speed. It loses the gain it might have won there; it does not
    lose the queries it did rewrite. The paper's own claim is exactly this — never
    worse than the binary plan — so the metric has to be able to express it.

    The agent solution measured on this task rewrote nine of eleven plans and ran
    out of time on the 12- and 14-leaf ones. Scored per suite that was 0 against a
    reference of 11; scored per query it is the eight it earned.
    """
    ok, reason = _source_policy(tree)
    if not ok:
        return False, reason, {}
    output.mkdir(parents=True, exist_ok=True)
    plans = sorted(workloads.glob("*.json"), key=lambda p: int(p.stem))
    if not plans:
        return False, "no workload plans", {}
    # The declared limit is per query. Each plan is rewritten and lowered in its
    # own process with its own budget, so a policy that is slow on one join size
    # loses that query and keeps the rest.
    budget = PLAN_TIMEOUT_SECONDS
    failures: dict[str, str] = {}
    with tempfile.TemporaryDirectory(prefix="plan-one-") as one_text:
        one = Path(one_text)
        for plan in plans:
            case = one / plan.stem
            case.mkdir()
            shutil.copy(plan, case / plan.name)
            command = [
                sys.executable, "-I", str(JUDGE_DIR / "plan_builder.py"),
                "--app", str(tree), "--workloads", str(case),
                "--output", str(output), "--upstream", str(JUDGE_DIR / "upstream"),
            ]
            try:
                proc = subprocess.run(
                    command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=budget,
                    env={"PATH": os.environ.get("PATH", ""), "PYTHONHASHSEED": "0",
                         "PYTHONDONTWRITEBYTECODE": "1"},
                )
            except subprocess.TimeoutExpired:
                failures[plan.stem] = "timed out"
                continue
            if proc.returncode != 0 or not (output / plan.name).is_file():
                failures[plan.stem] = "rewrite or lowering failed"
    if len(failures) == len(plans):
        return False, "plan rewriting failed on every query", failures
    return True, "", failures


def _write_configs(workloads: Path, reference: Path, candidate: Path, config_dir: Path) -> dict[str, bool]:
    identical = {}
    correctness_dir = config_dir / "correctness"
    timing_dir = config_dir / "timing"
    correctness_dir.mkdir(parents=True, exist_ok=True)
    timing_dir.mkdir(parents=True, exist_ok=True)
    for ir in sorted(workloads.glob("*.json"), key=lambda p: int(p.stem)):
        ref = reference / f"{ir.stem}.json"
        cand = candidate / f"{ir.stem}.json"
        identical[ir.stem] = hashlib.sha256(ref.read_bytes()).digest() == hashlib.sha256(cand.read_bytes()).digest()
        correctness = [("BinaryJoin", ir), ("Reference", ref), ("Candidate", cand)]
        timing = [("ReferenceA", ref), ("CandidateA", cand), ("CandidateB", cand), ("ReferenceB", ref)]
        for directory, plans in ((correctness_dir, correctness), (timing_dir, timing)):
            payload = {"query": ir.stem, "plans": [{"method": method, "path": str(path.resolve())} for method, path in plans]}
            (directory / f"{ir.stem}.json").write_text(json.dumps(payload), encoding="utf-8")
    return identical


def _run_engine(configs: Path, timings: Path, repetitions: int) -> tuple[bool, str]:
    timings.write_text("duration(µs),method,variant,query\n", encoding="utf-8")
    command = [
        str(JUDGE_DIR / "bin" / "join_runner"),
        "--configs", str(configs), "--data", str(JUDGE_DIR / "data"),
        "--timings-outfile", str(timings), "--repetitions", str(repetitions),
    ]
    try:
        proc = subprocess.run(
            command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
            timeout=ENGINE_TIMEOUT_SECONDS, env={"PATH": os.environ.get("PATH", "")},
        )
    except subprocess.TimeoutExpired:
        return False, "Stats-CEB execution timed out"
    if proc.returncode != 0:
        diagnostic = proc.stderr.decode("utf-8", "replace")[-32768:]
        if "binaryjoin_vs_yannakakis.rs" in diagnostic and "left == right" in diagnostic:
            return False, "Stats-CEB output equality check failed"
        if proc.returncode < 0:
            # Killed by a signal, not a refusal. This masked the task's real
            # defect for two rounds: the correctness pass runs the original
            # BinaryJoin plan, which needs more than the 2048 MB the task asked
            # for, so the judge container OOM-killed it and every submission —
            # the authors' own reference included — scored 0 under the message
            # below. A dead process is not a verdict about the plan.
            return False, (f"Stats-CEB engine was killed by signal {-proc.returncode} "
                           "(out of memory or wall-clock kill), not rejected")
        return False, "Stats-CEB engine rejected an executable plan"
    return True, ""


def _live_relative_gains(timings: Path, identical: dict[str, bool]) -> dict[str, float]:
    values: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    with timings.open(newline="") as handle:
        for row in csv.DictReader(handle):
            values[row["query"]][row["method"]].append(float(row["duration(µs)"]))
    result = {}
    for query, same in identical.items():
        ref = values[query]["ReferenceA"] + values[query]["ReferenceB"]
        cand = values[query]["CandidateA"] + values[query]["CandidateB"]
        if len(ref) != 2 * REPETITIONS or len(cand) != 2 * REPETITIONS:
            raise ValueError("timing output is incomplete")
        result[query] = 1.0 if same else statistics.median(ref) / statistics.median(cand)
    return result


def evaluate(solution_path: str) -> tuple[float, float, str, dict]:
    """Apply one patch and score real Stats-CEB execution; never propagate bad input."""
    candidate_tree = reference_tree = None
    try:
        suite = _suite_name()
        official = _reference_case_gains(suite)
        reference_score, reference_gain = _score_gains(official, len(official))
        ok, reason, candidate_tree, patch_metrics = _apply_patch(solution_path)
        if not ok or candidate_tree is None:
            return 0.0, 0.0, reason or "invalid patch", _required_metrics(0.0, reference_score, **patch_metrics)
        ok, reason, reference_tree, _ = _apply_patch(TASK_DIR / "reference.patch")
        if not ok or reference_tree is None:
            return 0.0, 0.0, "reference preparation failed", _required_metrics(0.0, reference_score)
        with tempfile.TemporaryDirectory(prefix="statsceb-eval-") as temp_text:
            temp = Path(temp_text)
            workloads = JUDGE_DIR / "workloads" / suite
            failed: dict[str, dict[str, str]] = {}
            for label, tree, output in (("reference", reference_tree, temp / "reference"),
                                        ("candidate", candidate_tree, temp / "candidate")):
                built, build_reason, per_query = _build_plans(tree, workloads, output)
                if not built:
                    if label == "reference":
                        return 0.0, 0.0, "reference preparation failed", _required_metrics(
                            0.0, reference_score, **patch_metrics)
                    return 0.0, 0.0, build_reason, _required_metrics(
                        0.0, reference_score, rewritten=0, not_rewritten=len(official), **patch_metrics)
                failed[label] = per_query
            # A query the reference itself could not lower is not a fair case for
            # anyone, so it leaves the suite. A query only the candidate failed
            # stays, and scores as the binary plan it left in place.
            unusable = set(failed["reference"])
            skipped = set(failed["candidate"]) - unusable
            timed = {p.stem for p in (temp / "candidate").glob("*.json")} \
                  & {p.stem for p in (temp / "reference").glob("*.json")}
            live_dir = temp / "live"
            live_dir.mkdir()
            for stem in timed:
                shutil.copy(workloads / f"{stem}.json", live_dir / f"{stem}.json")
            identical = _write_configs(live_dir, temp / "reference", temp / "candidate", temp / "configs")
            ran, run_reason = _run_engine(temp / "configs" / "correctness", temp / "correctness.csv", 1)
            if not ran:
                return 0.0, 0.0, run_reason, _required_metrics(0.0, reference_score, **patch_metrics)
            ran, run_reason = _run_engine(temp / "configs" / "timing", temp / "timings.csv", REPETITIONS)
            if not ran:
                return 0.0, 0.0, run_reason, _required_metrics(0.0, reference_score, **patch_metrics)
            relative = _live_relative_gains(temp / "timings.csv", identical)
            # Only queries the candidate actually rewrote and that were timed earn
            # anything. Every other query in the suite is a zero for itself; the
            # divisor below is the whole suite, not the part that succeeded, so a
            # policy cannot raise its score by refusing the queries it is bad at.
            effective = {q: official[q] * relative[q] for q in official
                         if q in relative and q not in unusable}
            graded = len(official) - len(unusable)
            if not effective:
                return 0.0, 0.0, "no query produced a timed result", _required_metrics(
                    0.0, reference_score, rewritten=0, zeroed=graded, **patch_metrics)
            score, aggregate_gain = _score_gains(effective, graded)
        metrics = _required_metrics(
            score, reference_score, aggregate_speedup=round(aggregate_gain, 3),
            reference_aggregate_speedup=round(reference_gain, 3), case_count=len(effective),
            rewritten=len(effective), zeroed=graded - len(effective),
            **patch_metrics,
        )
        zero_note = f"; {graded - len(effective)} scored zero" if graded > len(effective) else ""
        return score, score, f"valid rewrite; {len(effective)} of {graded} queries scored{zero_note}", metrics
    except Exception:
        try:
            official_all = _reference_case_gains(_suite_name())
            reference_score, _ = _score_gains(official_all, len(official_all))
        except Exception:
            reference_score = 0.0
        return 0.0, 0.0, "evaluation failed safely", _required_metrics(0.0, reference_score)
    finally:
        for tree in (candidate_tree, reference_tree):
            if tree is not None:
                shutil.rmtree(tree.parent, ignore_errors=True)


def main() -> int:
    path = sys.argv[1] if len(sys.argv) > 1 else ""
    score, unbounded, message, metrics = evaluate(path)
    print(json.dumps({"score": score, "score_unbounded": unbounded, "message": message, "metrics": metrics}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
