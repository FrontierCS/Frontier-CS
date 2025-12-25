"""
Batch evaluation support for Frontier-CS.

Provides batch and incremental evaluation of multiple solutions across multiple problems.
"""

from .evaluator import BatchEvaluator
from .state import EvaluationState, PairResult
from .pair import Pair, expand_pairs, read_pairs_file, scan_solutions_dir

__all__ = [
    "BatchEvaluator",
    "EvaluationState",
    "PairResult",
    "Pair",
    "expand_pairs",
    "read_pairs_file",
    "scan_solutions_dir",
]
