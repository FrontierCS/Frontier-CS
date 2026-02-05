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
