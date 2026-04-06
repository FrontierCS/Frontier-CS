"""Agent-based solution generation using Claude Agent SDK.

This module handles the full agent lifecycle for solving competitive programming
problems: prompt construction, Agent SDK invocation with streaming, JSONL transcript
logging, live monitoring, timeout/cost control, and solution extraction.

Agent models are identified by a "-agent" suffix (e.g., "claude-opus-4-6-agent").
They are treated as distinct "models" in the gen pipeline — no special routing needed
downstream.
"""

import asyncio
import json
import logging
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# Default budget limits
DEFAULT_COST_LIMIT_USD = 20.0
DEFAULT_TIMEOUT_SECONDS = 1200  # 20 minutes


def build_agent_prompt(problem_dir: str) -> str:
    """Construct the prompt given to the agent.

    Args:
        problem_dir: Absolute path to the problem directory.

    Returns:
        The prompt string for the agent.
    """
    return f"""You are solving a competitive programming problem.

Problem directory: {problem_dir}
- Read statement.txt for the problem description
- testdata/ contains sample test cases (*.in, *.ans), but these are only a subset
- Your solution will be evaluated against a larger hidden test suite
- You can compile with g++, run against the available samples, and iterate
- config.yaml has time/memory limits — respect them in your solution

Submit your final solution as solution.cpp in the current working directory."""


def extract_solution_cpp(workdir: Path) -> str:
    """Extract solution.cpp from the agent working directory.

    Looks for solution.cpp first, then falls back to any .cpp file.

    Args:
        workdir: The agent's working directory.

    Returns:
        The C++ source code, or empty string if not found.
    """
    # Primary: solution.cpp
    sol = workdir / "solution.cpp"
    if sol.is_file():
        return sol.read_text(encoding="utf-8")

    # Fallback: any .cpp file (agent might have used a different name)
    cpp_files = list(workdir.glob("*.cpp"))
    if cpp_files:
        # Pick the most recently modified one
        newest = max(cpp_files, key=lambda p: p.stat().st_mtime)
        return newest.read_text(encoding="utf-8")

    return ""


def build_metadata(
    *,
    tokens_in: int,
    tokens_out: int,
    cost_usd: float,
    time_seconds: float,
    turns: int,
    status: str,
) -> Dict[str, Any]:
    """Build the metadata dict for an agent run.

    Args:
        tokens_in: Total input tokens consumed.
        tokens_out: Total output tokens consumed.
        cost_usd: Total cost in USD.
        time_seconds: Wall-clock time in seconds.
        turns: Number of agentic turns (tool-use round trips).
        status: One of "success", "timeout", "cost_limit", "error".

    Returns:
        Metadata dictionary.
    """
    return {
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "cost_usd": round(cost_usd, 4),
        "time_seconds": round(time_seconds, 2),
        "turns": turns,
        "status": status,
    }


@dataclass
class TranscriptLogger:
    """Writes JSONL transcript of agent events, flushed per event."""

    path: Path
    _file: Any = field(default=None, init=False, repr=False)

    def open(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._file = open(self.path, "w", encoding="utf-8")

    def log(self, event: Dict[str, Any]) -> None:
        if self._file is None:
            return
        event["_ts"] = time.time()
        self._file.write(json.dumps(event, default=str) + "\n")
        self._file.flush()

    def close(self) -> None:
        if self._file is not None:
            self._file.close()
            self._file = None


async def run_agent(
    problem_dir: str,
    model: str,
    *,
    cost_limit: float = DEFAULT_COST_LIMIT_USD,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    transcript_path: Optional[Path] = None,
) -> Tuple[str, Dict[str, Any]]:
    """Run the agent to solve a problem.

    Args:
        problem_dir: Absolute path to the problem directory.
        model: Base model name (without -agent suffix).
        cost_limit: Maximum cost in USD.
        timeout: Maximum wall-clock time in seconds.
        transcript_path: Path for JSONL transcript log. None to skip.

    Returns:
        Tuple of (cpp_code, metadata_dict).
    """
    from claude_agent_sdk import query, ClaudeAgentOptions
    from claude_agent_sdk.types import StreamEvent

    prompt = build_agent_prompt(problem_dir)
    workdir = Path(problem_dir)

    options = ClaudeAgentOptions(
        model=model,
        cwd=str(workdir),
        max_budget_usd=cost_limit,
        permission_mode="bypassPermissions",
        include_partial_messages=True,
    )

    # Set up transcript logging
    transcript = TranscriptLogger(transcript_path) if transcript_path else None
    if transcript:
        transcript.open()

    start_time = time.time()
    status = "success"
    num_turns = 0
    total_cost: Optional[float] = None
    usage_in = 0
    usage_out = 0

    try:
        async def _run():
            nonlocal num_turns, total_cost, usage_in, usage_out

            async for message in query(prompt=prompt, options=options):
                # Import here to check types
                from claude_agent_sdk import AssistantMessage, ResultMessage

                if isinstance(message, StreamEvent):
                    event = message.event
                    event_type = event.get("type", "")

                    # Log every event
                    if transcript:
                        transcript.log({"type": "stream_event", "event": event})

                    # Live monitoring: tool calls
                    if event_type == "content_block_start":
                        cb = event.get("content_block", {})
                        if cb.get("type") == "tool_use":
                            tool = cb.get("name", "?")
                            elapsed = time.time() - start_time
                            print(
                                f"  [{elapsed:6.1f}s] [turn {num_turns}] {tool}",
                                flush=True,
                            )

                elif isinstance(message, AssistantMessage):
                    num_turns += 1
                    if transcript:
                        tools_used = [
                            b.name
                            for b in message.content
                            if hasattr(b, "name")
                        ]
                        transcript.log({
                            "type": "assistant_turn",
                            "turn": num_turns,
                            "tools": tools_used,
                            "model": message.model,
                        })

                    # Per-message usage tracking
                    if message.usage:
                        usage_in += message.usage.get("input_tokens", 0)
                        usage_out += message.usage.get("output_tokens", 0)

                    # Periodic cost summary to stderr
                    elapsed = time.time() - start_time
                    print(
                        f"  [{elapsed:6.1f}s] turn {num_turns}, "
                        f"{usage_in // 1000}K in / {usage_out // 1000}K out",
                        file=sys.stderr,
                        flush=True,
                    )

                elif isinstance(message, ResultMessage):
                    total_cost = message.total_cost_usd
                    if message.usage:
                        usage_in = message.usage.get("input_tokens", usage_in)
                        usage_out = message.usage.get("output_tokens", usage_out)
                    num_turns = message.num_turns
                    if transcript:
                        transcript.log({
                            "type": "result",
                            "cost_usd": total_cost,
                            "num_turns": num_turns,
                            "duration_ms": message.duration_ms,
                            "stop_reason": message.stop_reason,
                            "is_error": message.is_error,
                        })

        await asyncio.wait_for(_run(), timeout=timeout)

    except asyncio.TimeoutError:
        status = "timeout"
        logger.warning("Agent timed out after %.0fs", timeout)
    except Exception as e:
        status = "error"
        logger.error("Agent error: %s", e)
        if transcript:
            transcript.log({"type": "error", "error": str(e)})
    finally:
        if transcript:
            transcript.close()

    elapsed = time.time() - start_time

    # Extract solution (best-effort even on timeout/error)
    code = extract_solution_cpp(workdir)
    if not code and status == "success":
        status = "error"
        logger.error("Agent completed but no .cpp file found in %s", workdir)

    metadata = build_metadata(
        tokens_in=usage_in,
        tokens_out=usage_out,
        cost_usd=total_cost if total_cost is not None else 0.0,
        time_seconds=elapsed,
        turns=num_turns,
        status=status,
    )

    return code, metadata


def generate_agent_solution(
    problem_dir: str,
    model: str,
    *,
    cost_limit: float = DEFAULT_COST_LIMIT_USD,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    transcript_path: Optional[Path] = None,
) -> Tuple[str, Dict[str, Any]]:
    """Synchronous wrapper for run_agent.

    This is the main entry point called from generate_solutions.py.

    Args:
        problem_dir: Absolute path to the problem directory.
        model: Base model name (without -agent suffix).
        cost_limit: Maximum cost in USD.
        timeout: Maximum wall-clock time in seconds.
        transcript_path: Path for JSONL transcript log.

    Returns:
        Tuple of (cpp_code, metadata_dict).
    """
    return asyncio.run(
        run_agent(
            problem_dir,
            model,
            cost_limit=cost_limit,
            timeout=timeout,
            transcript_path=transcript_path,
        )
    )
