# Research Problems

Real-world systems challenges requiring domain expertise in GPU computing, distributed systems, ML pipelines, databases, and security.

## Basic Usage

```bash
# List all problems
frontier-eval --list

# Evaluate a solution (requires Docker)
frontier-eval flash_attn <your_solution.py>

# Evaluate multiple problems
frontier-eval --problems flash_attn,cross_entropy <your_solution.py>
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
frontier-eval flash_attn <your_solution.py> --skypilot
```

## Batch Evaluation

For evaluating multiple solutions at once, create a pairs file mapping solutions to problems:

```
# pairs.txt format: solution_path:problem_id
solutions/my_flash_attn_v1.py:flash_attn
solutions/my_flash_attn_v2.py:flash_attn
solutions/my_cross_entropy.py:cross_entropy
```

Then run:

```bash
# Evaluate all pairs
frontier-eval batch --pairs-file pairs.txt

# Resume interrupted evaluation
frontier-eval batch --pairs-file pairs.txt --resume

# Check status
frontier-eval batch --status --results-dir results/batch
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

# Batch evaluation
results = evaluator.evaluate_batch("research",
                                  problem_ids=["flash_attn", "cross_entropy"],
                                  code=my_code)
```

## Problem Structure

Each problem is in its own directory under `research/`:

```
research/
├── flash_attn/
│   ├── config.yaml      # Problem metadata and scoring
│   ├── readme            # Problem description
│   ├── evaluate.sh       # Evaluation script
│   └── resources/        # Baseline code, data, etc.
├── cross_entropy/
│   └── ...
└── ...
```
