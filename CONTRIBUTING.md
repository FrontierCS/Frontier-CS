# Contributing to Frontier-CS

> **For Problem Contributors**: Guidelines for creating and submitting new problems to Frontier-CS.

Frontier-CS is currently an **invitation-only** project for new problems.
Please create a GitHub pull request (PR) with your proposed problem following the guidelines below. After your PR is reviewed and merged, please send any hidden test data and reference solutions to the contact email provided at the end of this document.


- [Algorithmic Problems](#algorithmic-problems)
  - [Problem Submission Process](#problem-submission-process)
  - [Problem Structure](#problem-structure)
  - [Required Files](#required-files)
  - [Hidden Test Data and Human Reference](#hidden-test-data-and-human-reference)
- [Research Problems](#research-problems)
  - [Problem Submission Process](#research-problem-submission-process)
  - [Problem Structure](#research-problem-structure)
  - [Evaluation Flow](#evaluation-flow)
  - [Step by Step](#step-by-step)
  - [Problem Hierarchy](#problem-hierarchy-categories-and-variants)
- [Contact](#contact)

## Algorithmic Problems

### Problem Submission Process

1. **Invitation Required**: Only invited contributors can submit algorithmic problems
2. **Internal Review**: All problems undergo internal review by the Frontier-CS team
3. **Problem Numbering**: After approval, problems are assigned a unique numerical ID
4. **Structure Compliance**: Problems must follow the required directory structure

### Problem Structure

Each algorithmic problem must be organized in the following directory structure:

```
algorithmic/problems/{problem_id}/
├── config.yaml       # Problem configuration (time limit, memory limit, checker)
├── statement.txt     # Problem description and requirements
├── chk.cc or interactor.cc (for interactive problems)          # Evaluator
├── reference.cpp     # Reference solution (required for CI validation)
└── testdata/        # Test cases
    ├── 1.in         # Sample input
    ├── 1.ans        # Hidden evaluation data used by the evaluator, e.g., reference score.
    ├── 2.in
    ├── 2.ans
    └── ...
```

> **Note**: The `reference.cpp` is required for CI validation. When you submit a PR, the CI will automatically run your reference solution and verify it achieves score > 0.

### Required Files

#### config.yaml

Defines the problem configuration:

```yaml
type: default          # Problem type
time: 1s              # Time limit (e.g., 1s, 2s, 5s)
memory: 1024m         # Memory limit (e.g., 512m, 1024m, 2048m)
checker: chk.cc       # Custom checker file (optional)
subtasks:
  - score: 100        # Total score for this subtask
    n_cases: 10       # Number of test cases (= 1 for public version)
```

#### statement.txt

The problem statement should include:

- **Problem Description**: Clear description of the problem
- **Input Format**: Detailed specification of input format
- **Output Format**: Detailed specification of output format
- **Scoring**: Explanation of how solutions are scored
- **Time Limit**: Execution time limit
- **Memory Limit**: Memory usage limit
- **Sample Input/Output**: At least one example with explanation

#### chk.cc / interactor.cc (for interactive problems)

*Support partial score*

the current judge returns the partial score by parsing the message returned by `testlib.h`, making sure your `quitp` follows the following format:
```cpp
quitp(score, "Ratio: %.9f [additional message str]", score, ...);
```
To support raw score, use:
```cpp
quitp(score_ratio, "Value: %lld. Ratio: %.4f, RatioUnbounded: %.4f", score, score_ratio, unbounded_ratio);
```
#### testdata/

Test cases with inputs (`.in`) and expected outputs (`.ans`):

- `1.in`, `1.ans`: First test case
- `2.in`, `2.ans`: Second test case
- etc.

### Hidden Test Data and Human Reference

For security and evaluation integrity:

- **Hidden test data** (not in public repository)
- **Human reference solutions** (baseline implementations)

Please send these materials to: qmang@berkeley.edu once your PR is merged.

Include in your email:
- Problem ID (if assigned) or proposed problem name
- Complete test data set (all `.in` and `.ans` files)
- Reference solution(s) with explanation
- Any additional notes on test case design

## Research Problems

Research problems focus on systems optimization, ML systems, databases, compilers, and security challenges.

### Research Problem Submission Process

1. **Invitation Required**: Only invited contributors can submit research problems
2. **Internal Review**: Problems undergo internal review for quality and feasibility
3. **Tag Assignment**: Problems are assigned appropriate category tags (os, hpc, ai, db, pl, security)

### Research Problem Structure

Each research problem follows a standardized interface:

```
research/{problem_name}/
├── config.yaml          # Dependencies, datasets, runtime config
├── set_up_env.sh        # Environment setup script
├── evaluate.sh          # Evaluation entry point
├── evaluator.py         # Scoring logic
├── readme               # Problem description
├── reference.{py,cpp}   # Reference solution (required for CI, extension per language)
└── resources/           # Problem-specific code/data
```

> **Note**: A reference solution is required for CI validation. Use `reference.py` for Python problems or `reference.cpp` if `language: cpp` in config.yaml. The CI will automatically run your reference solution and verify it achieves score > 0.

### Solution Interface

Solutions implement a `Solution` class in `solution.py`:

```python
class Solution:
    def __init__(self):
        pass

    def solve(self, *args):
        # Returns: solution output (format varies by problem)
        pass
```

### Evaluation Flow

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

### Step by Step
#### 1. Create Problem Directory

```bash
mkdir -p research/{problem_name}/resources
```

#### 2. Create `config.yaml`

```yaml
tag: hpc                   # Category: os, hpc, ai, db, pl, security

dependencies:
  uv_project: resources    # Optional: uv project in resources/

datasets: []               # Optional: dataset URLs

runtime:
  timeout_seconds: 1800    # Evaluation timeout
  environment: "CUDA 12.2, Python 3.11, PyTorch 2.0+"  # Description for LLM prompts, used by generate_solutions.py
  docker:
    image: andylizf/triton-tlx:tlx-nv-cu122  # Docker image
    gpu: true              # GPU requirement
    dind: false            # Set true for Docker-in-Docker (auto-installs Docker CLI)
  resources:               # SkyPilot resources
    accelerators: "L4:1"
    cpus: "8+"
    memory: "32+"
```

The framework automatically:
- Installs dependencies from `uv_project` via `uv sync`
- Installs Docker CLI inside the container when `dind: true`

#### Protecting Pre-installed Packages (uv_overrides.txt)

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

#### 3. Create Evaluation Scripts

**set_up_env.sh**: Prepare environment
```bash
#!/bin/bash
# Install dependencies, download data, etc.
```

**evaluate.sh**: Run evaluation
```bash
#!/bin/bash
python evaluator.py
```

**evaluator.py**: Score the solution (last line must be numeric score)
```python
# ... evaluation logic ...
print(score)  # Must be last line!
```

#### 4. Register the Problem

Add to `research/problems.txt`:
```
research/{problem_name}
```

### Problem Hierarchy: Categories and Variants

Research problems follow a hierarchical structure:

```
Problem (e.g., gemm_optimization, poc_generation)
└── Category (e.g., squares, heap_buffer_overflow)
    └── Variant (e.g., arvo_21000)
```

| Level | Evaluation | Reporting |
|-------|------------|-----------|
| **Category** | — | Scores aggregated for leaderboard |
| **Variant** | Evaluated independently | Contributes to category score |

#### Example: Simple Variants

```
research/gemm_optimization/
├── squares/           # Variant (category = squares)
│   ├── config.yaml
│   ├── readme
│   └── evaluator.py
├── rectangles/        # Variant (category = rectangles)
└── transformerish/    # Variant (category = transformerish)
```

#### Example: Nested Variants

For problems with many variants per category:

```
research/poc_generation/
├── heap_buffer_overflow/       # Category
│   ├── config.yaml             # Category-level config (tag only)
│   ├── arvo_21000/             # Variant
│   │   ├── config.yaml
│   │   ├── readme
│   │   └── evaluator.py
│   └── arvo_47101/             # Variant
└── stack_buffer_overflow/      # Category
    └── ...
```

#### Registering Problems

Add each **variant** (not category) to `problems.txt`:
```
research/gemm_optimization/squares
research/gemm_optimization/rectangles
research/poc_generation/heap_buffer_overflow/arvo_21000
research/poc_generation/heap_buffer_overflow/arvo_47101
```

## CI Validation

When you submit a PR that adds or modifies problems, CI will automatically validate your changes:

1. **Detection**: CI detects which problems were modified via `git diff`
2. **Validation**: For each modified problem, CI runs the reference solution
3. **Pass Criteria**: Reference solution must achieve score > 0

### Reference Solution Requirements

| Track | File | Location |
|-------|------|----------|
| Algorithmic | `reference.cpp` | `algorithmic/problems/{id}/reference.cpp` |
| Research | `reference.{py,cpp}` | `research/problems/{name}/reference.{ext}` (extension per `language` in config.yaml) |

If the reference solution is missing or scores 0, the PR will be blocked from merging.

> **Important**: The reference solution must achieve score > 0. This is a design choice to ensure the evaluator is working correctly - a score > 0 proves that the evaluation pipeline can successfully compile/run the solution and produce a valid score. If the reference only scores 0, we cannot distinguish between "evaluator error" and "valid solution with no improvement". For problems that measure speedup against a baseline, the reference must be **faster than the baseline**, not just a copy of it.

### Local Testing

Before submitting a PR, test your reference solution locally:

```bash
# Algorithmic
frontier eval algorithmic {id} algorithmic/problems/{id}/reference.cpp

# Research (use .py or .cpp based on problem's language config)
frontier eval research {name} research/problems/{name}/reference.{ext}
```

## Contact

For questions, submissions, or to request an invitation:

**Email**: qmang@berkeley.edu (general \& algorithmic problems), zhifei.li@berkeley.edu (research problems)

Please include:
- Your name and affiliation
- Area of expertise
- Type of contribution (algorithmic/research problem)
- Brief description of your proposed contribution
