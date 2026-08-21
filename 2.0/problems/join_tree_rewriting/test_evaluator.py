from __future__ import annotations

import importlib.util
import math
import shutil
import subprocess
import sys
from pathlib import Path


TASK_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TASK_DIR))
SPEC = importlib.util.spec_from_file_location("join_tree_evaluator", TASK_DIR / "evaluator.py")
assert SPEC is not None and SPEC.loader is not None
EVALUATOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = EVALUATOR
SPEC.loader.exec_module(EVALUATOR)


def _development(monkeypatch) -> None:
    monkeypatch.delenv("FRONTIER_SUBMISSION_ROLE", raising=False)
    monkeypatch.setattr(EVALUATOR, "REPETITIONS", 1)
    monkeypatch.setattr(EVALUATOR, "_suite_name", lambda: "test")


def test_reference_scores_and_metrics_are_complete(monkeypatch) -> None:
    _development(monkeypatch)
    score, unbounded, message, metrics = EVALUATOR.evaluate(str(TASK_DIR / "reference.patch"))
    assert math.isfinite(score) and 0.0 <= score <= 100.0
    assert math.isfinite(unbounded)
    assert "valid rewrite" in message
    assert {"beats_reference", "reference_score", "margin"} <= metrics.keys()


def test_reference_repeats_exactly(monkeypatch) -> None:
    _development(monkeypatch)
    scores = [EVALUATOR.evaluate(str(TASK_DIR / "reference.patch"))[0] for _ in range(3)]
    assert max(scores) == min(scores)


def test_solver_packaging_path_is_accepted(tmp_path, monkeypatch) -> None:
    _development(monkeypatch)
    checkout = tmp_path / "app"
    shutil.copytree(TASK_DIR / "harbor" / "app", checkout)
    for command in (
        ["git", "init", "-q"],
        ["git", "config", "user.email", "test@example.invalid"],
        ["git", "config", "user.name", "Evaluator Test"],
        ["git", "add", "."],
        ["git", "commit", "-qm", "substrate"],
        ["git", "apply", str(TASK_DIR / "reference.patch")],
    ):
        subprocess.run(command, cwd=checkout, check=True)
    patch = checkout / "solution.patch"
    patch.write_text("stale egress file\n", encoding="utf-8")
    (checkout / "submit.sh").write_text("#!/bin/sh\n", encoding="utf-8")
    subprocess.run(
        ["bash", str(checkout / "make_submission.sh"), str(patch)],
        cwd=checkout,
        env={"APP_DIR": str(checkout), "PATH": "/usr/bin:/bin"},
        check=True,
    )
    score, _, message, metrics = EVALUATOR.evaluate(str(patch))
    assert score > 0.0
    assert "valid rewrite" in message
    assert metrics["valid_patch"] == 1


def test_invalid_submission_scores_zero_without_crashing(tmp_path, monkeypatch) -> None:
    _development(monkeypatch)
    bad = tmp_path / "bad.patch"
    bad.write_text("this is not a diff\n", encoding="utf-8")
    score, unbounded, message, metrics = EVALUATOR.evaluate(str(bad))
    assert score == 0.0 and unbounded == 0.0
    assert "changes no files" in message
    assert {"beats_reference", "reference_score", "margin"} <= metrics.keys()


def test_metric_orders_deliberate_solutions(monkeypatch) -> None:
    _development(monkeypatch)
    weak = EVALUATOR.evaluate(str(TASK_DIR / "baseline_naive.patch"))[0]
    reference = EVALUATOR.evaluate(str(TASK_DIR / "reference.patch"))[0]
    official = EVALUATOR._reference_case_gains("test")
    strong = EVALUATOR._score_gains({query: gain * 2.0 for query, gain in official.items()})[0]
    assert weak < reference < strong


def test_final_suite_is_distinct_and_scores(monkeypatch) -> None:
    dev = {path.stem for path in (EVALUATOR.JUDGE_DIR / "workloads" / "dev").glob("*.json")}
    final = {path.stem for path in (EVALUATOR.JUDGE_DIR / "workloads" / "final").glob("*.json")}
    assert dev.isdisjoint(final)
    assert len(dev) == len(final) == 12
    monkeypatch.setenv("FRONTIER_SUBMISSION_ROLE", "final")
    assert EVALUATOR._suite_name() == "final"
    monkeypatch.setattr(EVALUATOR, "_suite_name", lambda: "test")
    monkeypatch.setattr(EVALUATOR, "REPETITIONS", 1)
    score, _, _, metrics = EVALUATOR.evaluate(str(TASK_DIR / "reference.patch"))
    assert 0.0 <= score <= 100.0
    assert {"beats_reference", "reference_score", "margin"} <= metrics.keys()
