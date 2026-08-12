"""CI smoke tests for the directory-submission integrity boundary."""
from __future__ import annotations

import importlib.util
import os
import shutil
import tarfile
import tempfile
import unittest
from pathlib import Path
from typing import Callable


TASK_ROOT = Path(__file__).resolve().parents[1]
SUBSTRATE = TASK_ROOT / "harbor" / "app"
EXCLUDE = (".git", "bin", "obj", "__pycache__")

spec = importlib.util.spec_from_file_location("metaopt_task_evaluator", TASK_ROOT / "evaluator.py")
if spec is None or spec.loader is None:
    raise RuntimeError("could not load evaluator")
evaluator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evaluator)


def _should_exclude(path: Path, root: Path) -> bool:
    relative = path.relative_to(root)
    rel_text = relative.as_posix()
    parts = set(relative.parts)
    return any(
        rel_text == pattern or rel_text.startswith(pattern + "/") or pattern in parts
        for pattern in EXCLUDE
    )


def _harbor_round_trip(
    temporary: Path,
    mutate: Callable[[Path], None] | None = None,
) -> Path:
    """Stage /app, archive it like submit.py, then extract it like judge_server.py."""
    staged = temporary / "agent_app"
    shutil.copytree(SUBSTRATE, staged)
    for name in evaluator.HARBOR_RUNTIME_FILES:
        (staged / name).write_text(f"Harbor runtime fixture: {name}\n", encoding="utf-8")
    if mutate is not None:
        mutate(staged)

    archive = temporary / "submission.tar.gz"
    with tarfile.open(archive, mode="w:gz") as stream:
        for path in sorted(staged.rglob("*")):
            if path.is_file() and not _should_exclude(path, staged):
                stream.add(path, arcname=path.relative_to(staged).as_posix())

    relocated = temporary / "judge" / "submission"
    relocated.mkdir(parents=True)
    with tarfile.open(archive, mode="r:gz") as stream:
        members = stream.getmembers()
        if any(Path(member.name).is_absolute() or ".." in Path(member.name).parts for member in members):
            raise RuntimeError("unsafe test archive")
        stream.extractall(relocated)
    return relocated


class HarborSubmissionSmokeTests(unittest.TestCase):
    def test_private_suites_are_disjoint_and_topology_balanced(self) -> None:
        agent = evaluator._suite("agent")
        final = evaluator._suite("final")
        self.assertEqual(len(agent), 15)
        self.assertEqual(len(final), 15)
        self.assertTrue(
            {instance["id"] for instance in agent}.isdisjoint(
                instance["id"] for instance in final
            )
        )
        for role in ("agent", "final"):
            topology_counts = {topology: 0 for topology in evaluator.TOPOLOGY_EDGES}
            for topology, _seed in evaluator.CASE_SPECS_BY_ROLE[role]:
                topology_counts[topology] += 1
            self.assertEqual(set(topology_counts.values()), {evaluator.CASES_PER_TOPOLOGY})

    def test_submission_role_fails_closed(self) -> None:
        previous = os.environ.get("FRONTIER_SUBMISSION_ROLE")
        try:
            os.environ["FRONTIER_SUBMISSION_ROLE"] = "final"
            self.assertEqual(evaluator._evaluation_role(), "final")
            os.environ["FRONTIER_SUBMISSION_ROLE"] = "unexpected"
            with self.assertRaisesRegex(ValueError, "invalid submission role"):
                evaluator._evaluation_role()
        finally:
            if previous is None:
                os.environ.pop("FRONTIER_SUBMISSION_ROLE", None)
            else:
                os.environ["FRONTIER_SUBMISSION_ROLE"] = previous

    def test_reviewer_strategies_are_content_authenticated(self) -> None:
        for path in (
            TASK_ROOT / "reference.py",
            TASK_ROOT / "baseline_clustered.py",
            TASK_ROOT / "baseline_naive.py",
            TASK_ROOT / "baseline_mid.py",
            TASK_ROOT / "baseline_strong.py",
        ):
            evaluator._load_local_strategy(path)

    def test_untouched_starter_validates_and_builds(self) -> None:
        with tempfile.TemporaryDirectory(prefix="tegap_ci_starter_") as raw:
            submitted = _harbor_round_trip(Path(raw))
            self.assertEqual(evaluator._locked_tree_hash(submitted), evaluator.LOCKED_TREE_HASH)
            self.assertEqual(evaluator._run_csharp_project(submitted, []), [])

    def test_editable_file_and_candidate_helper_validate_and_build(self) -> None:
        def mutate(staged: Path) -> None:
            editable = staged / "MetaOptimize/TrafficEngineering/BudgetedDemandSearch.cs"
            text = editable.read_text(encoding="utf-8")
            editable.write_text(text.replace("return answer;", "return answer; // CI edit"), encoding="utf-8")
            helpers = staged / "MetaOptimize/TrafficEngineering/Candidate"
            helpers.mkdir()
            (helpers / "SmokeCandidateHelper.cs").write_text(
                "namespace MetaOptimize;\ninternal static class SmokeCandidateHelper { }\n",
                encoding="utf-8",
            )

        with tempfile.TemporaryDirectory(prefix="tegap_ci_editable_") as raw:
            submitted = _harbor_round_trip(Path(raw), mutate)
            self.assertEqual(evaluator._locked_tree_hash(submitted), evaluator.LOCKED_TREE_HASH)
            self.assertEqual(evaluator._run_csharp_project(submitted, []), [])

    def test_locked_file_change_is_rejected(self) -> None:
        def mutate(staged: Path) -> None:
            locked = staged / "MetaOptimize.Challenge/Program.cs"
            locked.write_text(locked.read_text(encoding="utf-8") + "\n", encoding="utf-8")

        with tempfile.TemporaryDirectory(prefix="tegap_ci_tamper_") as raw:
            submitted = _harbor_round_trip(Path(raw), mutate)
            with self.assertRaisesRegex(ValueError, "locked substrate file changed"):
                evaluator._validate_project(submitted)

    def test_nonzero_csharp_candidate_reports_frontier_metrics(self) -> None:
        candidate_source = r'''#pragma warning disable
namespace MetaOptimize;

using System;
using System.Collections.Generic;

public static class BudgetedDemandSearch
{
    public static int[] Find(AdversarialSearchInstance instance, IGapOracle oracle)
    {
        var random = new Random(0x5eed + instance.NodeCount);
        var best = new int[instance.Pairs.Length];
        var bestGap = -1.0;
        var attempts = 0;
        while (oracle.QueriesUsed < oracle.QueryBudget && attempts++ < 100000)
        {
            var candidate = new int[instance.Pairs.Length];
            var count = random.Next(Math.Max(1, instance.DensityLimit / 2), instance.DensityLimit + 1);
            var selected = new HashSet<int>();
            while (selected.Count < count)
            {
                selected.Add(random.Next(candidate.Length));
            }

            foreach (var index in selected)
            {
                candidate[index] = random.Next(1, instance.Levels.Length);
            }

            try
            {
                var result = oracle.Evaluate(candidate);
                if (result.Gap > bestGap)
                {
                    bestGap = result.Gap;
                    best = candidate;
                }
            }
            catch (ArgumentException)
            {
            }
        }

        return best;
    }
}
'''

        def mutate(staged: Path) -> None:
            editable = staged / "MetaOptimize/TrafficEngineering/BudgetedDemandSearch.cs"
            editable.write_text(candidate_source, encoding="utf-8")

        with tempfile.TemporaryDirectory(prefix="tegap_ci_scored_") as raw:
            submitted = _harbor_round_trip(Path(raw), mutate)
            score, mean_gap, message, metrics = evaluator.evaluate(str(submitted))
            self.assertGreater(score, 0.0, message)
            self.assertGreater(mean_gap, 0.0, message)
            self.assertIn(metrics.get("beats_reference"), (0, 1))
            self.assertGreater(metrics.get("reference_score", 0.0), 0.0)
            self.assertIn("margin", metrics)
            self.assertEqual(
                set(metrics),
                {"beats_reference", "reference_score", "margin", "mean_gap", "instance_count"},
            )
            self.assertNotIn("per_case_gaps", message)
            self.assertNotIn("per_topology_mean", message)


if __name__ == "__main__":
    unittest.main()
