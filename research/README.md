# Research Problems

> **Technical Reference**: Problem structure, evaluation details, and Solution interface for research track.
>
> For model evaluation workflow, see [SUBMIT.md](../SUBMIT.md).

Real-world systems challenges requiring domain expertise in GPU computing, distributed systems, ML pipelines, databases, and security.

## Basic Usage

Research track defaults to SkyPilot (cloud) because problems have specific resource requirements (GPUs, memory, etc.) that can affect evaluation results. Run `sky check` to verify cloud credentials. See [SkyPilot docs](https://skypilot.readthedocs.io/en/latest/getting-started/installation.html) for setup.

```bash
# List all problems
frontier list research

# Evaluate (uses SkyPilot by default)
frontier eval research flash_attn <your_solution.py>

# Use Docker instead (no cloud setup needed)
frontier eval research flash_attn <your_solution.py> --backend docker

```

## Batch Evaluation

For batch evaluation of multiple solutions, see [SUBMIT.md](../SUBMIT.md#step-2-run-evaluation).

```bash
frontier batch research                    # Evaluate all in solutions/
frontier batch research --model my_model   # Filter by model
frontier batch research --status           # Check progress
```

## Python API

```python
from frontier_cs import SingleEvaluator

evaluator = SingleEvaluator()

# Single problem (uses SkyPilot by default for research)
result = evaluator.evaluate("research", problem_id="flash_attn", code=my_code)
print(f"Score: {result.score}")

# Use Docker instead
result = evaluator.evaluate("research", problem_id="flash_attn", code=my_code,
                           backend="docker")
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

> For creating new problems (config.yaml format, evaluation scripts, uv_overrides.txt), see [CONTRIBUTING.md](../CONTRIBUTING.md#research-problems).

## Solution Requirements

- **Language**: Python only
- **Interface**: Implement a `Solution` class with a `solve()` method
- **Single file**: Submit one `solution.py` per problem

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

