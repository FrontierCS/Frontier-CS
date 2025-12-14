<p align="">
  <a href="https://frontier-cs.org">
    <img src="assets/logo.png" alt="Frontier-CS Logo" width="2000"/>
  </a>
</p>

[![Website](https://img.shields.io/badge/Website-frontier--cs.org-orange?logo=googlechrome)](https://frontier-cs.org) ![Research Problems](https://img.shields.io/badge/Research_Problems-50-blue) ![Algorithmic Problems](https://img.shields.io/badge/Algorithmic_Problems-114-green)

**Frontier-CS** is an _unsolved_, _verifiable_, _open-ended_, and _diverse_ dataset for evaluating frontier models on challenging computer science problems, ranging from optimization problems in real research to competitive programming–style open challenges.

Whether you are benchmarking LLM agents, evaluating code generation models, or stress-testing reasoning capabilities, Frontier-CS provides a comprehensive suite of tasks designed for rigorous and practical evaluation.

Frontier-CS consists of two categories:

- **Algorithmic Problems**: Competitive programming challenges, including optimization, construction, and interactive problems. For each algorithmic problem, we release the full problem statement, evaluator, and _one_ public test case.

- **Research Problems**: Real-world systems challenges, including GPU kernels, distributed scheduling, ML pipelines, database optimization, and security exploits. For research problems, we release all data and scripts required to fully reproduce the results.

Frontier-CS is continuously expanding with new and increasingly challenging tasks contributed by our community.

## Quickstart

### Installation

```bash
git clone https://github.com/FrontierCS/Frontier-CS.git
cd Frontier-CS

# Install Python dependencies (using uv, recommended)
uv sync

# Or with pip:
pip install -e .
```

### API Keys

Set environment variables for the models you want to use:

```bash
export OPENAI_API_KEY="sk-..."        # For GPT models
export ANTHROPIC_API_KEY="sk-ant-..." # For Claude models
export GOOGLE_API_KEY="..."           # For Gemini models
```

### Research Problems

Real-world research problems requiring domain expertise in areas including machine learning, operating systems, distributed systems, GPU computing, databases, programming languages, and security.

**CLI Evaluation:**

```bash
# List available problems
frontier-eval --list

# Evaluate a single problem (requires Docker)
frontier-eval flash_attn <your_solution.py>

# Evaluate with SkyPilot (cloud)
frontier-eval flash_attn <your_solution.py> --skypilot

# Evaluate multiple problems
frontier-eval --problems flash_attn,cross_entropy <your_solution.py>
```

**Generate Solutions:**

```bash
cd research
python generate_solutions.py --model <model_name>
```

### Algorithmic Problems

Competitive programming-style problems with automated judging (see [algorithmic/README.md](algorithmic/README.md) for details).

**Start Judge Server:**

```bash
cd algorithmic && docker compose up -d
```

**CLI Evaluation:**

```bash
# Evaluate your solution for problem 1
frontier-eval --algorithmic 1 <your_solution.cpp>
```

### Evaluation API

Unified Python API for evaluating both algorithmic and research problems:

```python
from frontier_cs import FrontierCSEvaluator

evaluator = FrontierCSEvaluator()

# Algorithmic problem (requires judge server)
result = evaluator.evaluate("algorithmic", problem_id=1, code=cpp_code)
print(f"Score: {result.score}")

# Research problem (requires Docker)
result = evaluator.evaluate("research", problem_id="flash_attn", code=py_code)
print(f"Score: {result.score}")

# Research problem with SkyPilot (cloud)
result = evaluator.evaluate("research", problem_id="flash_attn", code=py_code,
                           backend="skypilot")

# Batch evaluation
results = evaluator.evaluate_batch("research",
                                  problem_ids=["flash_attn", "cross_entropy"],
                                  code=py_code)
```

## Submit Your Results

We currently release partial test cases for algorithmic problems to allow users to test and debug their solutions. To submit your solutions for full evaluation and have it included in the leaderboard, please send your solutions to qmang@berkeley.edu or wenhao.chai@princeton.edu following the instructions in [SUBMIT_RESULTS.md](SUBMIT_RESULTS.md).

## Citing Us

If you found Frontier-CS useful, please cite us as:

```bibtex

```
