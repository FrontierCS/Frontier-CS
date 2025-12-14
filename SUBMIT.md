# Submitting Your Results

We welcome submissions from all models and agent frameworks. To have your results included in our leaderboard, please follow the instructions below.

## Algorithmic Problems

We currently release **1 -- 3 public test case** per problem for local testing and debugging. Full evaluation (with all test cases) is performed on our servers.

### What to Submit

1. **Solution files**: `{problem_id}_{model_name}_solution.cpp` for each problem
2. **Model/Agent info**: Name and version of the model or agent framework used
3. **Generation method**: Brief description of how solutions were generated (e.g., one-shot, multi-turn, with/without feedback)

### Submission Format

Organize your solutions as:
```
submissions/
├── 1_gpt4_solution.cpp
├── 2_gpt4_solution.cpp
├── ...
└── metadata.json
```

`metadata.json`:
```json
{
  "model": "gpt-4o",
  "agent_framework": "custom",
  "generation_method": "one-shot",
  "date": "2025-01-15",
  "notes": "Optional additional notes"
}
```

## Research Problems

Research problems require a `solution.py` file implementing the `Solution` class interface.

### Problem Structure

Research problems follow a hierarchical structure:

```
Problem (e.g., gemm_optimization, poc_generation)
└── Category (e.g., squares, heap_buffer_overflow)
    └── Variant (e.g., arvo_21000)
```

| Level | Example | Description |
|-------|---------|-------------|
| **Problem** | `gemm_optimization` | Top-level problem domain |
| **Category** | `gemm_optimization/squares` | Scores are **aggregated** at this level for leaderboard reporting |
| **Variant** | `poc_generation/heap_buffer_overflow/arvo_21000` | Each variant is **evaluated independently** with its own README |

**Key distinction:**
- **Evaluation**: Each variant runs independently and produces its own score
- **Reporting**: Scores are aggregated by category for the leaderboard (e.g., all `heap_buffer_overflow` variants → one score)

> Note: Some problems have only one level (e.g., `flash_attn`), which functions as both category and variant.

### Problem ID Format

Each variant has a unique **Problem ID** based on its path under `research/`.

The full list of all evaluatable variants is in [`research/problems.txt`](research/problems.txt) (109 variants total, aggregated into ~50 categories for reporting).

| Type | Example Path | Problem ID |
|------|-------------|------------|
| Single problem | `research/flash_attn` | `flash_attn` |
| Problem with variants | `research/gemm_optimization/squares` | `gemm_optimization/squares` |
| Nested variants | `research/poc_generation/heap_buffer_overflow/arvo_21000` | `poc_generation/heap_buffer_overflow/arvo_21000` |

### What to Submit

1. **Solution files**: `solution.py` for each problem, placed in a directory matching the Problem ID
2. **Model/Agent info**: Name and version of the model or agent framework used
3. **Local evaluation results** (optional but recommended): Score from running the evaluator locally

### Submission Format

Your submission zip should mirror the Problem ID directory structure:

```
submission.zip
├── flash_attn/
│   └── solution.py
├── gemm_optimization/
│   └── squares/
│       └── solution.py
├── cant_be_late/
│   └── high_availability_loose_deadline/
│       └── solution.py
├── poc_generation/
│   └── heap_buffer_overflow/
│       └── arvo_21000/
│           └── solution.py
└── metadata.json
```

**Important**: The directory structure must exactly match the Problem ID. For example:
- `flash_attn/solution.py`
- `gemm_optimization/squares/solution.py`

Each `solution.py` must implement:
```python
class Solution:
    def __init__(self):
        pass

    def solve(self, *args):
        # Returns: solution output (format varies by problem)
        pass
```

### metadata.json

```json
{
  "model": "gpt-4o",
  "agent_framework": "custom",
  "generation_method": "one-shot",
  "date": "2025-01-15",
  "problems_solved": [
    "flash_attn",
    "gemm_optimization/squares",
    "cant_be_late/high_availability_loose_deadline"
  ],
  "notes": "Optional additional notes"
}
```

### Running Local Evaluation

Before submitting, you can verify your solutions locally:

```bash
# Evaluate a single solution
frontier-eval flash_attn solution.py

# Batch evaluation with progress tracking
frontier-eval batch --pairs-file pairs.txt --results-dir results/

# Batch evaluation with SkyPilot (cloud)
frontier-eval batch --pairs-file pairs.txt --skypilot --max-concurrent 4
```

## How to Submit

Send your submission to:
- **Email**: qmang@berkeley.edu or wenhao.chai@princeton.edu

Please include:
1. A zip/tar archive of your solutions following the format above
2. `metadata.json` with model and method information
3. (Optional) Local evaluation results if you ran them

## Leaderboard

Accepted submissions will be evaluated on our full test suite and results will be published on the [Frontier-CS Leaderboard](https://frontier-cs.org).
