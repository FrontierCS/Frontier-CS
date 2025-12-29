# Research Problems

Real-world systems challenges requiring domain expertise in GPU computing, distributed systems, ML pipelines, databases, and security.

## Basic Usage

```bash
# List all problems
frontier list

# Evaluate a solution (requires Docker)
frontier eval flash_attn <your_solution.py>

# Evaluate multiple problems
frontier eval --problems flash_attn,cross_entropy <your_solution.py>
```

## Cloud Evaluation with SkyPilot

Some problems require GPUs or specific hardware. Use [SkyPilot](https://skypilot.readthedocs.io/) to run evaluations on cloud VMs.

**Setup:**

```bash
sky check
```

See [SkyPilot docs](https://skypilot.readthedocs.io/en/latest/getting-started/installation.html) for cloud credential setup.

**Usage:**

```bash
frontier eval flash_attn <your_solution.py> --skypilot
```

## Batch Evaluation

Batch evaluation automatically scans `solutions/` and parses problem IDs from filenames:

```bash
# Evaluate all solutions (auto-skips completed)
frontier batch

# Check status
frontier batch --status

# Force re-evaluate all
frontier batch --no-resume
```

## Python API

```python
from frontier_cs import FrontierCSEvaluator

evaluator = FrontierCSEvaluator()

# Single problem
result = evaluator.evaluate("research", problem_id="flash_attn", code=my_code)
print(f"Score: {result.score}")

# With SkyPilot
result = evaluator.evaluate("research", problem_id="flash_attn", code=my_code,
                           backend="skypilot")
```

## Problem Structure

Each problem is in its own directory under `research/problems/`:

```
research/problems/
├── flash_attn/           # Single problem
│   ├── config.yaml
│   ├── readme
│   ├── evaluator.py
│   └── resources/
├── gemm_optimization/    # Problem with variants
│   ├── squares/
│   ├── rectangles/
│   └── ...
└── ...
```

### File Reference

| File                   | Purpose                                                 |
| ---------------------- | ------------------------------------------------------- |
| `config.yaml`          | Runtime config (Docker image, GPU requirement, timeout) |
| `readme`               | Problem description, API spec, scoring formula          |
| `set_up_env.sh`        | Environment setup (install deps, check CUDA)            |
| `download_datasets.sh` | Download datasets (for local pre-download)              |
| `evaluate.sh`          | Evaluation entry point                                  |
| `run_evaluator.sh`     | Invokes `evaluator.py`                                  |
| `evaluator.py`         | Core evaluation logic                                   |
| `resources/`           | Baseline code, benchmark, test data                     |

### config.yaml Example

```yaml
dependencies:
  uv_project: resources # Optional: uv project in resources/
datasets: [] # Optional: dataset URLs
tag: hpc # Category: os, hpc, ai, db, pl, security
runtime:
  docker:
    image: andylizf/triton-tlx:tlx-nv-cu122
    gpu: true
  timeout_seconds: 1800
```

## Evaluation Flow

Inside the Docker container, the execution order is:

```
1. set_up_env.sh         →  Initialize environment
2. Copy solution.py      →  /work/execution_env/solution_env/
3. evaluate.sh           →  Check files, call run_evaluator.sh
4. run_evaluator.sh      →  python3 evaluator.py
5. evaluator.py          →  Load Solution.solve(), run benchmark, print score
```

The final score is extracted from the last numeric line of stdout.

## Solution Interface

Submit a `solution.py` implementing the `Solution` class. The interface varies by problem type:

### Triton Kernel Problems (flash_attn, cross_entropy, gemm_optimization...)

```python
class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns either:
        - {"code": "python_code_string"}
        - {"program_path": "path/to/kernel.py"}
        """
        kernel_code = '''
import triton
import triton.language as tl

@triton.jit
def my_kernel(...):
    ...

def entry_function(...):
    ...
'''
        return {"code": kernel_code}
```

### ML Training Problems (imagenet_pareto...)

```python
class Solution:
    def solve(self, train_loader, val_loader, metadata: dict) -> torch.nn.Module:
        """
        Train and return a model.

        metadata contains: num_classes, input_dim, param_limit,
                          baseline_accuracy, device, etc.
        """
        model = MyModel(...)
        # training loop
        return model
```

### Other Problems

Check each problem's `readme` for the specific `solve()` signature and return type.

## Generating Solutions with LLMs

Use `generate_solutions.py` to generate solutions using LLMs.

```bash
# Generate one solution
python research/scripts/generate_solutions.py --problem flash_attn --model gpt-5 --indices 1

# Preview what would be generated
python research/scripts/generate_solutions.py --dryrun
```

### Two Modes

**Problem mode** (generate new solutions):

```bash
python research/scripts/generate_solutions.py --problem flash_attn --model gpt-5
```

Generates **problems × models × indices** (Cartesian product):

- Problems: `--problem` patterns or `--problems-file` (default: auto-discover all problems)
- Models: `--model` list or `--models-file` (default: `models.txt`)
- Indices: `--indices N` or `--indices-file` (default: `indices.txt` or single solution)

Solution naming: `{problem}.{model}.py` for index 0, `{problem}.{model}_{i}.py` for index i.

**Solution mode** (regenerate existing solutions):

```bash
python research/scripts/generate_solutions.py --solution "flash_attn.gpt5*" --force
```

- Matches existing solutions in `solutions/` by pattern
- Model inferred from solution filename (e.g., `flash_attn.gpt5.py` → model `gpt5`)
- Requires `--force` since solutions already exist
- Still needs `models.txt` or `--model` to map prefix to model name

### Options

| Option                          | Description                                                                    |
| ------------------------------- | ------------------------------------------------------------------------------ |
| `--problem` / `--problems-file` | Problem pattern or file (default: auto-discover)                               |
| `--model` / `--models-file`     | Model(s) or file (default: `models.txt`)                                       |
| `--indices` / `--indices-file`  | Solution indices count or file (default: `indices.txt`)                        |
| `--solution PATTERN`            | Regenerate existing solutions by pattern (mutually exclusive with `--problem`) |
| `--force`                       | Overwrite existing solutions                                                   |
| `--dryrun`                      | Preview without generating                                                     |
| `--concurrency N`               | Parallel API calls                                                             |
| `--timeout SECONDS`             | API timeout (default: 600s)                                                    |

### Output

Solutions are saved as flat files in `solutions/`:

```
solutions/
├── flash_attn.gpt5.py
├── flash_attn.gpt5_1.py
├── flash_attn.claude.py
└── cross_entropy.gpt5.py
```

### API Keys

Set environment variables for the providers you need. Multiple keys per provider are supported for load balancing (e.g., `OPENAI_API_KEY`, `OPENAI_API_KEY2`, `OPENAI_API_KEY_2`).

| Provider   | Environment Variable | Models                                |
| ---------- | -------------------- | ------------------------------------- |
| OpenAI     | `OPENAI_API_KEY`     | gpt-4o, gpt-5, o1, o3, ...            |
| Anthropic  | `ANTHROPIC_API_KEY`  | claude-sonnet-4-5, claude-opus-4, ... |
| Google     | `GOOGLE_API_KEY`     | gemini-2.5-pro, gemini-2.5-flash, ... |
| xAI        | `XAI_API_KEY`        | grok-3, grok-3-mini, ...              |
| DeepSeek   | `DEEPSEEK_API_KEY`   | deepseek-r1, deepseek-chat, ...       |
| OpenRouter | `OPENROUTER_API_KEY` | openrouter/\* models                  |

```bash
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-...
export GOOGLE_API_KEY=...
```
