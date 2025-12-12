<p align="">
  <a href="https://frontier-cs.org">
    <img src="assets/logo.png" alt="Frontier-CS Logo" width="2000"/>
  </a>
</p>

[![Website](https://img.shields.io/badge/Website-frontier--cs.org-orange?logo=googlechrome)](https://frontier-cs.org) ![Research Problems](https://img.shields.io/badge/Research_Problems-50-blue) ![Algorithmic Problems](https://img.shields.io/badge/Algorithmic_Problems-110-green)


**Frontier-CS** is an *unsolved*, *verifiable*, *open-ended*, and *diverse* dataset for evaluating frontier models on challenging computer science problems, ranging from optimization problems in real research to competitive programming–style open challenges.

Whether you are benchmarking LLM agents, evaluating code generation models, or stress-testing reasoning capabilities, Frontier-CS provides a comprehensive suite of tasks designed for rigorous and practical evaluation.

Frontier-CS consists of two categories:

- **Algorithmic Problems**: Competitive programming challenges, including optimization, construction, and interactive problems. For each algorithmic problem, we release the full problem statement, evaluator, and *one* public test case.  

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

Real-world research problems requiring domain expertise in areas including machine learning, operating systems, distributed systems, GPU computing, machine learning, databases, programming languages, and security.


```bash
cd research

# Generate solutions with an LLM
python generate_oneshot_gpt.py --model <model_name>

# Run evaluation locally (requires Docker)
chmod -x ./main_loop.sh
./main_loop.sh

# Or run on cloud (requires SkyPilot)
python scripts/skypilot_per_solution.py --max-concurrent 4
```

### Algorithmic Problems

Competitive programming-style problems with automated judging (see [algorithmic/README.md](algorithmic/README.md) for details).

**Start Judge Server:**

```bash
cd algorithmic && docker-compose up -d
```

**Run Benchmark:**

```bash
python scripts/run_tests.py <model_name>
```

**Simple Evaluation API:**

You can programmatically evaluate solutions using the Python API after setting up the judge server docker, which provides a convenient interface to integrate with your customized agents or evolving frameworks.

```python
from src.evaluator import FrontierCSEvaluator

# Initialize evaluator
judge = FrontierCSEvaluator()

# Evaluate a C++ solution
cpp_code = """
#include <bits/stdc++.h>
using namespace std;
int main() {
    int n;
    cin >> n;
    cout << n * 2 << endl;
    return 0;
}
"""

# Get score (0-100)
score = judge.evaluate_solution(
    problem_track="algorithmic",
    problem_id=1,
    solution_code=cpp_code
)
print(f"Score: {score}")
```
## Submit Your Results
We currently release partial test cases for algorithmic problems to allow users to test and debug their solutions. To submit your solutions for full evaluation and have it included in the leaderboard, please send your solutions to qmang@berkeley.edu or wenhao.chai@princeton.edu following the instructions in [SUBMIT_RESULTS.md](SUBMIT_RESULTS.md).

## Citing Us

If you found Frontier-CS useful, please cite us as:

```bibtex

```
