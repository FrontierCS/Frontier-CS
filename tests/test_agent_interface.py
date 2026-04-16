"""Tests for agent model name handling and agent_interface."""

from frontier_cs.models import get_model_prefix, detect_provider, is_reasoning_model


def test_agent_model_prefix():
    """Agent model prefix includes 'agent' suffix."""
    assert get_model_prefix("claude-opus-4-6-agent") == "claude4.6opusagent"
    assert get_model_prefix("claude-sonnet-4-5-agent") == "claude4.5sonnetagent"


def test_agent_model_prefix_does_not_collide_with_single_shot():
    """Agent prefix must differ from single-shot prefix."""
    assert get_model_prefix("claude-opus-4-6-agent") != get_model_prefix("claude-opus-4-6")


def test_agent_detect_provider():
    """Agent models detect as anthropic provider."""
    assert detect_provider("claude-opus-4-6-agent") == "anthropic"
    assert detect_provider("claude-sonnet-4-5-agent") == "anthropic"


def test_agent_is_not_reasoning_model():
    """Agent models are not reasoning models."""
    assert is_reasoning_model("claude-opus-4-6-agent") is False


import json
import os
import tempfile
from pathlib import Path


def _make_problem_dir(tmpdir: str, *, interactive: bool = False, samples: int = 2) -> Path:
    """Create a minimal problem directory for testing."""
    pdir = Path(tmpdir) / "problems" / "0"
    pdir.mkdir(parents=True)
    (pdir / "statement.txt").write_text("# Test Problem\nSolve it.\n")

    config = {
        "type": "interactive" if interactive else "default",
        "time": "1s",
        "memory": "256m",
        "subtasks": [{"score": 100, "n_cases": 3}],
    }
    if interactive:
        config["interactor"] = "interactor.cc"
        (pdir / "interactor.cc").write_text("// interactor\n")
    else:
        config["checker"] = "chk.cc"

    import yaml
    (pdir / "config.yaml").write_text(yaml.dump(config))

    testdata = pdir / "testdata"
    testdata.mkdir()
    for i in range(1, samples + 1):
        (testdata / f"{i}.in").write_text(f"{i}\n")
        (testdata / f"{i}.ans").write_text(f"{i * 2}\n")

    # testlib.h at judge/include/ level
    judge_inc = Path(tmpdir) / "judge" / "include"
    judge_inc.mkdir(parents=True, exist_ok=True)
    (judge_inc / "testlib.h").write_text("// testlib stub\n")

    return pdir


def test_build_agent_prompt_standard():
    """Standard problem prompt includes test script and scoring info."""
    from frontier_cs.gen.agent_interface import build_agent_prompt

    with tempfile.TemporaryDirectory() as tmpdir:
        pdir = _make_problem_dir(tmpdir)
        prompt = build_agent_prompt(str(pdir), parity=False)
        assert "test_all.sh" in prompt
        assert "STANDARD" in prompt or "SPECIAL JUDGE" in prompt
        assert "partial" in prompt.lower()
        # Samples should be embedded (they're tiny)
        assert "Sample 1" in prompt


def test_build_agent_prompt_interactive():
    """Interactive problem prompt includes interactor guidance."""
    from frontier_cs.gen.agent_interface import build_agent_prompt

    with tempfile.TemporaryDirectory() as tmpdir:
        pdir = _make_problem_dir(tmpdir, interactive=True)
        prompt = build_agent_prompt(str(pdir), parity=False)
        assert "INTERACTIVE" in prompt
        assert "interactor.cc" in prompt


def test_build_agent_prompt_embeds_small_samples():
    """Small samples are embedded directly in the prompt."""
    from frontier_cs.gen.agent_interface import build_agent_prompt

    with tempfile.TemporaryDirectory() as tmpdir:
        pdir = _make_problem_dir(tmpdir, samples=2)
        prompt = build_agent_prompt(str(pdir), parity=False)
        # The sample content should appear in the prompt
        assert "Sample 1" in prompt
        assert "Sample 2" in prompt


def test_build_agent_prompt_skips_large_samples():
    """Large samples are NOT embedded in the prompt."""
    from frontier_cs.gen.agent_interface import build_agent_prompt, _MAX_EMBED_SIZE

    with tempfile.TemporaryDirectory() as tmpdir:
        pdir = _make_problem_dir(tmpdir, samples=1)
        # Make the input file larger than the embed threshold
        (pdir / "testdata" / "1.in").write_text("x" * (_MAX_EMBED_SIZE + 1))
        prompt = build_agent_prompt(str(pdir), parity=False)
        # Should NOT contain the embedded content
        assert "Sample 1" not in prompt


def test_build_agent_prompt_parity_no_test_refs():
    """Parity mode prompt has no references to test scripts or test data."""
    from frontier_cs.gen.agent_interface import build_agent_prompt

    with tempfile.TemporaryDirectory() as tmpdir:
        pdir = _make_problem_dir(tmpdir, samples=2)
        prompt = build_agent_prompt(str(pdir), parity=True)
        assert "test_all.sh" not in prompt
        assert "run_interactive.sh" not in prompt
        assert "testdata/" not in prompt
        assert "Sample 1" not in prompt
        assert "chk.cc" not in prompt
        assert "interactor.cc" not in prompt
        # Prompt is lean — delegates to CLAUDE.md
        assert "CLAUDE.md" in prompt
        assert "statement.txt" in prompt


def test_build_agent_prompt_parity_interactive():
    """Parity mode interactive prompt identifies type but delegates details to CLAUDE.md."""
    from frontier_cs.gen.agent_interface import build_agent_prompt

    with tempfile.TemporaryDirectory() as tmpdir:
        pdir = _make_problem_dir(tmpdir, interactive=True)
        prompt = build_agent_prompt(str(pdir), parity=True)
        assert "INTERACTIVE" in prompt
        assert "run_interactive.sh" not in prompt
        assert "interactor.cc" not in prompt


def test_extract_cpp_from_workdir():
    """Extract solution.cpp from agent working directory."""
    from frontier_cs.gen.agent_interface import extract_solution_cpp

    with tempfile.TemporaryDirectory() as tmpdir:
        workdir = Path(tmpdir) / "problem"
        workdir.mkdir()
        sol_path = workdir / "solution.cpp"
        sol_path.write_text('#include <iostream>\nint main() { return 0; }')
        code = extract_solution_cpp(workdir)
        assert "#include <iostream>" in code


def test_extract_cpp_from_parent():
    """Extract solution.cpp when agent writes it to tmpdir root instead of workdir."""
    from frontier_cs.gen.agent_interface import extract_solution_cpp

    with tempfile.TemporaryDirectory() as tmpdir:
        workdir = Path(tmpdir) / "problem"
        workdir.mkdir()
        # Agent wrote solution.cpp in the parent (tmpdir), not in workdir
        sol_path = Path(tmpdir) / "solution.cpp"
        sol_path.write_text('#include <cstdio>\nint main() {}')
        code = extract_solution_cpp(workdir)
        assert "#include <cstdio>" in code


def test_extract_cpp_missing():
    """Return empty string if no solution.cpp found."""
    from frontier_cs.gen.agent_interface import extract_solution_cpp

    with tempfile.TemporaryDirectory() as tmpdir:
        # Use a nested dir to mimic real layout (tmpdir/problem) and avoid
        # picking up stray .cpp files from the system /tmp.
        workdir = Path(tmpdir) / "problem"
        workdir.mkdir()
        code = extract_solution_cpp(workdir)
        assert code == ""


def test_build_metadata():
    """Build metadata dict from agent run results."""
    from frontier_cs.gen.agent_interface import build_metadata

    meta = build_metadata(
        tokens_in=100000,
        tokens_out=25000,
        cost_usd=5.50,
        time_seconds=300.5,
        turns=15,
        status="success",
        model="claude-sonnet-4-5",
        prompt="You are solving a competitive programming problem.",
    )
    assert meta["tokens_in"] == 100000
    assert meta["tokens_out"] == 25000
    assert meta["cost_usd"] == 5.50
    assert meta["time_seconds"] == 300.5
    assert meta["turns"] == 15
    assert meta["status"] == "success"
    assert meta["model"] == "claude-sonnet-4-5"
    assert meta["prompt"] == "You are solving a competitive programming problem."


def test_write_helper_scripts_standard():
    """Standard problem gets test_all.sh but not run_interactive.sh."""
    from frontier_cs.gen.agent_interface import _write_helper_scripts

    with tempfile.TemporaryDirectory() as tmpdir:
        workdir = Path(tmpdir)
        _write_helper_scripts(workdir, is_interactive=False)
        assert (workdir / "test_all.sh").is_file()
        assert os.access(workdir / "test_all.sh", os.X_OK)
        assert not (workdir / "run_interactive.sh").is_file()


def test_write_helper_scripts_interactive():
    """Interactive problem gets both scripts."""
    from frontier_cs.gen.agent_interface import _write_helper_scripts

    with tempfile.TemporaryDirectory() as tmpdir:
        workdir = Path(tmpdir)
        _write_helper_scripts(workdir, is_interactive=True)
        assert (workdir / "test_all.sh").is_file()
        assert (workdir / "run_interactive.sh").is_file()
        assert os.access(workdir / "run_interactive.sh", os.X_OK)


def test_write_workdir_claude_md_standard():
    """CLAUDE.md for standard problems mentions test_all.sh."""
    from frontier_cs.gen.agent_interface import _write_workdir_claude_md

    with tempfile.TemporaryDirectory() as tmpdir:
        workdir = Path(tmpdir)
        _write_workdir_claude_md(workdir, is_interactive=False, parity=False)
        content = (workdir / "CLAUDE.md").read_text()
        assert "test_all.sh" in content
        assert "solution.cpp" in content


def test_write_workdir_claude_md_interactive():
    """CLAUDE.md for interactive problems mentions flush."""
    from frontier_cs.gen.agent_interface import _write_workdir_claude_md

    with tempfile.TemporaryDirectory() as tmpdir:
        workdir = Path(tmpdir)
        _write_workdir_claude_md(workdir, is_interactive=True, parity=False)
        content = (workdir / "CLAUDE.md").read_text()
        assert "flush" in content


def test_write_workdir_claude_md_parity():
    """Parity CLAUDE.md has self-testing guidance, no test script refs."""
    from frontier_cs.gen.agent_interface import _write_workdir_claude_md

    with tempfile.TemporaryDirectory() as tmpdir:
        workdir = Path(tmpdir)
        _write_workdir_claude_md(workdir, is_interactive=False, parity=True)
        content = (workdir / "CLAUDE.md").read_text()
        assert "brute-force" in content.lower() or "brute force" in content.lower()
        assert "solution.cpp" in content
        assert "test_all.sh" not in content
        assert "run_interactive.sh" not in content


def test_write_workdir_claude_md_parity_interactive():
    """Parity interactive CLAUDE.md has flush guidance."""
    from frontier_cs.gen.agent_interface import _write_workdir_claude_md

    with tempfile.TemporaryDirectory() as tmpdir:
        workdir = Path(tmpdir)
        _write_workdir_claude_md(workdir, is_interactive=True, parity=True)
        content = (workdir / "CLAUDE.md").read_text()
        assert "flush" in content
        assert "run_interactive.sh" not in content
