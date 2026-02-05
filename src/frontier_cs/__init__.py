"""
Frontier-CS: Evaluation framework for frontier CS problems.

Usage:
    from frontier_cs import SingleEvaluator

    evaluator = SingleEvaluator()

    # Algorithmic problems (uses Docker by default)
    score = evaluator.evaluate("algorithmic", problem_id=1, code=cpp_code)

    # Research problems (uses SkyPilot by default)
    score = evaluator.evaluate("research", problem_id="flash_attn", code=py_code)

    # Override backend
    score = evaluator.evaluate("research", problem_id="flash_attn", code=py_code,
                               backend="docker")

    # Batch evaluation with incremental progress
    from frontier_cs.batch import BatchEvaluator

    batch = BatchEvaluator(results_dir="results/gpt5")
    batch.evaluate_model("gpt-5", problems=["flash_attn", "cross_entropy"])

    # Batch evaluation with bucket storage (for SkyPilot)
    batch = BatchEvaluator(
        results_dir="results/gpt5",
        backend="skypilot",
        bucket_url="s3://my-bucket/frontier-results",
    )
    batch.# Use batch.scan_solutions_dir() or evaluate_pairs()
"""

from .single_evaluator import SingleEvaluator
from .config import RuntimeConfig, ResourcesConfig, DockerConfig, ProblemConfig
from .runner import EvaluationResult

__all__ = [
    "SingleEvaluator",
    "RuntimeConfig",
    "ResourcesConfig",
    "DockerConfig",
    "ProblemConfig",
    "EvaluationResult",
]

__version__ = "0.1.0"
