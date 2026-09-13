#!/usr/bin/env python3
"""
Script to automatically count and update problem statistics in README.md
Run this script to update the problem counts in the README.
"""

import os
from pathlib import Path


def count_research_problems(research_dir: Path) -> int:
    """Count research problems by counting evaluator.py files, with special handling for poc_generation."""
    count = 0
    
    # Special case: poc_generation counts as 4 problems (4 subcategories)
    poc_dir = research_dir / 'problems' / 'poc_generation'
    if poc_dir.exists():
        count += 4
    
    # Count all evaluator.py files, excluding those in poc_generation and
    # formal_conjectures (auto-generated Lean problems, counted separately)
    for evaluator_file in research_dir.rglob('evaluator.py'):
        # Skip if it's under poc_generation directory
        if 'poc_generation' not in str(evaluator_file) and 'formal_conjectures' not in str(evaluator_file):
            count += 1
    
    return count


def count_algorithmic_problems(algorithmic_dir: Path) -> int:
    """Count algorithmic problems by counting numbered directories."""
    problems_dir = algorithmic_dir / 'problems'
    
    if not problems_dir.exists():
        return 0
    
    count = 0
    for item in problems_dir.iterdir():
        if item.is_dir() and item.name.isdigit():
            count += 1
    
    return count


def count_benchmark20_problems(benchmark20_dir: Path) -> int:
    """Count Frontier-CS 2.0 problems by counting evaluator.py files."""
    problems_dir = benchmark20_dir / 'problems'
    if not problems_dir.exists():
        return 0
    return sum(1 for _ in problems_dir.rglob('evaluator.py'))


def update_readme_badge(readme_path: Path, research_count: int, algo_count: int, benchmark20_count: int):
    """Update the README with current problem counts using badges."""
    
    if not readme_path.exists():
        print(f"README not found at {readme_path}")
        return
    
    content = readme_path.read_text()
    
    # Create the problem-count badges (HTML img tag format)
    research_badge = f'<img src="https://img.shields.io/badge/Research_Problems-{research_count}-blue" alt="Research Problems">'
    algo_badge = f'<img src="https://img.shields.io/badge/Algorithmic_Problems-{algo_count}-green" alt="Algorithmic Problems">'
    benchmark20_badge = f'<img src="https://img.shields.io/badge/2.0_Problems-{benchmark20_count}-purple" alt="2.0 Problems">'
    
    # Replace existing badges using regex
    import re
    
    # Replace Research Problems badge (HTML img tag format)
    content = re.sub(
        r'<img src="https://img\.shields\.io/badge/Research_Problems-\d+-blue" alt="Research Problems">',
        research_badge,
        content
    )
    
    # Replace Algorithmic Problems badge (HTML img tag format)
    content = re.sub(
        r'<img src="https://img\.shields\.io/badge/Algorithmic_Problems-\d+-green" alt="Algorithmic Problems">',
        algo_badge,
        content
    )

    if 'alt="2.0 Problems"' in content:
        content = re.sub(
            r'<img src="https://img\.shields\.io/badge/2\.0_Problems-\d+-purple" alt="2\.0 Problems">',
            benchmark20_badge,
            content
        )
    else:
        content = content.replace(algo_badge, f"{algo_badge}\n  {benchmark20_badge}")
    
    # Write back
    readme_path.write_text(content)
    print(f"✅ Updated README with counts: Research={research_count}, Algorithmic={algo_count}, 2.0={benchmark20_count}")


def main():
    # Get repository root
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent
    
    # Count problems
    research_dir = repo_root / 'research'
    algorithmic_dir = repo_root / 'algorithmic'
    benchmark20_dir = repo_root / '2.0'
    readme_path = repo_root / 'README.md'
    
    research_count = count_research_problems(research_dir)
    algo_count = count_algorithmic_problems(algorithmic_dir)
    benchmark20_count = count_benchmark20_problems(benchmark20_dir)
    
    print(f"📊 Problem Statistics:")
    print(f"   Research Problems: {research_count}")
    print(f"   Algorithmic Problems: {algo_count}")
    print(f"   2.0 Problems: {benchmark20_count}")
    print(f"   Total: {research_count + algo_count + benchmark20_count}")
    
    # Update README
    update_readme_badge(readme_path, research_count, algo_count, benchmark20_count)


if __name__ == '__main__':
    main()
