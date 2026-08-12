from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


PROBLEM_DIR = Path(__file__).parent
SPEC = importlib.util.spec_from_file_location(
    "rocksdb_native_compaction_evaluator",
    PROBLEM_DIR / "evaluator.py",
)
assert SPEC is not None and SPEC.loader is not None
EVALUATOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = EVALUATOR
SPEC.loader.exec_module(EVALUATOR)

VALIDATOR_SPEC = importlib.util.spec_from_file_location(
    "rocksdb_native_compaction_validator",
    PROBLEM_DIR / "harbor" / "app" / "validate_solution_patch.py",
)
assert VALIDATOR_SPEC is not None and VALIDATOR_SPEC.loader is not None
VALIDATOR = importlib.util.module_from_spec(VALIDATOR_SPEC)
VALIDATOR_SPEC.loader.exec_module(VALIDATOR)


def _case(gain: float, *, profile: str, component: float = 1.0) -> dict:
    return {
        "gain": gain,
        "profile": profile,
        "ratios": {name: component for name in EVALUATOR.METRIC_WEIGHTS},
        "candidate_intra_l0": 0,
        "vanilla_intra_l0": 0,
    }


def _cases(gains: list[float], *, component: float = 1.0) -> list[dict]:
    return [
        _case(gain, profile=f"profile_{index}", component=component)
        for index, gain in enumerate(gains)
    ]


def _agent_accepts(text: str) -> bool:
    try:
        VALIDATOR.validate(text)
    except SystemExit:
        return False
    return True


def test_reference_patch_is_valid() -> None:
    ok, message, metrics = EVALUATOR.validate_patch(PROBLEM_DIR / "reference.patch")
    assert ok, message
    assert metrics["changed_files"] == [
        "db/compaction/compaction_picker.cc"
    ]
    assert (PROBLEM_DIR / "reference.cpp").read_bytes() == (
        PROBLEM_DIR / "reference.patch"
    ).read_bytes()


def test_no_improvement_scores_zero() -> None:
    score, unbounded, _ = EVALUATOR._score_cases(_cases([1.0] * 6))
    assert score == 0.0
    assert unbounded < 0.0


def test_gain_below_half_percent_is_inside_noise_floor() -> None:
    score, unbounded, _ = EVALUATOR._score_cases(_cases([1.004] * 6))
    assert score == 0.0
    assert unbounded < 0.0


def test_gain_at_half_percent_floor_scores_zero() -> None:
    score, unbounded, _ = EVALUATOR._score_cases(_cases([1.005] * 6))
    assert score == 0.0
    assert abs(unbounded) < 1e-9


def test_reference_level_gain_lands_midscale() -> None:
    score, unbounded, _ = EVALUATOR._score_cases(_cases([1.011] * 6))
    assert 45.0 < score < 55.0
    assert abs(score - unbounded) < 1e-9


def test_invalid_submission_ranks_below_any_valid_run() -> None:
    score, unbounded, _, metrics = EVALUATOR._invalid("boom")
    assert score == 0.0
    assert unbounded == EVALUATOR.INVALID_SCORE_UNBOUNDED
    assert metrics["valid_patch"] == 0

    _, worst_valid_unbounded, _ = EVALUATOR._score_cases(_cases([0.5] * 6))
    assert worst_valid_unbounded > EVALUATOR.INVALID_SCORE_UNBOUNDED
    assert (0.0, worst_valid_unbounded) > (0.0, EVALUATOR.INVALID_SCORE_UNBOUNDED)
    assert (0.0, 0.0) > (0.0, worst_valid_unbounded)


def test_evaluate_reports_sentinel_for_invalid_patch(tmp_path) -> None:
    reference = (PROBLEM_DIR / "reference.patch").read_text()
    outside = reference.replace(
        "db/compaction/compaction_picker.cc", "db/db_impl/db_impl.cc"
    )
    patch = tmp_path / "solution.patch"
    patch.write_text(outside)
    score, unbounded, message, metrics = EVALUATOR.evaluate(str(patch))
    assert score == 0.0
    assert unbounded == EVALUATOR.INVALID_SCORE_UNBOUNDED
    assert "outside the editable surface" in message
    assert metrics["valid_patch"] == 0


def test_evaluate_keeps_empty_patch_as_neutral_baseline(tmp_path) -> None:
    patch = tmp_path / "solution.patch"
    patch.write_text("")
    score, unbounded, message, metrics = EVALUATOR.evaluate(str(patch))
    assert score == 0.0
    assert unbounded == 0.0
    assert metrics["empty_patch"] == 1
    assert unbounded > EVALUATOR.INVALID_SCORE_UNBOUNDED


def test_single_profile_spike_scores_zero() -> None:
    cases = _cases([1.10] + [1.0] * 5)
    score, _, metrics = EVALUATOR._score_cases(cases)
    assert score == 0.0
    assert metrics["improved_profile_count"] == 1
    assert metrics["required_improved_profile_count"] == 3
    assert metrics["worst_case_gain"] == 1.0


def test_multi_profile_improvement_can_score() -> None:
    cases = _cases([1.04, 1.04, 1.04, 1.0, 1.0, 1.0])
    score, _, metrics = EVALUATOR._score_cases(cases)
    assert score > 0.0
    assert metrics["improved_profile_count"] == 3


def test_target_gain_reaches_full_score() -> None:
    score, unbounded, _ = EVALUATOR._score_cases(
        _cases([EVALUATOR.TARGET_ROBUST_GAIN] * 6)
    )
    assert score > 99.9
    assert abs(unbounded - 100.0) < 1e-6


def test_gains_far_above_target_saturate_bounded_score() -> None:
    score, unbounded, _ = EVALUATOR._score_cases(_cases([1.20] * 6))
    assert score == 100.0
    assert unbounded > 100.0


def test_severe_component_regression_hard_fails() -> None:
    cases = _cases([1.10] * 5) + [_case(1.0, profile="profile_5", component=0.49)]
    score, _, metrics = EVALUATOR._score_cases(cases)
    assert score == 0.0
    assert metrics["component_floor"] == 0.49


def test_component_regression_caps_are_graduated() -> None:
    for component, expected_cap in ((0.50, 0.0), (0.51, 10.0), (0.67, 25.0)):
        cases = _cases([2.0] * 6, component=component)
        score, _, _ = EVALUATOR._score_cases(cases)
        assert score <= expected_cap


def test_multiple_material_profile_regressions_score_zero() -> None:
    cases = _cases([1.10, 1.10, 1.10, 1.10, 0.97, 0.97])
    score, _, metrics = EVALUATOR._score_cases(cases)
    assert score == 0.0
    assert metrics["material_regression_count"] == 2


def test_final_cases_are_stable_per_suite_key(monkeypatch) -> None:
    monkeypatch.setenv("FRONTIER_LSM_FINAL_SUITE_KEY", "suite-a")
    first = EVALUATOR._generate_final_cases()
    second = EVALUATOR._generate_final_cases()
    assert sorted(profile for _, profile in first) == sorted(
        profile for profile in EVALUATOR.FINAL_PROFILES for _ in range(2)
    )
    assert sorted(profile for _, profile in second) == sorted(
        profile for profile in EVALUATOR.FINAL_PROFILES for _ in range(2)
    )
    assert len({seed for seed, _ in first}) == len(first)
    assert all(seed > 0 for seed, _ in first)
    assert first == second

    monkeypatch.setenv("FRONTIER_LSM_FINAL_SUITE_KEY", "suite-b")
    assert EVALUATOR._generate_final_cases() != first


def test_feedback_covers_every_final_profile() -> None:
    feedback_profiles = {
        profile for _, profile in EVALUATOR._feedback_cases() if profile != "smoke"
    }
    assert feedback_profiles == set(EVALUATOR.FINAL_PROFILES)


def test_agent_and_judge_patch_policies_match() -> None:
    assert VALIDATOR.ALLOWLIST == EVALUATOR.ALLOWLIST
    assert VALIDATOR.MAX_CHANGED_FILES == EVALUATOR.MAX_CHANGED_FILES
    assert VALIDATOR.STRUCTURAL_MARKERS == EVALUATOR.STRUCTURAL_MARKERS
    assert VALIDATOR.FORBIDDEN_IDENTIFIERS == EVALUATOR.FORBIDDEN_IDENTIFIERS
    assert (
        VALIDATOR.FORBIDDEN_CALL_IDENTIFIERS
        == EVALUATOR.FORBIDDEN_CALL_IDENTIFIERS
    )
    assert VALIDATOR.FORBIDDEN_FRAGMENTS == EVALUATOR.FORBIDDEN_FRAGMENTS

    reference = (PROBLEM_DIR / "reference.patch").read_text()
    repeated = "\n".join(reference for _ in range(EVALUATOR.MAX_CHANGED_FILES + 1))
    outside = reference.replace(
        "db/compaction/compaction_picker.cc", "db/db_impl/db_impl.cc"
    )
    assert outside != reference
    for text in ("", reference, repeated, outside):
        judge_ok, _, _ = EVALUATOR._validate_patch_text(text, allow_empty=True)
        assert _agent_accepts(text) == judge_ok

    anchor = "+        expanded_inputs_size = TotalFileSize(expanded_inputs.files);"
    for added_line in (
        "+        const auto probe = ioptions_.clock->NowMicros();",
        "+        const auto probe = clock();",
        "+        const auto probe = gettimeofday(nullptr, nullptr);",
        "+        const auto probe = std::random_device{}();",
    ):
        probe = reference.replace(anchor, f"{added_line}\n{anchor}")
        assert probe != reference
        judge_ok, _, _ = EVALUATOR._validate_patch_text(probe, allow_empty=True)
        assert not judge_ok
        assert not _agent_accepts(probe)


def test_patch_policy_allows_removal_only_changes() -> None:
    text = """diff --git a/db/compaction/compaction_picker.cc b/db/compaction/compaction_picker.cc
--- a/db/compaction/compaction_picker.cc
+++ b/db/compaction/compaction_picker.cc
@@ -1 +0,0 @@
-obsolete_policy_branch();
"""
    judge_ok, message, _ = EVALUATOR._validate_patch_text(text, allow_empty=True)
    assert judge_ok, message
    assert _agent_accepts(text)


def test_patch_policy_allows_legitimate_picker_context_names() -> None:
    reference = (PROBLEM_DIR / "reference.patch").read_text()
    anchor = "+        expanded_inputs_size = TotalFileSize(expanded_inputs.files);"
    additions = "\n".join(
        (
            "+        const auto path_count = ioptions_.db_paths.size();",
            "+        const uint64_t seed = path_count;",
            "+        SystemClock* clock = nullptr;",
        )
    )
    probe = reference.replace(anchor, f"{additions}\n{anchor}")
    assert probe != reference
    judge_ok, message, _ = EVALUATOR._validate_patch_text(probe, allow_empty=True)
    assert judge_ok, message
    assert _agent_accepts(probe)


def test_read_amplification_instrumentation_is_enabled() -> None:
    harness = (PROBLEM_DIR / "judge" / "harness" / "lsm_policy_harness.cc").read_text()
    assert "topt.read_amp_bytes_per_bit = 16;" in harness


def test_case_arms_run_once_in_parallel_pair(monkeypatch) -> None:
    calls: list[str] = []

    def fake_run(
        binary: Path, trusted_inspector: Path, seed: int, profile: str
    ) -> dict:
        calls.append(binary.name)
        return {
            "ok": True,
            "correctness_ok": True,
            "_wall_seconds": 1.0,
            "user_put_bytes": 1 << 30,
            "drain_compaction_bytes": 0,
            "trusted_compaction_output_bytes": 0,
            "trusted_upper_level_files": 0,
            "table_created_bytes": 2 << 30,
            "l0_trigger": 4,
            "pre_drain_pending_compaction_bytes": 0,
            "pre_drain_l0_files": 2,
            "pre_drain_l0_files_by_cf": [2],
            "pre_drain_level_files": [2, 1, 1, 1, 1, 1],
            "column_families": 1,
            "base_fingerprint": 123,
            "lsm_waf": 2.0,
            "read_amp": 1.5,
            "pre_drain_space_amp": 1.2,
            "stall_micros": 1000,
            "intra_l0_compactions": 1,
        }

    monkeypatch.setattr(EVALUATOR, "_run_harness", fake_run)
    result = EVALUATOR._paired_case(
        Path("vanilla"), Path("candidate"), 1202, "l0_pressure"
    )
    assert result["ok"]
    assert sorted(calls) == ["candidate", "vanilla"]


def test_feedback_case_runs_one_stable_pair(monkeypatch) -> None:
    calls: list[str] = []

    def fake_run(
        binary: Path, trusted_inspector: Path, seed: int, profile: str
    ) -> dict:
        calls.append(binary.name)
        return {
            "ok": True,
            "correctness_ok": True,
            "_wall_seconds": 1.0,
            "user_put_bytes": 1 << 30,
            "drain_compaction_bytes": 0,
            "trusted_compaction_output_bytes": 0,
            "trusted_upper_level_files": 0,
            "table_created_bytes": 2 << 30,
            "l0_trigger": 4,
            "column_families": 1,
            "pre_drain_pending_compaction_bytes": 0,
            "pre_drain_l0_files": 2,
            "pre_drain_l0_files_by_cf": [2],
            "lsm_waf": 2.0,
            "read_amp": 1.5,
            "pre_drain_space_amp": 1.2,
            "stall_micros": 0,
            "intra_l0_compactions": 1,
            "base_fingerprint": 123,
        }

    monkeypatch.setattr(EVALUATOR, "_run_harness", fake_run)
    monkeypatch.delenv("FRONTIER_SUBMISSION_ROLE", raising=False)
    result = EVALUATOR._paired_case(
        Path("vanilla"), Path("candidate"), 1202, "l0_pressure"
    )
    assert result["ok"]
    assert sorted(calls) == ["candidate", "vanilla"]


def test_debt_uses_measured_drain_output() -> None:
    base = {
        "user_put_bytes": 1 << 30,
        "drain_compaction_bytes": 0,
        "trusted_compaction_output_bytes": 1 << 28,
        "table_created_bytes": 2 << 30,
        "l0_trigger": 4,
        "column_families": 1,
        "pre_drain_pending_compaction_bytes": 0,
        "pre_drain_l0_files": 4,
        "pre_drain_l0_files_by_cf": [4],
        "pre_drain_level_files": [4, 1, 1, 1, 1, 1],
        "lsm_waf": 2.0,
        "read_amp": 1.5,
        "pre_drain_space_amp": 1.2,
        "stall_micros": 1000,
    }
    moved = dict(base)
    moved["pre_drain_l0_files"] = 3
    moved["pre_drain_l0_files_by_cf"] = [3]
    moved["pre_drain_level_files"] = [3, 2, 1, 1, 1, 1]
    assert EVALUATOR._objective_metrics(base)["debt"] == EVALUATOR._objective_metrics(
        moved
    )["debt"]


def test_more_drain_output_increases_debt() -> None:
    low = {
        "user_put_bytes": 1 << 30,
        "drain_compaction_bytes": 0,
        "trusted_compaction_output_bytes": 1 << 27,
        "table_created_bytes": 2 << 30,
        "l0_trigger": 4,
        "column_families": 3,
        "pre_drain_pending_compaction_bytes": 0,
        "pre_drain_l0_files": 12,
        "pre_drain_l0_files_by_cf": [12, 0, 0],
        "lsm_waf": 2.0,
        "read_amp": 1.5,
        "pre_drain_space_amp": 1.2,
    }
    high = dict(low)
    high["trusted_compaction_output_bytes"] = 1 << 29
    assert EVALUATOR._objective_metrics(high)["debt"] > EVALUATOR._objective_metrics(
        low
    )["debt"]


def test_debt_cost_has_explicit_neutral_point_and_scale() -> None:
    run = {
        "user_put_bytes": 1 << 30,
        "drain_compaction_bytes": 0,
        "trusted_compaction_output_bytes": 0,
        "table_created_bytes": 2 << 30,
        "read_amp": 1.5,
        "pre_drain_space_amp": 1.2,
    }
    assert EVALUATOR._objective_metrics(run)["debt"] == 1.0
    run["trusted_compaction_output_bytes"] = 1 << 28
    assert EVALUATOR._objective_metrics(run)["debt"] == 1.25


def test_debt_cost_uses_64_mib_denominator_floor() -> None:
    run = {
        "user_put_bytes": 1 << 25,
        "drain_compaction_bytes": 0,
        "trusted_compaction_output_bytes": 1 << 26,
        "table_created_bytes": 1 << 27,
        "read_amp": 1.5,
        "pre_drain_space_amp": 1.2,
    }
    assert EVALUATOR._objective_metrics(run)["debt"] == 2.0


def test_debt_pair_ratio_is_total_cost_ratio() -> None:
    base = {
        "user_put_bytes": 1 << 30,
        "drain_compaction_bytes": 0,
        "table_created_bytes": 2 << 30,
        "read_amp": 1.5,
        "pre_drain_space_amp": 1.2,
    }
    vanilla = dict(base, trusted_compaction_output_bytes=1 << 26)
    candidate = dict(base, trusted_compaction_output_bytes=3 << 26)
    ratio = EVALUATOR._objective_metrics(vanilla)["debt"] / EVALUATOR._objective_metrics(
        candidate
    )["debt"]
    assert abs(ratio - 17 / 19) < 1e-12


def test_observed_overlap_debt_regression_is_not_catastrophic() -> None:
    base = {
        "user_put_bytes": 187_597_280,
        "drain_compaction_bytes": 0,
        "table_created_bytes": 400_000_000,
        "read_amp": 1.5,
        "pre_drain_space_amp": 1.2,
    }
    vanilla = dict(base, trusted_compaction_output_bytes=11_740_781)
    candidate = dict(base, trusted_compaction_output_bytes=35_169_986)
    ratio = EVALUATOR._objective_metrics(vanilla)["debt"] / EVALUATOR._objective_metrics(
        candidate
    )["debt"]
    assert abs(ratio - 0.8948265361) < 1e-9
    assert ratio > 0.80


def test_harness_uses_quiescent_scoring_boundaries() -> None:
    harness = (PROBLEM_DIR / "judge" / "harness" / "lsm_policy_harness.cc").read_text()
    assert 'listener->Reset();' in harness
    assert 'options.statistics->Reset()' in harness
    assert 'PauseBackgroundWork()' in harness
    assert 'GetAllColumnFamilyMetaData' in harness
    assert '--trusted-residual' in harness
    assert 'db->EnableAutoCompaction(handles)' in harness
    assert 'trusted-residual-did-not-converge' in harness
    assert 'CollectDataDigest' in harness
    assert 'SpaceSampler' not in harness


def test_judge_image_uses_a_verified_source_archive() -> None:
    dockerfile = (PROBLEM_DIR / "docker" / "judge" / "Dockerfile").read_text()
    assert "9469e7d24644e298134d0464ec2d398a9b91cc401102009ec1ecde0383485d6c" in dockerfile
    assert "codeload.github.com/facebook/rocksdb/tar.gz/{commit}" in dockerfile
    assert ".frontier-upstream-commit" in dockerfile
    assert "hashlib.sha256(archive).hexdigest()" in dockerfile
    assert "git clone" not in dockerfile
    assert EVALUATOR.SOURCE_COMMIT_MARKER == ".frontier-upstream-commit"
