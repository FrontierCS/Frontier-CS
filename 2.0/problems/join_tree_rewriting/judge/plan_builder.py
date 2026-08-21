"""Build executable 2NSA plans from the authors' IR and rewrite hook."""

from __future__ import annotations

import argparse
import contextlib
import copy
import json
import subprocess
import sys
from io import StringIO
from pathlib import Path


def _leaves(bp, plan):
    if isinstance(plan, bp.LeafNode):
        return {plan.relation_name: (frozenset(plan.attrs()), plan.ec)}
    left = _leaves(bp, plan.left_child)
    right = _leaves(bp, plan.right_child)
    if left.keys() & right.keys():
        raise ValueError("a relation appears more than once")
    left.update(right)
    return left


def _validate(bp, original, candidate) -> None:
    if _leaves(bp, original) != _leaves(bp, candidate):
        raise ValueError("rewriting changed relation leaves or annotations")
    joins = 0

    def visit(node):
        nonlocal joins
        if isinstance(node, bp.LeafNode):
            return node.attrs()
        joins += 1
        left = visit(node.left_child)
        right = visit(node.right_child)
        if node.join_attrs() != left.intersection(right):
            raise ValueError("rewriting changed an equijoin predicate")
        return left | right

    visit(candidate)
    if joins != len(_leaves(bp, original)) - 1 or not bp.is_well_behaved(candidate):
        raise ValueError("rewriting did not return a lowerable binary tree")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--app", required=True)
    parser.add_argument("--workloads", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--upstream", required=True)
    args = parser.parse_args()

    app = Path(args.app)
    workloads = Path(args.workloads)
    output = Path(args.output)
    upstream = Path(args.upstream)
    output.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(app / "2phase_nsa"))
    from binary_plan import binary_plan as bp
    from binary_plan.rewrite_policy import rewrite_plan
    from binary_plan.to_semijoin_plan import MultiSemiJoin
    from binary_plan.util import ir_file_to_binary_plan

    for ir_path in sorted(workloads.glob("*.json"), key=lambda p: int(p.stem)):
        original = ir_file_to_binary_plan(str(ir_path))
        pristine = copy.deepcopy(original)
        with contextlib.redirect_stdout(StringIO()), contextlib.redirect_stderr(StringIO()):
            rewritten = rewrite_plan(original)
        _validate(bp, pristine, rewritten)
        template = output / f"{ir_path.stem}.template"
        template.write_text(
            MultiSemiJoin.from_wellbehaved_plan(rewritten).to_yannakakis_template(),
            encoding="utf-8",
        )
        for script in ("finalize_template.py", "yannakakis_from_template.py"):
            proc = subprocess.run(
                [sys.executable, str(upstream / script), "-t", str(template), "-b", str(ir_path)],
                capture_output=True,
                text=True,
                timeout=20,
            )
            if proc.returncode != 0:
                raise RuntimeError(f"upstream plan conversion failed for query {ir_path.stem}")
        if not template.with_suffix(".json").is_file():
            raise RuntimeError(f"upstream plan conversion produced no plan for query {ir_path.stem}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
