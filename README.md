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
  <a href="https://discord.gg/k4hd2nU4UE"><img src="https://img.shields.io/badge/Discord-Join_Community-5865F2?logo=discord&logoColor=white" alt="Discord"></a>
  <a href="https://deepwiki.com/FrontierCS/Frontier-CS"><img src="https://img.shields.io/badge/DeepWiki-Documentation-blue?logo=bookstack&logoColor=white" alt="DeepWiki"></a>
  <br>
  <a href="https://arxiv.org/abs/2512.15699"><img src="https://img.shields.io/badge/arXiv-2512.15699-b31b1b?logo=arxiv&logoColor=white" alt="arXiv"></a>
  <a href="https://huggingface.co/datasets/FrontierCS/Frontier-CS" target="_blank">
    <img src="https://img.shields.io/badge/Hugging_Face-🤗%20Datasets-orange" alt="Hugging Face">
  </a>
  <img src="https://img.shields.io/badge/Research_Problems-66-blue" alt="Research Problems">
  <img src="https://img.shields.io/badge/Algorithmic_Problems-172-green" alt="Algorithmic Problems">
</p>

## What is Frontier-CS?

**Frontier-CS** is an _unsolved_, _open-ended_, _verifiable_, and _diverse_ benchmark for evaluating AI on challenging computer science problems.

Think of it as an "exam" for AI, but instead of easy textbook questions, we give problems that are genuinely difficult: ones that researchers struggle with, that have no known optimal solutions, or that require deep expertise to even attempt.

## Why Frontier-CS?

Current benchmarks are becoming too easy. Models score 90%+ on many existing coding benchmarks, but that doesn't mean they can actually do useful research or solve real-world engineering challenges.

**Frontier-CS is different:**

|            | Traditional Benchmarks                     | Frontier-CS                                             |
| ---------- | ------------------------------------------ | ------------------------------------------------------- |
| Difficulty | Often saturated with evolving intelligence | _Unsolved_: no solution has achieved perfect scores     |
| Problems   | Textbook-style, known solutions            | _Open-ended_ research & optimization challenges         |
| Evaluation | Binary pass-or-fail                        | _Verifiable_ continuous scoring, always room to improve |
| Scope      | Usually one domain                         | _Diverse_: systems, ML, algorithms, security, and more  |

**[Leaderboard →](https://frontier-cs.org/leaderboard)** | Browse example problems at [frontier-cs.org](https://frontier-cs.org)

## Getting Started

### Installation

**Requirements:** Python 3.11+, Docker 24+ (for local evaluation)

```bash
git clone https://github.com/FrontierCS/Frontier-CS.git
cd Frontier-CS

# Install dependencies (using uv, recommended)
uv sync

# Or with pip:
pip install -e .
```

### Try it yourself

Here's [Algorithmic Problem 0](algorithmic/problems/0/statement.txt) - try to beat GPT-5!

```bash
# Run the example solution (Human Expert Solution)
frontier eval --algorithmic 0 algorithmic/problems/0/examples/reference.cpp

# Run the example solution (GPT-5 Thinking Solution)
frontier eval --algorithmic 0 algorithmic/problems/0/examples/gpt5.cpp

# Try your own solution!
frontier eval --algorithmic 0 <your_solution.cpp>
```

<p align="center">
  <img src="assets/teaser.png" alt="Example Problem" width="800"/>
</p>

### Research Problems

```bash
# List all problems
frontier list

# Evaluate a generated solution locally for flash_attn problem (requires Docker)
frontier eval flash_attn <your_solution.py>

# Evaluate on cloud (requires SkyPilot)
frontier eval flash_attn <your_solution.py> --skypilot
```

See [research/README.md](research/README.md) for full documentation.

### Algorithmic Problems

```bash
# Evaluate a solution locally (requires Docker)
frontier eval --algorithmic 1 <your_solution.cpp>

# Evaluate on cloud (requires SkyPilot)
frontier eval --algorithmic 1 <your_solution.cpp> --skypilot
```

See [algorithmic/README.md](algorithmic/README.md) for full documentation.

### Raw Score

Frontier-CS supports unbounded scoring, enabling open-ended evaluation compatible with algorithm evolution frameworks such as OpenEvolve.

```bash
# Get unbounded score (without clipping to 100)
frontier eval --unbounded flash_attn <your_solution.py>
frontier eval --algorithmic --unbounded 1 <your_solution.cpp>
```

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

# Get unbounded score for algorithmic problems
result = evaluator.evaluate("algorithmic", problem_id=1, code=cpp_code, unbounded=True)
print(f"Score (bounded): {result.score}")
print(f"Score (unbounded): {result.score_unbounded}")
```

## Submitting Results

Reference solutions and full test cases are withheld. We release partial test cases so you can develop and debug locally. For full evaluation and leaderboard inclusion, please follow the instructions in [SUBMIT.md](SUBMIT.md) and submit your solutions to qmang@berkeley.edu, wenhao.chai@princeton.edu, huanzhimao@berkeley.edu, or zhifei.li@berkeley.edu.

Questions? Join our [Discord](https://discord.gg/k4hd2nU4UE)

## Acknowledgments

Some problems are adapted from [ALE-bench](https://github.com/SakanaAI/ALE-Bench) and [AI-Driven Research for Systems (ADRS)](https://ucbskyadrs.github.io/).

## Citing Us

If you use Frontier-CS in your research, please cite:

```bibtex
@misc{mang2025frontiercsevolvingchallengesevolving,
      title={FrontierCS: Evolving Challenges for Evolving Intelligence},
      author = {Qiuyang Mang and Wenhao Chai and Zhifei Li and Huanzhi Mao and
                Shang Zhou and Alexander Du and Hanchen Li and Shu Liu and
                Edwin Chen and Yichuan Wang and Xieting Chu and Zerui Cheng and
                Yuan Xu and Tian Xia and Zirui Wang and Tianneng Shi and
                Jianzhu Yao and Yilong Zhao and Qizheng Zhang and Charlie Ruan and
                Zeyu Shen and Kaiyuan Liu and Runyuan He and Dong Xing and
                Zerui Li and Zirong Zeng and Yige Jiang and Lufeng Cheng and
                Ziyi Zhao and Youran Sun and Wesley Zheng and Meiyuwang Zhang and
                Ruyi Ji and Xuechang Tu and Zihan Zheng and Zexing Chen and
                Kangyang Zhou and Zhaozi Wang and Jingbang Chen and
                Aleksandra Korolova and Peter Henderson and Pramod Viswanath and
                Vijay Ganesh and Saining Xie and Zhuang Liu and Dawn Song and
                Sewon Min and Ion Stoica and Joseph E. Gonzalez and
                Jingbo Shang and Alvin Cheung},
      year={2025},
      eprint={2512.15699},
      archivePrefix={arXiv},
      primaryClass={cs.LG},
      url={https://arxiv.org/abs/2512.15699},
}
```
