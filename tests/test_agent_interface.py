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
import tempfile
from pathlib import Path


def test_build_agent_prompt():
    """Agent prompt includes problem dir and key instructions."""
    from frontier_cs.gen.agent_interface import build_agent_prompt

    prompt = build_agent_prompt("/tmp/fake_problem")
    assert "/tmp/fake_problem" in prompt
    assert "statement.txt" in prompt
    assert "testdata/" in prompt
    assert "hidden test suite" in prompt
    assert "solution.cpp" in prompt


def test_extract_cpp_from_workdir():
    """Extract solution.cpp from agent working directory."""
    from frontier_cs.gen.agent_interface import extract_solution_cpp

    with tempfile.TemporaryDirectory() as tmpdir:
        sol_path = Path(tmpdir) / "solution.cpp"
        sol_path.write_text('#include <iostream>\nint main() { return 0; }')
        code = extract_solution_cpp(Path(tmpdir))
        assert "#include <iostream>" in code


def test_extract_cpp_missing():
    """Return empty string if no solution.cpp found."""
    from frontier_cs.gen.agent_interface import extract_solution_cpp

    with tempfile.TemporaryDirectory() as tmpdir:
        code = extract_solution_cpp(Path(tmpdir))
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
    )
    assert meta["tokens_in"] == 100000
    assert meta["tokens_out"] == 25000
    assert meta["cost_usd"] == 5.50
    assert meta["time_seconds"] == 300.5
    assert meta["turns"] == 15
    assert meta["status"] == "success"
