# Contributing to Frontier-CS

<p align="">
  <a href="https://frontier-cs.org">
    <img src="assets/teaser.png" alt="Frontier-CS Logo" width="2000"/>
  </a>
</p>

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
└── testdata/        # Test cases
    ├── 1.in         # Sample input
    ├── 1.ans        # Hidden evaluation data used by the evaluator, e.g., reference score.
    ├── 2.in
    ├── 2.ans
    └── ...
```

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

Evaluator for scoring logic

(**NOTE**) the current judge returns the partial score by parsing the message returned by `testlib.h`, making sure your `quitp` follows the following format:
```cpp
quitp(score, "Ratio: %.9f [additional message str]", score, ...);
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
└── resources/           # Problem-specific code/data
```

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

```
config.yaml → set_up_env.sh → solve.sh → evaluate.sh → evaluator.py → score (0-100)
```

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
  requires_gpu: true       # GPU requirement
  resources:               # SkyPilot resources
    accelerators: "L4:1"
    cpus: "8+"
    memory: "32+"
  environment: "CUDA 12.2, Python 3.11, PyTorch 2.0+"
```

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

## Contact

For questions, submissions, or to request an invitation:

**Email**: qmang@berkeley.edu (general \& algorithmic problems), zhifei.li@berkeley.edu (research problems)

Please include:
- Your name and affiliation
- Area of expertise
- Type of contribution (algorithmic/research problem)
- Brief description of your proposed contribution
