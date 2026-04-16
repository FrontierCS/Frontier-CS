# Algorithmic Problems

> **Technical Reference**: Problem structure, Judge API, and evaluation details for algorithmic track.
>
> For model evaluation workflow, see [SUBMIT.md](../SUBMIT.md).

### Problem Structure

Each problem in `problems/{id}/` contains:

```
problems/{id}/
├── statement.txt      # Problem description
├── tag.txt            # Category tag
├── config.yaml        # Time/memory limits, test count
├── testdata/          # Test cases (public: 1 per problem)
│   ├── 1.in
│   └── 1.ans
└── chk.cc / interactor.cc   # Checker or interactor
```

### Solution Requirements

- **Language**: C++17 only
- **Single file**: Submit one `.cpp` file per problem

### How It Works

1. **Fetch problem** statement from judge API
2. **Generate solution** via LLM (C++ code)
3. **Submit** to judge server
4. **Poll** for result
5. **Score** based on test case pass rate

The judge server will save solutions and their detailed judging results under the folder `algorithmic/submissions`.


### Judge API

| Endpoint | Description |
|----------|-------------|
| `GET /problems` | List all problems |
| `GET /problem/{id}/statement` | Get problem statement |
| `POST /submit` | Submit solution |
| `GET /result/{sid}` | Get submission result |


### Python API

```python
from frontier_cs import SingleEvaluator

evaluator = SingleEvaluator()

# Evaluate an algorithmic problem
result = evaluator.evaluate("algorithmic", problem_id=1, code=cpp_code)
print(f"Score: {result.score}")

# Get unbounded score (without clipping)
result = evaluator.evaluate("algorithmic", problem_id=1, code=cpp_code, unbounded=True)
print(f"Score: {result.score}")  # Uses unbounded when unbounded=True
print(f"Score (unbounded): {result.score_unbounded}")
```

### CLI

```bash
# Evaluate a solution
frontier eval algorithmic 1 solution.cpp

# Get unbounded score
frontier eval algorithmic 1 solution.cpp --unbounded
```

### Batch Evaluation

For batch evaluation of multiple solutions, see [SUBMIT.md](../SUBMIT.md#step-2-run-evaluation).

```bash
frontier batch algorithmic                    # Evaluate all in solutions/
frontier batch algorithmic --backend skypilot # Use cloud go-judge
frontier batch algorithmic --status           # Check progress
```

**Note:** For algorithmic track, `--clusters` is not used. All workers share a single go-judge server (local Docker or SkyPilot).

### Cloud Evaluation (SkyPilot)

For environments where Docker privileged mode is unavailable (e.g., gVisor, Cloud Run):

```bash
# Auto-launch cloud judge
frontier eval algorithmic 1 solution.cpp --backend skypilot

# Or manually launch
sky launch -c algo-judge algorithmic/sky-judge.yaml --idle-minutes-to-autostop 10
frontier eval algorithmic 1 solution.cpp --judge-url http://$(sky status --ip algo-judge):8081
```

### Agent Evaluation

Agent mode lets an AI agent solve problems iteratively — reading the statement, writing code, compiling, testing against samples, and refining — rather than generating a single-shot solution.

Agents use the [Claude Agent SDK](https://github.com/anthropic/claude-agent-sdk) (Claude Code as a library). The agent gets a temporary copy of the problem directory with full tool access (shell, file I/O, compilation).

#### Model naming convention

Append `-agent` to any Claude model name to trigger agent mode:

```
claude-sonnet-4-5-20250514-agent   # Agent mode with Sonnet 4.5
claude-opus-4-6-20250610-agent     # Agent mode with Opus 4.6
```

The `-agent` suffix is stripped before passing the model to the SDK. The model prefix for output files includes `agent` (e.g., `claude4.5sonnetagent.cpp`), so agent and single-shot results never collide.

#### Running agent evaluation

```bash
cd algorithmic/scripts

# Single model, all problems
python generate_solutions.py \
  --model claude-sonnet-4-5-20250514-agent \
  --judge-url http://localhost:8081

# Subset of problems, custom budget
python generate_solutions.py \
  --model claude-sonnet-4-5-20250514-agent \
  --problems 0,1,2,3 \
  --agent-timeout 1800 \
  --agent-cost-limit 30 \
  --judge-url http://localhost:8081

# Multiple variants per problem
python generate_solutions.py \
  --model claude-sonnet-4-5-20250514-agent \
  --indices 3 \
  --judge-url http://localhost:8081
```

**Agent-specific CLI flags:**

| Flag | Default | Description |
|------|---------|-------------|
| `--agent-timeout` | 1200 (20 min) | Wall-clock timeout per problem in seconds |
| `--agent-cost-limit` | 20.0 | Max cost per problem in USD |

#### Output files

For each problem/variant, agent mode produces three files:

```
solutions/{problem_id}/
├── claude4.5sonnetagent.cpp           # Extracted C++ solution
├── claude4.5sonnetagent.meta.json     # Run metadata (cost, tokens, turns, status)
└── (in generation_logs/)
    └── claude4.5sonnetagent_*.transcript.jsonl  # Full agent transcript
```

**meta.json** fields:
- `tokens_in` / `tokens_out` — total token usage
- `cost_usd` — total API cost
- `time_seconds` — wall-clock time
- `turns` — number of agentic turns (tool-use round trips)
- `status` — `success`, `timeout`, `cost_limit`, or `error`

#### Prerequisites

1. **Claude Agent SDK**: `pip install claude-agent-sdk` (or `uv sync` if already in project deps)
2. **Claude Code CLI**: Must be installed and authenticated (`claude --version`)
3. **Judge server**: Running and accessible (see [Judge Server Configuration](#judge-server-configuration))
4. **g++**: Available in PATH for the agent to compile solutions

#### How it works

1. The problem directory is copied to a temp working directory (concurrent-safe)
2. `testlib.h` is automatically copied from `judge/include/` if present (needed for interactive problems)
3. The agent receives a structured prompt with the problem path and workflow guidance
4. The agent iterates: reads the problem, writes code, compiles, tests against samples, and refines
5. On completion (or timeout), `solution.cpp` is extracted from the working directory
6. The temp directory is cleaned up; solution + metadata are saved

#### Interactive problems

Problems with `interactor.cc` (instead of `chk.cc`) are interactive — the solution communicates with a judge interactor via stdin/stdout. The agent prompt instructs it to:

1. Compile the interactor using `g++ -std=gnu++17 -I. interactor.cc -o interactor`
2. Test locally via pipes (e.g., `mkfifo pipe; ./solution < pipe | ./interactor > pipe`)
3. `testlib.h` is provided automatically in the working directory

Interactive problems are harder for agents because local testing requires building a pipe harness, which agents sometimes skip or get wrong.

#### Known limitations

- **No extended thinking**: The Claude Agent SDK does not currently expose extended thinking controls. Enabling it may improve complex algorithmic reasoning.
- **Rewrite tendency**: Agents sometimes rewrite solutions from scratch after failures, losing working logic. The prompt mitigates this but doesn't eliminate it.
- **Interactive testing**: Agents frequently skip local testing for interactive problems, submitting untested code.
- **Algorithm ceiling**: For problems requiring non-trivial algorithmic insight (advanced DP, flow, geometry), agent iteration doesn't compensate for model capability gaps.

### Creating Problems

> For contributing problems to Frontier-CS (detailed file formats, CI requirements), see [CONTRIBUTING.md](../CONTRIBUTING.md#algorithmic-problems).

### Judge Server Configuration

#### config.yaml

```yaml
time_limit: 1000        # ms
memory_limit: 262144    # KB
test_count: 10
checker: chk.cc         # or interactor: interactor.cc
```

#### docker-compose.yml

The judge server will be auto-started when running `frontier eval algorithmic ...`.

```yaml
environment:
  PORT: "8081"              # API port
  JUDGE_WORKERS: "8"        # Concurrent evaluations
  GJ_PARALLELISM: "8"       # go-judge parallelism
```
