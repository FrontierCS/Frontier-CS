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
