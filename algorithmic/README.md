## FrontierCS - Algorithmic Problems
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

### Quick Start

#### Start Judge Server

```bash
docker compose up --build -d   # First time
docker compose up -d           # Subsequent runs
```

Judge runs at `http://localhost:8081`.

### How It Works

1. **Fetch problem** statement from judge API
2. **Generate solution** via LLM (C++ code)
3. **Submit** to judge server
4. **Poll** for result
5. **Score** based on test case pass rate

The judge sever will save solutions and their detailed judging results under the folder `algorithmic/submissions`.


### Judge API

| Endpoint | Description |
|----------|-------------|
| `GET /problems` | List all problems |
| `GET /problem/{id}/statement` | Get problem statement |
| `POST /submit` | Submit solution |
| `GET /result/{sid}` | Get submission result |


### Python API

```python
from frontier_cs import FrontierCSEvaluator

evaluator = FrontierCSEvaluator()

# Evaluate an algorithmic problem
result = evaluator.evaluate("algorithmic", problem_id=1, code=cpp_code)
print(f"Score: {result.score}")

# Get unbounded score (without clipping)
result = evaluator.evaluate("algorithmic", problem_id=1, code=cpp_code, unbounded=True)
print(f"Score (bounded): {result.score}")
if hasattr(result, 'score_unbounded'):
    print(f"Score (unbounded): {result.score_unbounded}")
```

### CLI

```bash
# Evaluate a solution
frontier-eval --algorithmic 1 solution.cpp

# Get unbounded score
frontier-eval --algorithmic 1 solution.cpp --unbounded
```

### Cloud Evaluation (SkyPilot)

For environments where Docker privileged mode is unavailable (e.g., gVisor, Cloud Run):

```bash
# Auto-launch cloud judge
frontier-eval --algorithmic --skypilot 1 solution.cpp

# Or manually launch
sky launch -c algo-judge algorithmic/sky-judge.yaml --idle-minutes-to-autostop 10
frontier-eval --algorithmic --judge-url http://$(sky status --ip algo-judge):8081 1 solution.cpp
```

### Customized Problems

1. Create `problems/{id}/` directory
2. Add required files:
   - `statement.txt`: Problem description
   - `config.yaml`: Limits and test count
   - `testdata/`: Input/output files
   - `chk.cc` or `interactor.cc`: Checker/interactor

3. Restart judge to pick up new problems


### Judge Server Configuration

#### config.yaml

```yaml
time_limit: 1000        # ms
memory_limit: 262144    # KB
test_count: 10
checker: chk.cc         # or interactor: interactor.cc
```

#### docker-compose.yml

```yaml
environment:
  PORT: "8081"              # API port
  JUDGE_WORKERS: "8"        # Concurrent evaluations
  GJ_PARALLELISM: "8"       # go-judge parallelism
```
