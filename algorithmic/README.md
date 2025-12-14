## Problem Structure

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

---

## Quick Start

### 1. Start Judge Server

```bash
docker-compose up --build -d   # First time
docker-compose up -d           # Subsequent runs
```

Judge runs at `http://localhost:8081`.

### 2. Run Benchmark for LLMs

```bash
python scripts/run_tests.py <model_name>
```

**Supported models:**
- `gpt`
- `claude`, `claude-opus`, `claude-opus-4-5`, `claude-sonnet-4-5`
- `gemini`, `gemini3`
- `Grok`

### 3. View Results

Results saved to `scripts/solutions/`:
- `{problem_id}_{model}_solution.cpp`: Generated code
- `{problem_id}_{model}_result.json`: Judge result with score

---

## How It Works

1. **Fetch problem** statement from judge API
2. **Generate solution** via LLM (C++ code)
3. **Submit** to judge server
4. **Poll** for result
5. **Score** based on test case pass rate

---

## Judge API

| Endpoint | Description |
|----------|-------------|
| `GET /problems` | List all problems |
| `GET /problem/{id}/statement` | Get problem statement |
| `POST /submit` | Submit solution |
| `GET /result/{sid}` | Get submission result |

---

## Customized Problems

1. Create `problems/{id}/` directory
2. Add required files:
   - `statement.txt`: Problem description
   - `tag.txt`: Category (optimization/construction/interactive)
   - `config.yaml`: Limits and test count
   - `testdata/`: Input/output files
   - `chk.cc` or `interactor.cc`: Checker/interactor

3. Restart judge to pick up new problems

---

## Configuration

### `config.yaml`

```yaml
time_limit: 1000        # ms
memory_limit: 262144    # KB
test_count: 10
checker: chk.cc         # or interactor: interactor.cc
```

### `docker-compose.yml`

```yaml
environment:
  PORT: "8081"              # API port
  JUDGE_WORKERS: "8"        # Concurrent evaluations
  GJ_PARALLELISM: "8"       # go-judge parallelism
```
