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

logger = logging.getLogger(__name__)

# Default budget limits
DEFAULT_COST_LIMIT_USD = 20.0
DEFAULT_TIMEOUT_SECONDS = 1200  # 20 minutes

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


# Shell script: compile solution.cpp and test against all sample cases.
# If chk.cc exists (special judge), uses it for verification instead of diff.
_TEST_ALL_SH = r"""#!/bin/bash
set -e
echo "=== Compiling solution.cpp ==="
g++ -std=gnu++17 -O2 -o solution solution.cpp
echo "=== Compilation OK ==="

# Compile checker if available (special judge)
USE_CHECKER=0
if [ -f "chk.cc" ]; then
    echo "=== Compiling special judge (chk.cc) ==="
    if g++ -std=gnu++17 -O2 -I. chk.cc -o checker 2>/dev/null; then
        USE_CHECKER=1
        echo "=== Checker compiled OK — using it instead of diff ==="
    else
        echo "=== Checker compilation failed — falling back to diff ==="
    fi
fi

passed=0; failed=0; total=0
for inf in testdata/*.in; do
    [ -f "$inf" ] || continue
    id=$(basename "$inf" .in)
    ans="testdata/${id}.ans"
    [ -f "$ans" ] || continue
    total=$((total + 1))

    # Run with timeout
    if timeout 15 ./solution < "$inf" > "my_${id}.out" 2>"my_${id}.err"; then
        if [ "$USE_CHECKER" -eq 1 ]; then
            # Special judge: ./checker <input> <output> <answer>
            checker_out=$(./checker "$inf" "my_${id}.out" "$ans" 2>&1) && chk_rc=$? || chk_rc=$?
            if [ $chk_rc -eq 0 ]; then
                echo "  Sample $id: PASS (checker: $checker_out)"
                passed=$((passed + 1))
            else
                echo "  Sample $id: WRONG ANSWER (checker exit $chk_rc)"
                echo "    Checker output: $checker_out"
                failed=$((failed + 1))
            fi
        else
            # Diff-based comparison (normalize whitespace)
            if diff -q <(tr -s '[:space:]' '\n' < "my_${id}.out" | sed '/^$/d') \
                        <(tr -s '[:space:]' '\n' < "$ans" | sed '/^$/d') >/dev/null 2>&1; then
                echo "  Sample $id: PASS"
                passed=$((passed + 1))
            else
                echo "  Sample $id: WRONG ANSWER"
                echo "    Expected (first 5 lines):"
                head -5 "$ans" | sed 's/^/      /'
                echo "    Got (first 5 lines):"
                head -5 "my_${id}.out" | sed 's/^/      /'
                failed=$((failed + 1))
            fi
        fi
    else
        rc=$?
        echo "  Sample $id: RUNTIME ERROR or TLE (exit $rc)"
        [ -s "my_${id}.err" ] && head -3 "my_${id}.err" | sed 's/^/    stderr: /'
        failed=$((failed + 1))
    fi
done

echo "=== Results: $passed/$total passed ==="
[ "$failed" -eq 0 ] && exit 0 || exit 1
"""

# Shell script: test solution against an interactor using named pipes.
_RUN_INTERACTIVE_SH = r"""#!/bin/bash
# Usage: ./run_interactive.sh [sample_id]  (default: 1)
# Compiles solution.cpp and interactor.cc, then tests via pipe.
# Exit codes: 0=accepted, 1=wrong answer, 2=presentation error, 3=build error, 4=timeout/crash

SAMPLE=${1:-1}
INF="testdata/${SAMPLE}.in"
ANSF="testdata/${SAMPLE}.ans"

if [ ! -f "$INF" ]; then
    echo "Error: $INF not found"
    exit 3
fi

# Compile only if binaries are missing or sources are newer
if [ ! -f ./solution ] || [ solution.cpp -nt ./solution ]; then
    echo "=== Compiling solution.cpp ==="
    g++ -std=gnu++17 -O2 -o solution solution.cpp || { echo "Compilation failed"; exit 3; }
fi

if [ ! -f ./interactor ] || [ interactor.cc -nt ./interactor ]; then
    echo "=== Compiling interactor ==="
    g++ -std=gnu++17 -O2 -I. interactor.cc -o interactor || { echo "Interactor compilation failed"; exit 3; }
fi

# Create named pipes in current dir (avoids /tmp permission issues)
PIPE_S2I=".pipe_s2i_$$"
PIPE_I2S=".pipe_i2s_$$"
rm -f "$PIPE_S2I" "$PIPE_I2S"
mkfifo "$PIPE_S2I" "$PIPE_I2S"

cleanup() { rm -f "$PIPE_S2I" "$PIPE_I2S" inter_stderr.tmp sol_stderr.tmp; }
trap cleanup EXIT

echo "=== Running sample $SAMPLE ==="

# interactor: reads from solution's stdout via pipe, writes to solution's stdin via pipe
# testlib interactors: argv = <inf> <ouf> [ans]
# We use /dev/null for ouf (output file) since we only care about exit code
timeout 120 ./interactor "$INF" /dev/null "$ANSF" < "$PIPE_S2I" > "$PIPE_I2S" 2>inter_stderr.tmp &
INTER_PID=$!

timeout 120 ./solution < "$PIPE_I2S" > "$PIPE_S2I" 2>sol_stderr.tmp &
SOL_PID=$!

# Wait for both processes
INTER_EXIT=0; SOL_EXIT=0
wait $INTER_PID 2>/dev/null || INTER_EXIT=$?
wait $SOL_PID 2>/dev/null || SOL_EXIT=$?

# Report results
if [ $INTER_EXIT -eq 0 ]; then
    echo "  Sample $SAMPLE: ACCEPTED (interactor exit 0)"
    [ -s inter_stderr.tmp ] && head -2 inter_stderr.tmp | sed 's/^/    interactor: /'
    exit 0
elif [ $INTER_EXIT -eq 1 ]; then
    echo "  Sample $SAMPLE: WRONG ANSWER (interactor exit 1)"
    [ -s inter_stderr.tmp ] && head -3 inter_stderr.tmp | sed 's/^/    interactor: /'
    exit 1
elif [ $INTER_EXIT -eq 2 ]; then
    echo "  Sample $SAMPLE: PRESENTATION ERROR (interactor exit 2)"
    [ -s inter_stderr.tmp ] && head -3 inter_stderr.tmp | sed 's/^/    interactor: /'
    exit 2
elif [ $INTER_EXIT -eq 124 ] || [ $INTER_EXIT -eq 137 ]; then
    echo "  Sample $SAMPLE: TIMEOUT (120s exceeded)"
    echo "    This usually means your solution deadlocked (missing flush? wrong protocol?)"
    [ -s sol_stderr.tmp ] && head -3 sol_stderr.tmp | sed 's/^/    solution stderr: /'
    exit 4
else
    echo "  Sample $SAMPLE: UNKNOWN (interactor exit $INTER_EXIT, solution exit $SOL_EXIT)"
    [ -s inter_stderr.tmp ] && head -3 inter_stderr.tmp | sed 's/^/    interactor: /'
    [ -s sol_stderr.tmp ] && head -3 sol_stderr.tmp | sed 's/^/    solution: /'
    exit 4
fi
"""


def build_agent_prompt(problem_dir: str, *, parity: bool = False) -> str:
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

    # Base info
    parts = [f"""You are solving a competitive programming problem.

Problem directory: {problem_dir}
- Read statement.txt for the full problem description
- Time limit: {time_limit}, Memory limit: {memory_limit}
- Total hidden test cases: {total_cases} (your score = fraction passed)
- testdata/ contains sample test cases — these are a SUBSET of the hidden tests"""]

    # Problem type specific guidance
    if is_interactive:
        parts.append("""
## Problem type: INTERACTIVE

This is an interactive problem. Your solution communicates with a judge interactor
via stdin/stdout. You do NOT read from files — you read responses from the interactor
and write queries/answers to stdout.

Key files provided:
- interactor.cc — the judge interactor (uses testlib.h, both provided)
- testdata/*.in — interactor input seeds (NOT your stdin)

**CRITICAL for interactive problems:**
- You MUST flush stdout after EVERY output line: use `cout << endl;` or `cout << flush;`
- Read the interactor source code to understand the exact protocol (what it sends, what it expects)
- Count your queries carefully against the stated limit

**Testing interactive solutions locally:**
Use the provided `./run_interactive.sh` script:
```bash
./run_interactive.sh 1    # Test with sample 1
./run_interactive.sh 2    # Test with sample 2
# Run all samples:
for i in testdata/*.in; do ./run_interactive.sh $(basename $i .in); done
```

If `run_interactive.sh` times out (exit code 4), it usually means a deadlock:
- Missing `flush` / `endl` on your output
- Reading when the interactor expects you to write, or vice versa
- Exceeding the query limit (interactor stops responding)

**Fallback testing:** If the shell script doesn't work, write a Python wrapper:
```python
import subprocess, os
proc_sol = subprocess.Popen(['./solution'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
proc_int = subprocess.Popen(['./interactor', 'testdata/1.in', '/dev/null', 'testdata/1.ans'],
                             stdin=proc_sol.stdout, stdout=proc_sol.stdin)
proc_int.wait(); proc_sol.wait()
print(f"interactor exit: {proc_int.returncode}")
```

IMPORTANT: You MUST test your solution locally before finalizing. Do NOT submit untested code.""")
    else:
        checker_note = ""
        if has_checker:
            checker_note = """
Note: This problem has a SPECIAL JUDGE (chk.cc) — multiple valid outputs may be accepted.
`test_all.sh` will automatically compile and use the checker for validation.
If the checker reports PASS but the output looks different from the .ans file, that's fine."""

        parts.append(f"""
## Problem type: {"SPECIAL JUDGE (multiple valid outputs accepted)" if has_checker else "STANDARD"}

**Testing your solution locally:**
Use the provided `./test_all.sh` script:
```bash
./test_all.sh    # Compiles solution.cpp and runs against ALL samples
```
This compiles, runs each sample, and compares output. Always run this before finalizing.{checker_note}""")

    # Scoring context
    parts.append(f"""
## Scoring

Your score is the fraction of hidden test cases passed (0-100%).
- There are {total_cases} hidden test cases total
- Partial credit counts — passing 7/10 cases = 70% score
- A correct-but-slow solution that passes small cases is MUCH better than a broken fast one
- Prioritize CORRECTNESS over optimality. Get a working solution first, then optimize.""")

    # Embed samples if small enough
    sample_text = _format_samples(samples, is_interactive)
    if sample_text:
        parts.append(sample_text)
    elif samples:
        parts.append("\n(Sample inputs are large — read them from testdata/ directory.)\n")

    # Workflow
    parts.append("""## Workflow

1. Read the FULL problem statement carefully. Re-read the constraints and edge cases.
2. Read ALL sample test cases and understand the expected I/O format.
3. Design your algorithm. Think about time complexity vs the constraints.
4. Write a SIMPLE correct solution first — brute force is fine for a first version.
5. Compile and test against ALL samples using the provided test script.
6. If samples fail: debug by examining the diff, don't just rewrite everything.
7. Once samples pass: think about edge cases and whether your algorithm handles large inputs.
8. Optimize only after correctness is established.

**Critical rules:**
- Do NOT rewrite your solution from scratch more than once. Incremental edits preserve working logic.
- Do NOT skip local testing. Every change must be tested before you move on.
- Do NOT submit without running test_all.sh (or run_interactive.sh for interactive).
- If you TLE on large cases, profile the bottleneck — don't simplify the entire algorithm.

**Retreat strategy — know when to simplify:**
- If you've been debugging the SAME bug for more than 5 edit-test cycles without progress,
  STOP and switch to a fundamentally simpler approach. A correct brute-force that passes
  small cases is worth more than a broken optimized solution that passes nothing.
- If your approach is off by a small constant (e.g., exceeding a limit by 1), consider whether
  a completely different algorithm would avoid the issue rather than patching endlessly.
- Remember: partial credit exists. A solution scoring 30% is infinitely better than 0%.
  When in doubt, submit what works even if it's suboptimal.

Submit your final solution as solution.cpp in the current working directory.""")

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
    parts = [f"""You are solving a competitive programming problem.

Problem directory: {problem_dir}
- Read statement.txt for the full problem description
- Time limit: {time_limit}, Memory limit: {memory_limit}
- Total test cases: {total_cases} (your score = fraction passed)
- Scoring is partial: 0-100% based on test cases passed"""]

    if is_interactive:
        parts.append("""
## Problem type: INTERACTIVE

This is an interactive problem. Your solution communicates with a hidden judge
via stdin/stdout. You do NOT read from files.

**CRITICAL:**
- Flush stdout after EVERY output line: `cout << endl;` or `cout << flush;`
- Read the problem statement carefully for the exact query/response protocol
- Count your queries against the stated limit""")
    elif has_checker:
        parts.append("""
## Problem type: SPECIAL JUDGE

This problem accepts multiple valid outputs. Your solution will be checked by
a special judge, not by exact string matching.""")
    else:
        parts.append("""
## Problem type: STANDARD

Your output must match the expected output exactly (whitespace-normalized).""")

    parts.append(f"""
## Scoring

Your score is the fraction of test cases passed (0-100%).
- There are {total_cases} test cases total
- Partial credit counts — passing 7/10 cases = 70% score
- A correct-but-slow solution that passes small cases is MUCH better than a broken fast one
- Prioritize CORRECTNESS over optimality

## Self-testing

No test data or test scripts are provided. You must validate your own solution:

1. **Write a brute-force reference solution** (even if O(n!) or exponential) that you are
   confident is correct for small inputs.
2. **Write a random test generator** that produces valid inputs within the problem constraints.
3. **Cross-validate (对拍):** Run both solutions on hundreds of random small inputs and compare
   outputs. Fix any discrepancies by debugging your main solution against the brute-force.
4. **Stress test:** Generate larger random inputs to check for TLE, MLE, or crashes.
5. **Edge cases:** Manually test minimum inputs (N=1, empty, etc.) and boundary values.

This self-testing approach is standard competitive programming practice. Do NOT skip it.

## Workflow

1. Read the FULL problem statement carefully. Re-read the constraints and edge cases.
2. Understand the I/O format from the examples in the problem statement.
3. Design your algorithm. Think about time complexity vs the constraints.
4. Write a SIMPLE correct solution first — brute force is fine for a first version.
5. Write a separate brute-force and test generator, then cross-validate.
6. Once confident in correctness: optimize for performance if needed.
7. Stress test with larger inputs before finalizing.

**Retreat strategy:** If stuck on the same bug for 5+ cycles, switch to a simpler
algorithm. A correct brute-force scoring 30% beats a broken solution scoring 0%.

Submit your final solution as solution.cpp in the current working directory.""")

    return "\n".join(parts)


def _write_helper_scripts(workdir: Path, is_interactive: bool) -> None:
    """Write test helper scripts to the agent's working directory."""
    # Always provide test_all.sh for non-interactive
    test_all = workdir / "test_all.sh"
    test_all.write_text(_TEST_ALL_SH, encoding="utf-8")
    test_all.chmod(test_all.stat().st_mode | stat.S_IEXEC)

    if is_interactive:
        run_inter = workdir / "run_interactive.sh"
        run_inter.write_text(_RUN_INTERACTIVE_SH, encoding="utf-8")
        run_inter.chmod(run_inter.stat().st_mode | stat.S_IEXEC)


def _write_workdir_claude_md(workdir: Path, is_interactive: bool, *, parity: bool = False) -> None:
    """Write a CLAUDE.md to the workdir so Claude Code picks up behavioral guidance."""
    lines = [
        "# Agent Eval — Working Directory",
        "",
        "You are solving a competitive programming problem in this directory.",
        "",
        "## Rules",
        "",
        "- Your ONLY deliverable is `solution.cpp` in this directory.",
        "- Use C++17 (g++ -std=gnu++17).",
        "- Always compile with `-O2` for performance testing.",
        "- Read the problem statement COMPLETELY before writing any code.",
        "",
        "## Testing",
        "",
    ]
    if parity:
        lines += [
            "No test data or test scripts are provided.",
            "Write your own brute-force solution + random test generator to cross-validate.",
            "This is standard competitive programming practice (对拍).",
            "",
        ]
        if is_interactive:
            lines += [
                "This is an INTERACTIVE problem.",
                "- `cout << endl;` or `cout << flush;` after EVERY line you output",
                "- Read the problem statement to understand the exact protocol",
                "- Count queries against the stated limit",
                "",
            ]
    elif is_interactive:
        lines += [
            "This is an INTERACTIVE problem. Use `./run_interactive.sh N` to test sample N.",
            "Do NOT skip interactive testing — protocol bugs are the #1 failure mode.",
            "",
            "### Interactive protocol checklist",
            "- `cout << endl;` or `cout << flush;` after EVERY line you output",
            "- Read the interactor source code to know the exact send/receive order",
            "- Count queries against the stated limit",
            "- If run_interactive.sh times out: you likely have a deadlock (missing flush or wrong protocol)",
            "- Fallback: write a Python subprocess wrapper if the shell script fails",
            "",
        ]
    else:
        lines += [
            "Use `./test_all.sh` to compile and test against all samples.",
            "If chk.cc exists, test_all.sh uses it as a special judge automatically.",
            "Fix any failing samples before moving on to optimization.",
            "",
        ]
    lines += [
        "## Common mistakes to avoid",
        "",
        "- Forgetting to flush stdout in interactive problems",
        "- Off-by-one errors in array indexing (0-indexed vs 1-indexed)",
        "- Integer overflow — use `long long` for anything that could exceed 2^31",
        "- Reading input in the wrong order or format",
        "- Not handling the edge case where N=1 or the input is minimal",
        "- Rewriting the entire solution when a small fix would work",
        "",
        "## When to retreat",
        "",
        "- If you've edited and tested 5+ times for the same bug without progress, STOP.",
        "- Switch to a simpler algorithm that is guaranteed correct, even if slower.",
        "- A correct brute-force scoring 30% beats a broken clever solution scoring 0%.",
        "- Partial credit is real: every test case you pass counts.",
        "",
    ]
    (workdir / "CLAUDE.md").write_text("\n".join(lines), encoding="utf-8")


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
    cost_limit: float = DEFAULT_COST_LIMIT_USD,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    transcript_path: Optional[Path] = None,
    parity: bool = False,
) -> Tuple[str, Dict[str, Any]]:
    """Run the agent to solve a problem.

    Args:
        problem_dir: Absolute path to the problem directory.
        model: Base model name (without -agent suffix).
        cost_limit: Maximum cost in USD.
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
    cost_limit: float = DEFAULT_COST_LIMIT_USD,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    transcript_path: Optional[Path] = None,
    parity: bool = False,
) -> Tuple[str, Dict[str, Any]]:
    """Synchronous wrapper for run_agent.

    This is the main entry point called from generate_solutions.py.

    Args:
        problem_dir: Absolute path to the problem directory.
        model: Base model name (without -agent suffix).
        cost_limit: Maximum cost in USD.
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
            cost_limit=cost_limit,
            timeout=timeout,
            transcript_path=transcript_path,
            parity=parity,
        )
    )
