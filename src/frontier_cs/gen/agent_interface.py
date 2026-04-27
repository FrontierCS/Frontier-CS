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
import os
import shutil
import stat
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from frontier_cs.gen.agent_constants import (
    CLAUDE_MD_FULL_ACCESS,
    CLAUDE_MD_PARITY,
    CLAUDE_MD_PARITY_INTERACTIVE_ADDENDUM,
    FULL_ACCESS_INTERACTIVE_SECTION,
    FULL_ACCESS_PROMPT,
    FULL_ACCESS_STANDARD_SECTION,
    FULL_ACCESS_TAIL,
    PARITY_INTERACTIVE_SECTION,
    PARITY_PROMPT,
    PARITY_SPJ_SECTION,
    PARITY_STANDARD_SECTION,
    PARITY_TAIL,
    RUN_INTERACTIVE_SH,
    TEST_ALL_SH,
)

logger = logging.getLogger(__name__)

# Default budget limits — aligned with Harbor adapter (task.toml agent.timeout_sec=10800)
DEFAULT_COST_LIMIT_USD = None  # None = no limit; Harbor relies on timeout, not cost cap
DEFAULT_TIMEOUT_SECONDS = 10800  # 3 hours, matching Harbor

# Max size of sample I/O to embed directly in the prompt (bytes).
# Larger inputs are left for the agent to read from disk.
_MAX_EMBED_SIZE = 4096


def _read_problem_config(problem_dir: str) -> Dict[str, Any]:
    """Read and parse config.yaml from a problem directory."""
    config_path = Path(problem_dir) / "config.yaml"
    if config_path.is_file():
        return yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    return {}


def _collect_samples(problem_dir: str) -> List[Dict[str, str]]:
    """Collect sample test cases from testdata/, sorted by number.

    Returns list of dicts with keys 'id', 'input', 'answer'.
    Only includes samples where both .in and .ans exist and are small enough to embed.
    """
    testdata = Path(problem_dir) / "testdata"
    if not testdata.is_dir():
        return []

    samples = []
    in_files = sorted(testdata.glob("*.in"), key=lambda p: int(p.stem) if p.stem.isdigit() else 0)
    for in_file in in_files:
        ans_file = in_file.with_suffix(".ans")
        if not ans_file.is_file():
            continue
        if in_file.stat().st_size > _MAX_EMBED_SIZE or ans_file.stat().st_size > _MAX_EMBED_SIZE:
            continue
        samples.append({
            "id": in_file.stem,
            "input": in_file.read_text(encoding="utf-8"),
            "answer": ans_file.read_text(encoding="utf-8"),
        })
    return samples


def _format_samples(samples: List[Dict[str, str]], is_interactive: bool) -> str:
    """Format sample test cases for inclusion in the prompt."""
    if not samples:
        return ""
    parts = ["\n## Sample test cases (embedded for convenience)\n"]
    note = " (interactor judge input — NOT your stdin)" if is_interactive else ""
    for s in samples:
        parts.append(f"### Sample {s['id']}{note}")
        parts.append(f"Input:\n```\n{s['input'].rstrip()}\n```")
        parts.append(f"Expected output:\n```\n{s['answer'].rstrip()}\n```\n")
    return "\n".join(parts)




def build_agent_prompt(problem_dir: str, *, parity: bool = True) -> str:
    """Construct a problem-aware prompt for the agent.

    Reads config.yaml to detect problem type (interactive vs standard, SPJ),
    embeds small sample I/O directly, and provides tailored workflow guidance.

    In parity mode, no test data or helper scripts are referenced — the agent
    must write its own tests. This matches the Harbor adapter setup.

    Args:
        problem_dir: Absolute path to the problem directory.
        parity: If True, build a prompt that assumes no test data or scripts.

    Returns:
        The prompt string for the agent.
    """
    config = _read_problem_config(problem_dir)
    is_interactive = config.get("type") == "interactive"
    has_checker = "checker" in config
    time_limit = config.get("time", "?")
    memory_limit = config.get("memory", "?")
    subtasks = config.get("subtasks", [])
    total_cases = sum(s.get("n_cases", 0) for s in subtasks) if subtasks else "?"

    if parity:
        return _build_parity_prompt(
            problem_dir, config, is_interactive, has_checker,
            time_limit, memory_limit, total_cases,
        )

    samples = _collect_samples(problem_dir)

    parts = [FULL_ACCESS_PROMPT.format(
        problem_dir=problem_dir, time_limit=time_limit,
        memory_limit=memory_limit, total_cases=total_cases,
    )]

    if is_interactive:
        parts.append(FULL_ACCESS_INTERACTIVE_SECTION)
    else:
        checker_note = ""
        if has_checker:
            checker_note = ("\nNote: This problem has a SPECIAL JUDGE (chk.cc) — "
                           "multiple valid outputs may be accepted.")
        problem_type = "SPECIAL JUDGE (multiple valid outputs accepted)" if has_checker else "STANDARD"
        parts.append(FULL_ACCESS_STANDARD_SECTION.format(
            problem_type=problem_type, checker_note=checker_note,
        ))

    sample_text = _format_samples(samples, is_interactive)
    if sample_text:
        parts.append(sample_text)
    elif samples:
        parts.append("\n(Sample inputs are large — read them from testdata/ directory.)\n")

    parts.append(FULL_ACCESS_TAIL)

    return "\n".join(parts)


def _build_parity_prompt(
    problem_dir: str,
    config: Dict[str, Any],
    is_interactive: bool,
    has_checker: bool,
    time_limit: str,
    memory_limit: str,
    total_cases: Any,
) -> str:
    """Build a prompt for parity mode (no test data, no helper scripts).

    Matches the Harbor adapter setup: agent gets only the problem statement
    and must write its own tests.
    """
    parts = [PARITY_PROMPT.format(
        problem_dir=problem_dir, time_limit=time_limit,
        memory_limit=memory_limit, total_cases=total_cases,
    )]

    if is_interactive:
        parts.append(PARITY_INTERACTIVE_SECTION)
    elif has_checker:
        parts.append(PARITY_SPJ_SECTION)
    else:
        parts.append(PARITY_STANDARD_SECTION)

    parts.append(PARITY_TAIL)

    return "\n".join(parts)


def _write_helper_scripts(workdir: Path, is_interactive: bool) -> None:
    """Write test helper scripts to the agent's working directory."""
    test_all = workdir / "test_all.sh"
    test_all.write_text(TEST_ALL_SH, encoding="utf-8")
    test_all.chmod(test_all.stat().st_mode | stat.S_IEXEC)

    if is_interactive:
        run_inter = workdir / "run_interactive.sh"
        run_inter.write_text(RUN_INTERACTIVE_SH, encoding="utf-8")
        run_inter.chmod(run_inter.stat().st_mode | stat.S_IEXEC)


def _write_workdir_claude_md(workdir: Path, is_interactive: bool, *, parity: bool = True) -> None:
    """Write a CLAUDE.md to the workdir so Claude Code picks up behavioral guidance."""
    if parity:
        content = CLAUDE_MD_PARITY
        if is_interactive:
            content += CLAUDE_MD_PARITY_INTERACTIVE_ADDENDUM
    else:
        content = CLAUDE_MD_FULL_ACCESS
    (workdir / "CLAUDE.md").write_text(content, encoding="utf-8")


def extract_solution_cpp(workdir: Path) -> str:
    """Extract solution.cpp from the agent working directory.

    Searches for solution.cpp in the workdir, its parent (the tmpdir root),
    and recursively. Falls back to any .cpp file that looks like a solution.

    Args:
        workdir: The agent's working directory (typically tmpdir/problem).

    Returns:
        The C++ source code, or empty string if not found.
    """
    # Search these directories in priority order
    search_dirs = [workdir, workdir.parent]

    for d in search_dirs:
        sol = d / "solution.cpp"
        if sol.is_file():
            return sol.read_text(encoding="utf-8")

    # Fallback: any .cpp file in workdir or parent (excluding problem-provided files)
    problem_files = {p.name for p in workdir.glob("**/*.cpp")
                     if p.stat().st_mtime < workdir.stat().st_mtime}
    for d in search_dirs:
        cpp_files = [
            p for p in d.glob("*.cpp")
            if p.name not in problem_files and p.name != "chk.cc"
        ]
        if cpp_files:
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
    model: str,
    prompt: str,
) -> Dict[str, Any]:
    """Build the metadata dict for an agent run.

    Args:
        tokens_in: Total input tokens consumed.
        tokens_out: Total output tokens consumed.
        cost_usd: Total cost in USD.
        time_seconds: Wall-clock time in seconds.
        turns: Number of agentic turns (tool-use round trips).
        status: One of "success", "timeout", "cost_limit", "error".
        model: The model name passed to the agent SDK.
        prompt: The full prompt sent to the agent.

    Returns:
        Metadata dictionary.
    """
    return {
        "model": model,
        "prompt": prompt,
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
    api_key: Optional[str] = None,
    cost_limit: Optional[float] = DEFAULT_COST_LIMIT_USD,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    transcript_path: Optional[Path] = None,
    parity: bool = True,
) -> Tuple[str, Dict[str, Any]]:
    """Run the agent to solve a problem.

    Args:
        problem_dir: Absolute path to the problem directory.
        model: Base model name (without -agent suffix).
        api_key: Anthropic API key. If provided, passed to the SDK subprocess
            via env (per-run), allowing pool-managed key rotation. If None,
            the SDK falls back to inheriting ANTHROPIC_API_KEY from the parent.
        cost_limit: Maximum cost in USD. None = no limit.
        timeout: Maximum wall-clock time in seconds.
        transcript_path: Path for JSONL transcript log. None to skip.
        parity: If True, strip test data and helper scripts (Harbor parity mode).

    Returns:
        Tuple of (cpp_code, metadata_dict).
    """
    from claude_agent_sdk import query, ClaudeAgentOptions
    from claude_agent_sdk.types import StreamEvent

    # Claude Code CLI uses short model names, not full API model IDs.
    # Map common API IDs to CLI-accepted names.
    CLI_MODEL_MAP = {
        "claude-sonnet-4-5-20250514": "claude-sonnet-4-5",
        "claude-sonnet-4-6-20250610": "claude-sonnet-4-6",
        "claude-opus-4-6-20250610": "claude-opus-4-6",
        "claude-haiku-4-5-20251001": "claude-haiku-4-5",
    }
    model = CLI_MODEL_MAP.get(model, model)

    # Read problem config before copying to detect type.
    config = _read_problem_config(problem_dir)
    is_interactive = config.get("type") == "interactive"

    # Copy problem dir to a temp working directory to avoid polluting the original.
    # This also makes concurrent runs on the same problem safe.
    tmpdir = tempfile.mkdtemp(prefix="agent_eval_")
    workdir = Path(tmpdir) / "problem"

    if parity:
        # Parity mode: only copy statement.txt and config.yaml — no test data,
        # no checker, no interactor. Agent must self-test.
        workdir.mkdir(parents=True)
        for fname in ("statement.txt", "config.yaml", "tag.txt"):
            src = Path(problem_dir) / fname
            if src.is_file():
                shutil.copy2(src, workdir / fname)
    else:
        shutil.copytree(problem_dir, workdir)
        # Provide testlib.h so agents can compile interactors/checkers for local testing.
        testlib_src = Path(problem_dir).parent.parent / "judge" / "include" / "testlib.h"
        if testlib_src.is_file():
            shutil.copy2(testlib_src, workdir / "testlib.h")
        # Write helper scripts for local testing.
        _write_helper_scripts(workdir, is_interactive)

    _write_workdir_claude_md(workdir, is_interactive, parity=parity)

    prompt = build_agent_prompt(str(workdir), parity=parity)

    sdk_env: Dict[str, str] = {}
    if api_key:
        sdk_env["ANTHROPIC_API_KEY"] = api_key

    options = ClaudeAgentOptions(
        model=model,
        cwd=str(workdir),
        env=sdk_env,
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

                    # Track token usage from streaming message_delta events.
                    # This is the only reliable source when timeout kills
                    # the run before ResultMessage arrives.
                    if event_type == "message_delta":
                        delta_usage = event.get("usage", {})
                        if delta_usage.get("output_tokens"):
                            usage_out = delta_usage["output_tokens"]

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
                        usage_in = max(usage_in, message.usage.get("input_tokens", 0))
                        usage_out = max(usage_out, message.usage.get("output_tokens", 0))
                    # SDK may send multiple ResultMessages (main run + follow-ups).
                    # Keep the highest turn count to avoid a follow-up (turns=1)
                    # clobbering the real value.
                    num_turns = max(num_turns, message.num_turns)
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
        # Claude CLI often exits with code 1 after a successful run.
        # If we already received a ResultMessage (total_cost is set),
        # treat this as a successful completion, not an error.
        if total_cost is not None:
            logger.info("Agent completed (post-result CLI exit: %s)", e)
        else:
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

    # Clean up temp directory
    shutil.rmtree(tmpdir, ignore_errors=True)

    metadata = build_metadata(
        tokens_in=usage_in,
        tokens_out=usage_out,
        cost_usd=total_cost if total_cost is not None else 0.0,
        time_seconds=elapsed,
        turns=num_turns,
        status=status,
        model=model,
        prompt=prompt,
    )

    return code, metadata


def generate_agent_solution(
    problem_dir: str,
    model: str,
    *,
    api_key: Optional[str] = None,
    cost_limit: Optional[float] = DEFAULT_COST_LIMIT_USD,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    transcript_path: Optional[Path] = None,
    parity: bool = True,
) -> Tuple[str, Dict[str, Any]]:
    """Synchronous wrapper for run_agent.

    This is the main entry point called from generate_solutions.py.

    Args:
        problem_dir: Absolute path to the problem directory.
        model: Base model name (without -agent suffix).
        api_key: Anthropic API key (passed to SDK subprocess env, per-run).
            If None, the SDK inherits ANTHROPIC_API_KEY from the parent process.
        cost_limit: Maximum cost in USD. None = no limit.
        timeout: Maximum wall-clock time in seconds.
        transcript_path: Path for JSONL transcript log.
        parity: If True, strip test data and helper scripts (Harbor parity mode).

    Returns:
        Tuple of (cpp_code, metadata_dict).
    """
    return asyncio.run(
        run_agent(
            problem_dir,
            model,
            api_key=api_key,
            cost_limit=cost_limit,
            timeout=timeout,
            transcript_path=transcript_path,
            parity=parity,
        )
    )
