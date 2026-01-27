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
frontier-eval batch

# With SkyPilot (cloud VMs)
frontier-eval batch --skypilot --workers 20 --clusters 4

# Check status
frontier-eval batch --status

# Force re-evaluate all
frontier-eval batch --no-resume

# Retry failed evaluations
frontier-eval batch --retry-failed
```

**Parameters:**
- `--workers`: Number of parallel workers (default: 1)
- `--clusters`: Number of SkyPilot clusters for load-balancing (default: same as workers, research + skypilot only)

With `--workers 20 --clusters 4`, 20 workers share 4 clusters via load-balancing.

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
| `config.yaml`          | Runtime config (Docker image, GPU, timeout, dependencies) |
| `readme`               | Problem description, API spec, scoring formula          |
| `set_up_env.sh`        | Dataset preparation only (deps handled by framework)    |
| `evaluate.sh`          | Evaluation entry point                                  |
| `evaluator.py`         | Core evaluation logic                                   |
| `resources/`           | Baseline code, benchmark, test data, pyproject.toml     |

**Note:** `resources/`, `common/`, and `__pycache__/` directories are excluded from problem detection. A valid problem directory must contain `evaluator.py` or `evaluate.py`.

### config.yaml Example

```yaml
tag: hpc  # Category: os, hpc, ai, db, pl, security
runtime:
  timeout_seconds: 1800
  environment: "Custom environment description for LLM prompts"  # Optional
  docker:
    image: andylizf/triton-tlx:tlx-nv-cu122
    gpu: true
    dind: false  # Set true for Docker-in-Docker (auto-installs Docker CLI)
  resources:
    accelerators: "L4:1"  # GPU type and count
dependencies:
  uv_project: resources  # Auto-synced by framework (pyproject.toml in resources/)
```

The framework automatically:
- Installs dependencies from `uv_project` via `uv sync`
- Installs Docker CLI inside the container when `dind: true`

### Protecting Pre-installed Packages (Important!)

Many Docker images come with pre-installed, customized versions of packages like `triton` or `torch`. If your `pyproject.toml` lists these as dependencies, `uv` will replace them with standard versions, breaking GPU support.

**Solution:** Create `resources/uv_overrides.txt` to skip pre-installed packages:

```
triton ; sys_platform == 'never'
torch ; sys_platform == 'never'
```

The `sys_platform == 'never'` condition is always false, so `uv` skips these packages entirely.

**Example:** Problem using `andylizf/triton-tlx` image with custom Triton:

```
resources/
├── pyproject.toml      # Lists triton>=2.1.0 as dependency
├── uv_overrides.txt    # Prevents triton from being replaced
└── benchmark.py
```

Without `uv_overrides.txt`:
```
- triton==3.4.0+gitc95fb48c (uninstalled!)
~ triton==3.1.0 (replaced with standard version)
→ RuntimeError: 0 active drivers
```

With `uv_overrides.txt`:
```
Triton version: 3.4.0 (kept original)
→ Works correctly
```

**When to use:** Always add `uv_overrides.txt` when your Docker image has custom-built packages (especially Triton, PyTorch, or CUDA-related libraries).

## Evaluation Flow

Inside the Docker container, the execution order is:

```
1. Copy solution.py      →  /work/execution_env/solution_env/
2. Install curl/uv       →  Framework auto-installs if missing
3. Install Docker CLI    →  If dind: true in config.yaml
4. uv sync               →  Auto-install deps from uv_project
5. set_up_env.sh         →  Dataset preparation (if exists)
6. evaluate.sh           →  Check files, run evaluator
7. evaluator.py          →  Load Solution.solve(), run benchmark, print score
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
