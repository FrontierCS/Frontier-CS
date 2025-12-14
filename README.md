<p align="">
  <a href="https://frontier-cs.org">
    <img src="assets/logo.png" alt="Frontier-CS Logo" width="2000"/>
  </a>
</p>

<h2 align="center">
Evolving Challenges for Evolving Intelligence
</h2>

<p align="center">
  <a href="https://frontier-cs.org"><img src="https://img.shields.io/badge/Website-frontier--cs.org-orange?logo=googlechrome" alt="Website"></a>
  <a href="https://frontier-cs.org/leaderboard"><img src="https://img.shields.io/badge/Leaderboard-View_Rankings-purple?logo=trophy" alt="Leaderboard"></a>
  <img src="https://img.shields.io/badge/Research_Problems-50-blue" alt="Research Problems">
  <img src="https://img.shields.io/badge/Algorithmic_Problems-115-green" alt="Algorithmic Problems">
</p>

## What is Frontier-CS?

**Frontier-CS** is an _unsolved_, _open-ended_, _verifiable_, and _diverse_ benchmark for evaluating AI on challenging computer science problems.

Think of it as an "exam" for AI, but instead of easy textbook questions, we give problems that are genuinely difficult: ones that researchers struggle with, that have no known optimal solutions, or that require deep expertise to even attempt.

## Why Frontier-CS?

Current benchmarks are becoming too easy. Models score 90%+ on many existing coding benchmarks, but that doesn't mean they can actually do useful research or solve real-world engineering challenges.

**Frontier-CS is different:**

|            | Traditional Benchmarks          | Frontier-CS                                             |
| ---------- | ------------------------------- | ------------------------------------------------------- |
| Difficulty | Often saturated (90%+ scores)   | _Unsolved_: no model has achieved perfect scores        |
| Problems   | Textbook-style, known solutions | _Open-ended_ research & optimization challenges         |
| Evaluation | Binary pass/fail                | _Verifiable_ continuous scoring, always room to improve |
| Scope      | Usually one domain              | _Diverse_: systems, ML, algorithms, security, and more  |

**[Leaderboard →](https://frontier-cs.org/leaderboard)** | Browse all problems at [frontier-cs.org](https://frontier-cs.org)

## Getting Started

### Installation

```bash
git clone https://github.com/FrontierCS/Frontier-CS.git
cd Frontier-CS

# Install dependencies (using uv, recommended)
uv sync

# Or with pip:
pip install -e .
```

### Try it yourself

<p align="center">
  <img src="assets/teaser.png" alt="Example Problem" width="800"/>
</p>

```bash
# Run the example solution
frontier-eval <PROBLEM_ID> examples/<PROBLEM_ID>_solution.py
```

<!-- TODO: Replace <PROBLEM_ID> with actual problem, add example solution to examples/ -->

### Research Problems

```bash
# List all problems
frontier-eval --list

# Evaluate a solution (requires Docker)
frontier-eval flash_attn <your_solution.py>

# Evaluate on cloud (requires SkyPilot)
frontier-eval flash_attn <your_solution.py> --skypilot
```

See [research/README.md](research/README.md) for full documentation.

### Algorithmic Problems

```bash
# Start the judge server
cd algorithmic && docker compose up -d

# Evaluate a solution
frontier-eval --algorithmic 1 <your_solution.cpp>
```

See [algorithmic/README.md](algorithmic/README.md) for full documentation.

### Python API

```python
from frontier_cs import FrontierCSEvaluator

evaluator = FrontierCSEvaluator()

# Evaluate a research problem
result = evaluator.evaluate("research", problem_id="flash_attn", code=my_code)
print(f"Score: {result.score}")

# Evaluate an algorithmic problem
result = evaluator.evaluate("algorithmic", problem_id=1, code=cpp_code)
print(f"Score: {result.score}")
```

## Submitting Results

We release partial test cases so you can develop and debug locally. For full evaluation and leaderboard inclusion, submit your solutions to qmang@berkeley.edu, or wenhao.chai@princeton.edu, or zhifei.li@berkeley.edu following the instructions in [SUBMIT.md](SUBMIT.md).

## Acknowledgments

Some problems are adapted from [ALE-bench](https://github.com/SakanaAI/ALE-Bench) and [AI-Driven Research for Systems (ADRS)](https://ucbskyadrs.github.io/).

## Citing Us

If you use Frontier-CS in your research, please cite:

```bibtex

```
