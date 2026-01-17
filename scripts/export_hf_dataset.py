#!/usr/bin/env python3
"""Export Frontier-CS problems to HuggingFace-compatible format."""

import json
import os
from pathlib import Path

def export_dataset(output_dir: str = "hf_export"):
    base_path = Path(__file__).parent.parent
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    problems = []

    # Algorithmic problems
    algo_path = base_path / "algorithmic" / "problems"
    for problem_dir in sorted(algo_path.iterdir()):
        if not problem_dir.is_dir():
            continue

        statement = ""
        config = ""

        statement_file = problem_dir / "statement.txt"
        if statement_file.exists():
            statement = statement_file.read_text(encoding="utf-8")

        config_file = problem_dir / "config.yaml"
        if config_file.exists():
            config = config_file.read_text(encoding="utf-8")

        problems.append({
            "problem_id": problem_dir.name,
            "category": "algorithmic",
            "statement": statement,
            "config": config,
        })

    # Research problems
    research_path = base_path / "research" / "problems"
    for category_dir in sorted(research_path.iterdir()):
        if not category_dir.is_dir():
            continue

        readme_file = category_dir / "readme"
        config_file = category_dir / "config.yaml"

        if readme_file.exists() or config_file.exists():
            statement = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""
            config = config_file.read_text(encoding="utf-8") if config_file.exists() else ""

            problems.append({
                "problem_id": category_dir.name,
                "category": "research",
                "statement": statement,
                "config": config,
            })
        else:
            for subproblem_dir in sorted(category_dir.iterdir()):
                if not subproblem_dir.is_dir():
                    continue

                readme_file = subproblem_dir / "readme"
                config_file = subproblem_dir / "config.yaml"

                statement = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""
                config = config_file.read_text(encoding="utf-8") if config_file.exists() else ""

                if statement or config:
                    problems.append({
                        "problem_id": f"{category_dir.name}/{subproblem_dir.name}",
                        "category": "research",
                        "statement": statement,
                        "config": config,
                    })

    # Write JSONL
    output_file = output_path / "problems.jsonl"
    with open(output_file, "w", encoding="utf-8") as f:
        for p in problems:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

    print(f"Exported {len(problems)} problems to {output_file}")

    # Also create train split for HF compatibility
    data_dir = output_path / "data"
    data_dir.mkdir(exist_ok=True)

    # Use .json extension (HF auto-loader recognizes this better than .jsonl)
    with open(data_dir / "test-00000-of-00001.json", "w", encoding="utf-8") as f:
        for p in problems:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

    print(f"Created HF-compatible data at {data_dir}")

    # Create dataset card (README.md)
    algo_count = sum(1 for p in problems if p["category"] == "algorithmic")
    research_count = sum(1 for p in problems if p["category"] == "research")

    readme_content = f"""---
license: apache-2.0
task_categories:
  - text-generation
language:
  - en
tags:
  - code
  - algorithms
  - competitive-programming
  - research
size_categories:
  - n<1K
---

# Frontier-CS Dataset

A benchmark dataset for evaluating AI systems on challenging computer science problems.

## Dataset Description

This dataset contains {len(problems)} problems across two categories:
- **Algorithmic**: {algo_count} competitive programming problems with automated judging
- **Research**: {research_count} open-ended research problems

## Dataset Structure

Each problem has the following fields:
- `problem_id`: Unique identifier for the problem
- `category`: Either "algorithmic" or "research"
- `statement`: The problem statement text
- `config`: YAML configuration for evaluation

## Usage

```python
from datasets import load_dataset

dataset = load_dataset("FrontierCS/Frontier-CS")
```

## License

Apache 2.0
"""
    with open(output_path / "README.md", "w", encoding="utf-8") as f:
        f.write(readme_content)

    print(f"Created dataset card README.md")

if __name__ == "__main__":
    export_dataset()
