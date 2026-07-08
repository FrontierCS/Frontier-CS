"""Regression tests for algorithmic @k aggregation in ``EvaluationState``.

These pin the fix from #161/#162: failed evaluations (compile errors, timeouts,
missing solutions) must count as ``0`` in the ``@k`` denominators instead of
being dropped, so ``score_at_1``/``pass_at_1`` are computed across *all* problems
rather than only the ones that happened to run successfully.
"""

import pytest

from frontier_cs.batch.state import EvaluationState, PairResult


def _state(rows):
    """Build an EvaluationState from (problem, variant, status, score) rows.

    Solutions use the nested ``{problem}/{model}.cpp`` layout so the aggregator
    parses model ``gpt5.2`` and the given variant from the filename.
    """
    results = {}
    for problem, variant, status, score in rows:
        suffix = "" if variant == 0 else f"_{variant}"
        solution = f"{problem}/gpt5.2{suffix}.cpp"
        pair_id = f"{solution}:{problem}"
        results[pair_id] = PairResult(pair_id=pair_id, status=status, score=score)
    return EvaluationState(results=results)


def test_reproduces_issue_161_denominator():
    """The exact shape reported in #161: 108 pass, 40 zero-score, 24 failed.

    With failures counted as zero the denominator is the full 172 problems,
    not the 148 that ran successfully.
    """
    rows = []
    for i in range(108):  # successful, positive score
        rows.append((f"p{i}", 0, "success", 100.0))
    for i in range(108, 148):  # successful, zero score
        rows.append((f"p{i}", 0, "success", 0.0))
    for i in range(148, 172):  # failed (compile error / timeout)
        status = "timeout" if i % 2 else "error"
        rows.append((f"p{i}", 0, status, None))

    stats = _state(rows).aggregate_by_model()["gpt5.2"]

    assert stats["total"] == 172
    assert stats["successful"] == 148
    assert stats["failed"] == 24
    # Denominator is all attempted problems, not just the successful ones.
    assert stats["num_problems"] == 172
    assert stats["pass_at_1"] == pytest.approx(108 / 172)
    assert stats["pass_at_5"] == pytest.approx(108 / 172)
    # score_at_1 averages the base-variant score (0 for failures) over 172 problems.
    assert stats["score_at_1"] == pytest.approx(10800 / 172)
    assert stats["score_at_5"] == pytest.approx(10800 / 172)
    # avg_score stays a success-only statistic and is unaffected by the fix.
    assert stats["avg_score"] == pytest.approx(10800 / 148)


def test_minimal_failed_counts_as_zero():
    """A successful zero-score run is an attempt; a failure is a zero, not a drop."""
    rows = [
        ("a", 0, "success", 80.0),  # pass
        ("b", 0, "success", 0.0),   # attempted, scored 0
        ("c", 0, "error", None),    # compile error -> 0
        ("d", 0, "timeout", None),  # timeout -> 0
    ]
    stats = _state(rows).aggregate_by_model()["gpt5.2"]

    assert stats["total"] == 4
    assert stats["successful"] == 2
    assert stats["failed"] == 2
    assert stats["num_problems"] == 4
    assert stats["pass_at_1"] == pytest.approx(1 / 4)   # only "a" scores > 0
    assert stats["score_at_1"] == pytest.approx((80 + 0 + 0 + 0) / 4)


def test_failed_base_variant_still_counted_multivariant():
    """A problem whose base variant failed must not vanish from the denominator.

    Base variant (0) failed but a sibling variant passed: the problem still
    counts, contributes 0 to @1, yet passes @5 via the sibling.
    """
    rows = [
        ("solo", 0, "error", None),     # base variant failed -> 0
        ("solo", 1, "success", 60.0),   # sibling variant passed
    ]
    stats = _state(rows).aggregate_by_model()["gpt5.2"]

    assert stats["num_problems"] == 1          # not dropped
    assert stats["pass_at_1"] == pytest.approx(0.0)   # base variant is a 0
    assert stats["score_at_1"] == pytest.approx(0.0)
    assert stats["pass_at_5"] == pytest.approx(1.0)   # sibling rescues @5
    assert stats["score_at_5"] == pytest.approx(60.0)
    assert stats["avg_at_5"] == pytest.approx((0 + 60 + 0 + 0 + 0) / 5)
