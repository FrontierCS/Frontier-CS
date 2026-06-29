"""Greedy-decoding correctness gate.

A serving/scheduler optimization must not change what the model generates. At
temperature 0 the patched server must reproduce the baseline's outputs
token-for-token on a small fixed prompt set. The baseline outputs are collected
once (and cached alongside the baseline metrics); the patched outputs are then
compared against that reference.

The prompts are generic and benchmark-agnostic on purpose.
"""

from __future__ import annotations

from typing import Any

from .settings import EvalSettings

SMOKE_PROMPTS = (
    "Write a Python function that returns the n-th Fibonacci number.",
    "Explain what a hash map is in two sentences.",
    "Reverse the string 'serving' and return only the result.",
    "What is the time complexity of binary search? Answer in one line.",
    "Write a one-line shell command to count lines in a file named data.txt.",
    "Summarize the difference between a list and a tuple in Python.",
    "Given the list [3,1,2], return it sorted ascending.",
    "Write a regular expression that matches an IPv4 address.",
    "Convert the decimal number 42 to binary.",
    "Name three common HTTP status codes and what they mean.",
    "Write a SQL query selecting all rows from a table named users.",
    "What does the 'git rebase' command do? One sentence.",
)


def collect_greedy_outputs(base_url: str, *, settings: EvalSettings, n: int) -> dict[str, str]:
    from openai import OpenAI

    client = OpenAI(base_url=base_url, api_key="EMPTY", timeout=300.0)
    prompts = list(SMOKE_PROMPTS)[: max(1, n)]
    outputs: dict[str, str] = {}
    for prompt in prompts:
        completion = client.chat.completions.create(
            model=settings.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=256,
            seed=0,
        )
        outputs[prompt] = completion.choices[0].message.content or ""
    return outputs


def compare_outputs(reference: dict[str, str], candidate: dict[str, str]) -> tuple[bool, int]:
    mismatches = 0
    for prompt, reference_text in reference.items():
        if candidate.get(prompt, "") != reference_text:
            mismatches += 1
    return mismatches == 0, mismatches
