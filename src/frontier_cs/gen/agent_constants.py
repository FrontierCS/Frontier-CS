"""Prompt templates, shell scripts, and CLAUDE.md content for agent eval.

All large string constants live here to keep agent_interface.py focused on logic.
"""

# ---------------------------------------------------------------------------
# Shell scripts (used in parity=False mode only)
# ---------------------------------------------------------------------------

TEST_ALL_SH = r"""#!/bin/bash
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

RUN_INTERACTIVE_SH = r"""#!/bin/bash
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

# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

# Parity prompt (default): agent gets NO test data, must self-test
PARITY_PROMPT = """You are solving a competitive programming problem.

Problem directory: {problem_dir}
- Read statement.txt for the full problem description
- Time limit: {time_limit}, Memory limit: {memory_limit}
- Total test cases: {total_cases} (your score = fraction passed)
- Scoring is partial: 0-100% based on test cases passed"""

PARITY_INTERACTIVE_SECTION = """
## Problem type: INTERACTIVE

This is an interactive problem. Your solution communicates with a hidden judge
via stdin/stdout. You do NOT read from files.

**CRITICAL:**
- Flush stdout after EVERY output line: `cout << endl;` or `cout << flush;`
- Read the problem statement carefully for the exact query/response protocol
- Count your queries against the stated limit"""

PARITY_SPJ_SECTION = """
## Problem type: SPECIAL JUDGE

This problem accepts multiple valid outputs. Your solution will be checked by
a special judge, not by exact string matching."""

PARITY_STANDARD_SECTION = """
## Problem type: STANDARD

Your output must match the expected output exactly (whitespace-normalized)."""

PARITY_SCORING_AND_WORKFLOW = """
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

Submit your final solution as solution.cpp in the current working directory."""

# Full-access prompt (parity=False): agent gets test data and helper scripts
FULL_ACCESS_PROMPT = """You are solving a competitive programming problem.

Problem directory: {problem_dir}
- Read statement.txt for the full problem description
- Time limit: {time_limit}, Memory limit: {memory_limit}
- Total hidden test cases: {total_cases} (your score = fraction passed)
- testdata/ contains sample test cases — these are a SUBSET of the hidden tests"""

FULL_ACCESS_INTERACTIVE_SECTION = """
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
print(f"interactor exit: {{proc_int.returncode}}")
```

IMPORTANT: You MUST test your solution locally before finalizing. Do NOT submit untested code."""

FULL_ACCESS_STANDARD_SECTION = """
## Problem type: {problem_type}

**Testing your solution locally:**
Use the provided `./test_all.sh` script:
```bash
./test_all.sh    # Compiles solution.cpp and runs against ALL samples
```
This compiles, runs each sample, and compares output. Always run this before finalizing.{checker_note}"""

FULL_ACCESS_SCORING_SECTION = """
## Scoring

Your score is the fraction of hidden test cases passed (0-100%).
- There are {total_cases} hidden test cases total
- Partial credit counts — passing 7/10 cases = 70% score
- A correct-but-slow solution that passes small cases is MUCH better than a broken fast one
- Prioritize CORRECTNESS over optimality. Get a working solution first, then optimize."""

FULL_ACCESS_WORKFLOW = """## Workflow

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

Submit your final solution as solution.cpp in the current working directory."""

# ---------------------------------------------------------------------------
# CLAUDE.md content
# ---------------------------------------------------------------------------

CLAUDE_MD_HEADER = """# Agent Eval — Working Directory

You are solving a competitive programming problem in this directory.

## Rules

- Your ONLY deliverable is `solution.cpp` in this directory.
- Use C++17 (g++ -std=gnu++17).
- Always compile with `-O2` for performance testing.
- Read the problem statement COMPLETELY before writing any code.

## Testing
"""

CLAUDE_MD_PARITY_TESTING = """No test data or test scripts are provided.
Write your own brute-force solution + random test generator to cross-validate.
This is standard competitive programming practice (对拍).
"""

CLAUDE_MD_PARITY_INTERACTIVE = """This is an INTERACTIVE problem.
- `cout << endl;` or `cout << flush;` after EVERY line you output
- Read the problem statement to understand the exact protocol
- Count queries against the stated limit
"""

CLAUDE_MD_FULL_INTERACTIVE = """This is an INTERACTIVE problem. Use `./run_interactive.sh N` to test sample N.
Do NOT skip interactive testing — protocol bugs are the #1 failure mode.

### Interactive protocol checklist
- `cout << endl;` or `cout << flush;` after EVERY line you output
- Read the interactor source code to know the exact send/receive order
- Count queries against the stated limit
- If run_interactive.sh times out: you likely have a deadlock (missing flush or wrong protocol)
- Fallback: write a Python subprocess wrapper if the shell script fails
"""

CLAUDE_MD_FULL_STANDARD = """Use `./test_all.sh` to compile and test against all samples.
If chk.cc exists, test_all.sh uses it as a special judge automatically.
Fix any failing samples before moving on to optimization.
"""

CLAUDE_MD_FOOTER = """
## Common mistakes to avoid

- Forgetting to flush stdout in interactive problems
- Off-by-one errors in array indexing (0-indexed vs 1-indexed)
- Integer overflow — use `long long` for anything that could exceed 2^31
- Reading input in the wrong order or format
- Not handling the edge case where N=1 or the input is minimal
- Rewriting the entire solution when a small fix would work

## When to retreat

- If you've edited and tested 5+ times for the same bug without progress, STOP.
- Switch to a simpler algorithm that is guaranteed correct, even if slower.
- A correct brute-force scoring 30% beats a broken clever solution scoring 0%.
- Partial credit is real: every test case you pass counts.
"""
