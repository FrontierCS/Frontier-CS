#!/usr/bin/env python3
from __future__ import annotations
"""
CLI interface for Frontier-CS evaluation.

Usage:
    # Single problem evaluation
    frontier eval research flash_attn solution.py
    frontier eval algorithmic 1 solution.cpp

    # Override backend
    frontier eval research flash_attn solution.py --backend docker

    # All problems for a solution
    frontier eval research --all-problems solution.py

    # List problems
    frontier list
    frontier list research
    frontier list algorithmic
    frontier list 2.0

    # Batch evaluation
    frontier batch research
    frontier batch algorithmic
    frontier batch research --solutions-dir path/to/solutions
"""

import argparse
import contextlib
import json
import logging
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
import warnings
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional

warnings.filterwarnings(
    "ignore",
    category=FutureWarning,
    message=r"(?s).*google\.generativeai.*",
)

if TYPE_CHECKING:
    from .runner import EvaluationResult

logger = logging.getLogger(__name__)


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser with subcommands."""
    parser = argparse.ArgumentParser(
        prog="frontier",
        description="Frontier-CS: Evaluate solutions for frontier AI research problems",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  eval     Evaluate a solution
  batch    Batch evaluation with incremental progress
  list     List available problems
  show     Show problem statement
  harbor   Run generated Harbor tasks with stable Frontier-CS result output

Examples:
  frontier eval research flash_attn solution.py
  frontier eval algorithmic 1 solution.cpp
  frontier batch research
  frontier list algorithmic
  frontier harbor trial algorithmic 0 -a codex -m gpt-5.5
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # ==========================================================================
    # EVAL subcommand
    # ==========================================================================
    eval_parser = subparsers.add_parser(
        "eval",
        help="Evaluate a solution",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Evaluate a research problem
  frontier eval research flash_attn solution.py

  # Evaluate an algorithmic problem
  frontier eval algorithmic 1 solution.cpp

  # Override backend
  frontier eval research flash_attn solution.py --backend docker

  # Evaluate multiple problems
  frontier eval research --problems flash_attn,cross_entropy solution.py
  frontier eval research --all-problems solution.py
        """,
    )

    # Positional arguments for eval
    eval_parser.add_argument(
        "track",
        choices=["research", "algorithmic", "2.0"],
        help="Track: research, algorithmic, or 2.0",
    )
    eval_parser.add_argument(
        "problem_id",
        nargs="?",
        default=None,
        help="Problem ID (e.g., flash_attn for research, 1 for algorithmic)",
    )
    eval_parser.add_argument(
        "solution",
        nargs="?",
        default=None,
        help="Path to solution file",
    )

    # Problem selection
    problem_group = eval_parser.add_argument_group("Problem Selection")
    problem_group.add_argument(
        "--problems",
        type=str,
        help="Comma-separated list of problem IDs to evaluate",
    )
    problem_group.add_argument(
        "--all-problems",
        action="store_true",
        help="Evaluate all problems in the track",
    )
    problem_group.add_argument(
        "--problems-file",
        type=Path,
        help="File containing problem IDs (one per line)",
    )

    # Backend options
    backend_group = eval_parser.add_argument_group("Backend Options")
    backend_group.add_argument(
        "--backend",
        type=str,
        choices=["docker", "skypilot"],
        help="Evaluation backend: docker (local) or skypilot (cloud). "
             "Default: skypilot for research, docker for algorithmic",
    )
    backend_group.add_argument(
        "--cloud",
        type=str,
        default="gcp",
        help="Cloud provider for SkyPilot (default: gcp)",
    )
    backend_group.add_argument(
        "--region",
        type=str,
        help="Cloud region for SkyPilot",
    )
    backend_group.add_argument(
        "--idle-timeout",
        type=int,
        default=10,
        help="Minutes of idleness before SkyPilot cluster autostops (default: 10)",
    )
    backend_group.add_argument(
        "--keep-cluster",
        action="store_true",
        help="Keep SkyPilot cluster running after evaluation (disables autostop)",
    )
    backend_group.add_argument(
        "--judge-url",
        type=str,
        default="http://localhost:8081",
        help="Judge server URL for algorithmic problems",
    )

    # Evaluation options
    eval_opts = eval_parser.add_argument_group("Evaluation Options")
    eval_opts.add_argument(
        "--code",
        type=str,
        help="Solution code as string (alternative to file)",
    )
    eval_opts.add_argument(
        "--timeout",
        type=int,
        default=1000,
        help="Timeout per evaluation in seconds (default: 1000)",
    )

    # Output options
    output_group = eval_parser.add_argument_group("Output Options")
    output_group.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )
    output_group.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Only output scores",
    )
    output_group.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output including logs",
    )

    # ==========================================================================
    # BATCH subcommand
    # ==========================================================================
    batch_parser = subparsers.add_parser(
        "batch",
        help="Batch evaluation with incremental progress",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Evaluate research solutions (uses SkyPilot by default)
  frontier batch research

  # Evaluate algorithmic solutions (uses Docker by default)
  frontier batch algorithmic

  # Override default backend
  frontier batch research --backend docker
  frontier batch algorithmic --backend skypilot

  # Filter by model or problem
  frontier batch research --model gpt5.1
  frontier batch research --problem flash_attn

  # Resume interrupted evaluation
  frontier batch research --resume

Solution files use format: {problem}/{model}.py (e.g., flash_attn/gpt5.py)
        """,
    )

    # Track as positional argument
    batch_parser.add_argument(
        "track",
        choices=["research", "algorithmic", "2.0"],
        help="Track to evaluate: research, algorithmic, or 2.0",
    )

    # Pairs input (mutually exclusive)
    pairs_group = batch_parser.add_mutually_exclusive_group()
    pairs_group.add_argument(
        "--pairs",
        type=str,
        help="Comma-separated pairs (solution:problem,solution:problem)",
    )
    pairs_group.add_argument(
        "--pairs-file",
        type=Path,
        help="Pairs file (solution:problem per line)",
    )
    pairs_group.add_argument(
        "--solutions-dir",
        type=Path,
        help="Solutions directory to scan (default: solutions/)",
    )

    batch_parser.add_argument(
        "--problems-dir",
        type=Path,
        help="Problems directory (default: auto-detect from code location)",
    )

    batch_filter = batch_parser.add_argument_group("Filter Options")
    batch_filter.add_argument(
        "--model",
        type=str,
        help="Filter solutions by model name (e.g., gpt4, claude)",
    )
    batch_filter.add_argument(
        "--problem",
        type=str,
        help="Filter solutions by problem name (e.g., flash_attn)",
    )

    batch_output = batch_parser.add_argument_group("Output Options")
    batch_output.add_argument(
        "--results-dir",
        type=Path,
        default=Path("results/batch"),
        help="Directory for results and state (default: results/batch/{track})",
    )

    batch_track = batch_parser.add_argument_group("Track Options")
    batch_track.add_argument(
        "--judge-url",
        type=str,
        default="http://localhost:8081",
        help="Judge server URL for algorithmic problems",
    )

    batch_backend = batch_parser.add_argument_group("Backend Options")
    batch_backend.add_argument(
        "--backend",
        type=str,
        choices=["docker", "skypilot"],
        help="Evaluation backend: docker (local) or skypilot (cloud). "
             "Default: skypilot for research, docker for algorithmic",
    )
    batch_backend.add_argument(
        "--clusters",
        type=int,
        help="Number of SkyPilot clusters (research + skypilot only, default: same as --workers)",
    )
    batch_backend.add_argument(
        "--workers",
        type=int,
        default=10,
        help="Number of parallel workers/concurrent evaluations (default: 10)",
    )
    batch_backend.add_argument(
        "--idle-timeout",
        type=int,
        default=10,
        help="Minutes of idleness before SkyPilot cluster autostops (default: 10)",
    )
    batch_backend.add_argument(
        "--keep-cluster",
        action="store_true",
        help="Keep SkyPilot cluster running after evaluation (disables autostop)",
    )
    batch_backend.add_argument(
        "--bucket-url",
        type=str,
        help="Bucket URL for result storage (s3://... or gs://...). "
             "Results are written directly to the bucket by each worker and "
             "synced incrementally. Enables reliable resume across runs.",
    )
    batch_backend.add_argument(
        "--timeout",
        type=int,
        default=1000,
        help="Timeout per evaluation in seconds (default: 1000)",
    )

    batch_control = batch_parser.add_argument_group("Control Options")
    batch_control.add_argument(
        "--resume",
        action="store_true",
        help="Resume interrupted evaluation",
    )
    batch_control.add_argument(
        "--no-resume",
        action="store_true",
        help="Start fresh, ignoring previous state",
    )
    batch_control.add_argument(
        "--status",
        action="store_true",
        help="Show evaluation status and exit",
    )
    batch_control.add_argument(
        "--retry-failed",
        action="store_true",
        help="Retry failed pairs (includes error/timeout AND score=0)",
    )
    batch_control.add_argument(
        "--report",
        action="store_true",
        help="Show aggregated report and exit",
    )
    batch_control.add_argument(
        "--export-failed",
        type=Path,
        help="Export failed pairs to file",
    )
    batch_control.add_argument(
        "--sync-bucket",
        action="store_true",
        help="Sync results from bucket to local state and export reports",
    )

    # ==========================================================================
    # LIST subcommand
    # ==========================================================================
    list_parser = subparsers.add_parser(
        "list",
        help="List available problems",
    )
    list_parser.add_argument(
        "track",
        nargs="?",
        choices=["research", "algorithmic", "2.0"],
        help="Track to list (default: both)",
    )

    # ==========================================================================
    # SHOW subcommand
    # ==========================================================================
    show_parser = subparsers.add_parser(
        "show",
        help="Show problem statement",
    )
    show_parser.add_argument(
        "track",
        choices=["research", "algorithmic", "2.0"],
        help="Track: research, algorithmic, or 2.0",
    )
    show_parser.add_argument(
        "problem_id",
        help="Problem ID to show",
    )

    # ==========================================================================
    # HARBOR subcommand
    # ==========================================================================
    harbor_parser = subparsers.add_parser(
        "harbor",
        help="Run generated Harbor tasks and print Frontier-CS rewards",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  frontier harbor trial algorithmic 0 -a codex -m gpt-5.5 --agent-timeout 180
  frontier harbor trial 2.0 erdos_unit_distance -a codex -m gpt-5.5

This is a thin wrapper over `harbor trial start`. It preserves Harbor's
CLI/API semantics, then reads the trial artifacts so rewards are shown even
when the agent times out after making a valid iterative submission.
        """,
    )
    harbor_subparsers = harbor_parser.add_subparsers(
        dest="harbor_command",
        help="Harbor wrapper commands",
    )
    harbor_trial = harbor_subparsers.add_parser(
        "trial",
        help="Run one generated Harbor task",
    )
    harbor_trial.add_argument(
        "track",
        choices=["algorithmic", "2.0"],
        help="Generated Harbor adapter track",
    )
    harbor_trial.add_argument(
        "problem_id",
        help="Problem ID (e.g. 0 or erdos_unit_distance)",
    )
    harbor_trial.add_argument(
        "-a",
        "--agent",
        default="codex",
        help="Harbor agent name (default: codex)",
    )
    harbor_trial.add_argument(
        "-m",
        "--model",
        help="Agent model name passed to Harbor",
    )
    harbor_trial.add_argument(
        "--dataset-dir",
        type=Path,
        help="Directory containing generated Harbor tasks",
    )
    harbor_trial.add_argument(
        "--task-path",
        type=Path,
        help="Explicit generated Harbor task path",
    )
    harbor_trial.add_argument(
        "--trials-dir",
        type=Path,
        default=None,
        help="Harbor trials directory (default: .frontier-cs/harbor/trials)",
    )
    harbor_trial.add_argument(
        "--agent-timeout",
        type=float,
        help="Agent execution timeout in seconds",
    )
    harbor_trial.add_argument(
        "--verifier-timeout",
        type=float,
        help="Verifier execution timeout in seconds",
    )
    harbor_trial.add_argument(
        "--force-build",
        action="store_true",
        help="Pass --force-build to Harbor",
    )
    harbor_trial.add_argument(
        "--delete",
        action="store_true",
        help="Pass --delete to Harbor",
    )
    harbor_trial.add_argument(
        "--uv",
        action="store_true",
        help="Run Harbor as `uv run --no-sync harbor` instead of `harbor`",
    )
    harbor_trial.add_argument(
        "--harbor-bin",
        default="harbor",
        help="Harbor executable name/path (default: harbor)",
    )
    harbor_trial.add_argument(
        "--env",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Environment variable to pass to Harbor; repeatable",
    )
    harbor_trial.add_argument(
        "--no-generate",
        action="store_true",
        help="Do not auto-generate a missing Harbor task",
    )
    harbor_trial.add_argument(
        "--verbose",
        action="store_true",
        help="Print Harbor output and trial artifact details",
    )
    harbor_trial.add_argument(
        "--json",
        action="store_true",
        help="Print a JSON summary with reward, tokens, cost, and trial metadata",
    )

    return parser


def print_result(result: EvaluationResult, quiet: bool = False, verbose: bool = False) -> None:
    """Print evaluation result."""
    if quiet:
        if result.success:
            print(f"{result.problem_id}: {result.score}")
        else:
            print(f"{result.problem_id}: ERROR")
        return

    print(f"\n{'='*60}")
    print(f"Problem: {result.problem_id}")
    print(f"Status: {result.status.value}")

    if result.success:
        print(f"Score: {result.score}")
        if result.score_unbounded is not None and result.score_unbounded != result.score:
            print(f"Score (unbounded): {result.score_unbounded}")
    else:
        print(f"Message: {result.message}")

    if result.duration_seconds:
        print(f"Duration: {result.duration_seconds:.1f}s")

    if verbose and result.logs:
        print(f"\n--- Logs ---\n{result.logs}")

    print("=" * 60)


def print_results_json(results: List[EvaluationResult]) -> None:
    """Print results as JSON."""
    import json

    data = []
    for r in results:
        item = {
            "problem_id": r.problem_id,
            "score": r.score,
            "score_unbounded": r.score_unbounded,
            "status": r.status.value,
            "message": r.message,
            "duration_seconds": r.duration_seconds,
        }
        data.append(item)
    print(json.dumps(data, indent=2))


def get_problem_ids(
    args: argparse.Namespace,
    evaluator: SingleEvaluator,
    track: str,
) -> List[str]:
    """Get list of problem IDs to evaluate."""
    if args.all_problems:
        return evaluator.list_problems(track)

    if args.problems:
        return [p.strip() for p in args.problems.split(",")]

    if args.problems_file:
        if not args.problems_file.exists():
            print(f"Error: Problems file not found: {args.problems_file}", file=sys.stderr)
            sys.exit(1)
        problems = []
        for line in args.problems_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                problems.append(line)
        return problems

    if args.problem_id:
        return [args.problem_id]

    return []


def run_batch(args: argparse.Namespace) -> int:
    """Run batch evaluation command."""
    import signal
    import atexit
    from .batch import BatchEvaluator
    from .batch.pair import Pair

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="[%(levelname)s] %(message)s",
    )

    # Track batch evaluator for cleanup on interrupt
    batch_evaluator_ref: List = []  # Use list to allow modification in nested function

    def cleanup_on_exit():
        """Cleanup SkyPilot clusters on exit."""
        if batch_evaluator_ref:
            batch = batch_evaluator_ref[0]
            if hasattr(batch, '_cluster_names') and batch._cluster_names and not batch.keep_cluster:
                print("\nCleaning up SkyPilot clusters...")
                batch._cleanup_cluster_pool()

    def signal_handler(signum, frame):
        """Handle Ctrl+C by cleaning up and exiting."""
        print("\n\nInterrupted! Cleaning up...")
        cleanup_on_exit()
        sys.exit(1)

    # Register cleanup handlers
    atexit.register(cleanup_on_exit)
    signal.signal(signal.SIGINT, signal_handler)

    # Determine backend
    track = args.track

    # Determine backend: explicit --backend, or default based on track
    if args.backend:
        backend = args.backend
    elif track == "research":
        backend = "skypilot"
    else:
        backend = "docker"
    bucket_url = getattr(args, "bucket_url", None)
    keep_cluster = getattr(args, "keep_cluster", False)
    idle_timeout = None if keep_cluster else getattr(args, "idle_timeout", 10)
    judge_url = getattr(args, "judge_url", None)

    # Get workers and clusters
    workers = args.workers
    clusters = args.clusters  # None means same as workers

    # Set default paths based on track
    base_dir = Path(__file__).parents[2]  # src/frontier_cs/cli.py -> repo root
    solutions_dir = getattr(args, "solutions_dir", None)
    if solutions_dir is None:
        solutions_dir = base_dir / track / "solutions"
    problems_dir = getattr(args, "problems_dir", None)
    if problems_dir is None:
        problems_dir = base_dir / track / "problems"

    # Results dir: always add track subdir
    results_dir = args.results_dir / track
    timeout = getattr(args, "timeout", 1000)
    # Build kwargs, only include timeout if explicitly set (otherwise use BatchEvaluator default)
    batch_kwargs = dict(
        results_dir=results_dir,
        solutions_dir=solutions_dir,
        problems_dir=problems_dir,
        backend=backend,
        track=track,
        workers=workers,
        clusters=clusters,
        timeout=timeout,
        bucket_url=bucket_url,
        keep_cluster=keep_cluster,
        idle_timeout=idle_timeout,
        judge_url=judge_url,
    )

    batch = BatchEvaluator(**batch_kwargs)
    batch_evaluator_ref.append(batch)  # Register for cleanup on interrupt

    # Handle status command
    if args.status:
        status = batch.get_status()
        print("\nBatch Evaluation Status")
        print("=" * 40)
        print(f"Total pairs: {status['total_pairs']}")
        print(f"Completed: {status['completed']}")
        print(f"Successful: {status['successful']}")
        print(f"Errors: {status['errors']}")
        print(f"Pending: {status['pending']}")
        print(f"Started: {status['started_at'] or 'N/A'}")
        print(f"Updated: {status['updated_at'] or 'N/A'}")
        return 0

    # Handle sync-bucket command
    if getattr(args, "sync_bucket", False):
        if not bucket_url:
            print("Error: --sync-bucket requires --bucket-url", file=sys.stderr)
            return 1
        print(f"\nSyncing results from {bucket_url}...")
        count = batch.sync_from_bucket()
        print(f"Merged {count} results from bucket")

        # Export reports
        batch._export_all_results()
        status = batch.get_status()
        print(f"\nStatus: {status['completed']}/{status['total_pairs']} completed")
        print(f"Results exported to {results_dir}")
        return 0

    # Handle report command
    if args.report:
        # Detect and filter orphaned results (results for problems that no longer exist)
        valid_problems = batch._get_valid_problems()
        orphaned = batch._get_orphaned_pairs()
        if orphaned:
            orphaned_problems = sorted(set(pid.split(":")[1] for pid in orphaned))
            print(f"\n⚠️  Warning: Found {len(orphaned)} orphaned result(s) for problems that no longer exist:")
            for p in orphaned_problems:
                print(f"    - {p}")
            print("  These will be excluded from the report.\n")

        print("Aggregated Results by Model")
        print("=" * 60)
        by_model = batch.state.aggregate_by_model(valid_problems if valid_problems else None)
        for model, stats in sorted(by_model.items()):
            avg = f"{stats['avg_score']:.4f}" if stats['avg_score'] is not None else "N/A"
            print(f"  {model}: {stats['successful']}/{stats['total']} successful, avg={avg}")

        print("\nAggregated Results by Problem")
        print("=" * 60)
        by_problem = batch.state.aggregate_by_problem(valid_problems if valid_problems else None)
        for problem, stats in sorted(by_problem.items()):
            avg = f"{stats['avg_score']:.4f}" if stats['avg_score'] is not None else "N/A"
            print(f"  {problem}: {stats['successful']}/{stats['total']} successful, avg={avg}")

        # Also export CSV files
        batch.state.export_aggregated_csv(
            results_dir / "by_model.csv", by="model",
            valid_problems=valid_problems if valid_problems else None
        )
        batch.state.export_aggregated_csv(
            results_dir / "by_problem.csv", by="problem",
            valid_problems=valid_problems if valid_problems else None
        )
        print(f"\nCSV files exported to {results_dir}")
        return 0

    # Handle export-failed command
    if args.export_failed:
        count = batch.state.export_failed(args.export_failed)
        print(f"Exported {count} failed pairs to {args.export_failed}")
        return 0

    # Handle retry-failed command
    # Retries both error/timeout AND score=0 pairs (can't distinguish real 0 from failure)
    if args.retry_failed:
        print(f"\nRetrying failed pairs from {results_dir}")
        state = batch.retry_failed()
        print(f"\nComplete: {state.success_count}/{state.total_pairs} successful")
        # Return 0 even if some evaluations failed - individual errors are expected
        return 0

    # Handle resume command
    if args.resume:
        print(f"\nResuming batch evaluation from {results_dir}")
        state = batch.resume()
        print(f"\nComplete: {state.success_count}/{state.total_pairs} successful")
        # Return 0 even if some evaluations failed - individual errors are expected
        return 0

    # Determine input mode
    resume = not args.no_resume
    state = None

    if args.pairs:
        # Mode: pairs from command line
        pairs = []
        for p in args.pairs.split(","):
            p = p.strip()
            if ":" not in p:
                print(f"Error: Invalid pair format (expected solution:problem): {p}", file=sys.stderr)
                return 1
            solution, problem = p.split(":", 1)
            pairs.append(Pair(solution=solution.strip(), problem=problem.strip()))

        backend_info = f" [backend={backend}]" if backend != "docker" else ""
        print(f"\nBatch evaluation{backend_info}: {len(pairs)} pairs")
        state = batch.evaluate_pairs(pairs, resume=resume)

    elif args.pairs_file:
        # Mode: pairs file
        if not args.pairs_file.exists():
            print(f"Error: Pairs file not found: {args.pairs_file}", file=sys.stderr)
            return 1

        backend_info = f" [backend={backend}]" if backend != "docker" else ""
        print(f"\nBatch evaluation{backend_info} from pairs file: {args.pairs_file}")
        state = batch.evaluate_pairs_file(args.pairs_file, resume=resume)

    else:
        # Mode: scan solutions directory (default)
        from .batch import scan_solutions_dir

        if not solutions_dir.is_dir():
            print(f"Error: No solutions directory found: {solutions_dir}", file=sys.stderr)
            print("Use --solutions-dir to specify", file=sys.stderr)
            return 1

        pairs = scan_solutions_dir(solutions_dir, problems_dir=problems_dir)
        if not pairs:
            print(f"Error: No solution files found in {solutions_dir}", file=sys.stderr)
            return 1

        # Apply filters
        model_filter = getattr(args, "model", None)
        problem_filter = getattr(args, "problem", None)

        if model_filter or problem_filter:
            from .gen.solution_format import parse_solution_filename

            filtered_pairs = []
            for pair in pairs:
                # Filter by problem
                if problem_filter and pair.problem != problem_filter:
                    continue

                # Filter by model
                if model_filter:
                    filename = Path(pair.solution).name
                    parsed = parse_solution_filename(filename)
                    if parsed:
                        model_name, _, _ = parsed
                        if model_name != model_filter:
                            continue
                    else:
                        continue

                filtered_pairs.append(pair)

            pairs = filtered_pairs
            if not pairs:
                filter_desc = []
                if model_filter:
                    filter_desc.append(f"model={model_filter}")
                if problem_filter:
                    filter_desc.append(f"problem={problem_filter}")
                print(f"Error: No solutions found matching filters: {', '.join(filter_desc)}", file=sys.stderr)
                return 1

        backend_info = f", backend={backend}" if backend != "docker" else ""
        print(f"\nBatch evaluation ({track}{backend_info}): {len(pairs)} solutions from {solutions_dir}")
        state = batch.evaluate_pairs(pairs, resume=resume)

    # Print summary
    print(f"\n{'='*40}")
    print("Batch Evaluation Summary")
    print("=" * 40)
    print(f"Total: {state.total_pairs}")
    print(f"Successful: {state.success_count}")
    print(f"Errors: {state.error_count}")
    print(f"Results saved to: {results_dir}")
    print(f"\nOutput files:")
    print(f"  - results.csv: All results")
    print(f"  - by_model.csv: Aggregated by model")
    print(f"  - by_problem.csv: Aggregated by problem")
    if state.error_count > 0:
        print(f"  - failed.txt: {state.error_count} failed pairs")

    # Return 0 even if some evaluations failed - individual errors are expected
    return 0


def run_list(args: argparse.Namespace) -> int:
    """Run list command."""
    from .single_evaluator import SingleEvaluator

    evaluator = SingleEvaluator(backend="docker")

    if args.track == "algorithmic":
        # Only list algorithmic problems in compact format
        problems = evaluator.list_problems("algorithmic")
        print(f"\nAlgorithmic Problems ({len(problems)} total):\n")
        ids_per_line = 10
        for i in range(0, len(problems), ids_per_line):
            line_ids = problems[i:i+ids_per_line]
            print("  " + ", ".join(line_ids))
    elif args.track == "research":
        # Only list research problems
        all_research = evaluator.list_problems("research")
        research_problems = [p for p in all_research if not p.startswith("algorithmic/")]
        print(f"\nResearch Problems ({len(research_problems)} total):\n")
        for p in research_problems:
            print(f"  {p}")
    elif args.track == "2.0":
        problems = evaluator.list_problems("2.0")
        print(f"\nFrontier-CS 2.0 Problems ({len(problems)} total):\n")
        for p in problems:
            print(f"  {p}")
    else:
        # List both tracks (no track specified)
        all_research = evaluator.list_problems("research")
        research_problems = [p for p in all_research if not p.startswith("algorithmic/")]
        print(f"\nResearch Problems ({len(research_problems)} total):\n")
        for p in research_problems:
            print(f"  {p}")

        alg_problems = evaluator.list_problems("algorithmic")
        print(f"\nAlgorithmic Problems ({len(alg_problems)} total):\n")
        ids_per_line = 10
        for i in range(0, len(alg_problems), ids_per_line):
            line_ids = alg_problems[i:i+ids_per_line]
            print("  " + ", ".join(line_ids))

        benchmark20_problems = evaluator.list_problems("2.0")
        print(f"\nFrontier-CS 2.0 Problems ({len(benchmark20_problems)} total):\n")
        for p in benchmark20_problems:
            print(f"  {p}")
    return 0


def run_show(args: argparse.Namespace) -> int:
    """Run show command."""
    from .single_evaluator import SingleEvaluator

    evaluator = SingleEvaluator(backend="docker")
    statement = evaluator.get_problem_statement(args.track, args.problem_id)
    if statement:
        print(statement)
    else:
        print(f"Problem not found: {args.problem_id}", file=sys.stderr)
        return 1
    return 0


def _harbor_task_name(track: str, problem_id: str) -> str:
    if track == "algorithmic":
        return f"frontier-cs-algorithm-{problem_id}"
    if track == "2.0":
        slug = problem_id.replace("_", "-").replace(".", "-")
        return f"frontier-cs-2-0-{slug}"
    raise ValueError(f"Unsupported Harbor track: {track}")


def _repo_root() -> Path:
    cwd = Path.cwd()
    if (cwd / "algorithmic").is_dir() and (cwd / "src" / "frontier_cs").is_dir():
        return cwd
    return Path(__file__).parents[2]


def _default_harbor_dataset_dir(track: str) -> Path:
    base = _repo_root() / ".frontier-cs" / "harbor" / "datasets"
    if track == "algorithmic":
        return base / "frontier-cs-algorithm"
    if track == "2.0":
        return base / "frontier-cs-2.0"
    raise ValueError(f"Unsupported Harbor track: {track}")


def _default_harbor_trials_dir() -> Path:
    return _repo_root() / ".frontier-cs" / "harbor" / "trials"


def _adapter_module_for_track(track: str) -> tuple[str, Path]:
    root = _repo_root()
    if track == "algorithmic":
        return (
            "frontier_cs_algorithm.main",
            root / "adapters" / "frontier-cs-algorithm" / "src",
        )
    if track == "2.0":
        return (
            "frontier_cs_2_0.main",
            root / "adapters" / "frontier-cs-2.0" / "src",
        )
    raise ValueError(f"Unsupported Harbor track: {track}")


def _generate_harbor_task(track: str, problem_id: str, output_dir: Path) -> None:
    module, adapter_src = _adapter_module_for_track(track)
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        str(adapter_src)
        if not existing_pythonpath
        else f"{adapter_src}{os.pathsep}{existing_pythonpath}"
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        "-m",
        module,
        "--source",
        str(_repo_root()),
        "--output-dir",
        str(output_dir),
        "--task-ids",
        str(problem_id),
        "--overwrite",
    ]
    completed = subprocess.run(
        command,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "Failed to generate Harbor task:\n"
            + " ".join(command)
            + "\n"
            + (completed.stdout or "")
        )


def _harbor_command_prefix(args: argparse.Namespace) -> list[str]:
    if args.uv:
        return ["uv", "run", "--no-sync", args.harbor_bin]
    if shutil.which(args.harbor_bin):
        return [args.harbor_bin]
    if shutil.which("uvx"):
        return ["uvx", args.harbor_bin]
    if shutil.which("uv"):
        return ["uv", "tool", "run", args.harbor_bin]
    return [args.harbor_bin]


def _progress(message: str) -> None:
    print(f"[frontier harbor] {message}", file=sys.stderr, flush=True)


def _parse_harbor_env(values: list[str]) -> dict[str, str]:
    env: dict[str, str] = {}
    for item in values:
        if "=" not in item:
            raise ValueError(f"Invalid --env value {item!r}; expected KEY=VALUE")
        key, value = item.split("=", 1)
        if not key:
            raise ValueError(f"Invalid --env value {item!r}; empty key")
        env[key] = value
    return env


def _load_json_file(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _find_harbor_trial_dir(
    *,
    trials_dir: Path,
    task_name: str,
    harbor_stdout: str,
) -> Path | None:
    for line in harbor_stdout.splitlines():
        if line.startswith("Trial name:"):
            trial_name = line.split(":", 1)[1].strip()
            candidate = trials_dir / trial_name
            if candidate.exists():
                return candidate

    candidates = sorted(
        trials_dir.glob(f"{task_name}__*"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if candidates:
        return candidates[0]

    expected_task_names = {task_name, f"frontier-cs/{task_name}"}
    result_files = sorted(
        trials_dir.glob("*/result.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for result_file in result_files:
        result = _load_json_file(result_file)
        if result and result.get("task_name") in expected_task_names:
            return result_file.parent
    return None


def _trial_dir_matches_task(candidate: Path, task_name: str) -> bool:
    if candidate.name.startswith(f"{task_name}__"):
        return True
    if candidate.name.startswith(f"{task_name[:32]}__"):
        return True

    config = _load_json_file(candidate / "config.json") or {}
    task = config.get("task") or {}
    task_path = task.get("path")
    if task_path and Path(str(task_path)).name == task_name:
        return True

    result = _load_json_file(candidate / "result.json") or {}
    return result.get("task_name") in {task_name, f"frontier-cs/{task_name}"}


def _find_live_harbor_trial_dir(
    *,
    trials_dir: Path,
    task_name: str,
    harbor_stdout: str,
    known_trial_dirs: set[Path],
    started_at: float,
) -> Path | None:
    for line in harbor_stdout.splitlines():
        if line.startswith("Trial name:"):
            trial_name = line.split(":", 1)[1].strip()
            candidate = trials_dir / trial_name
            if candidate.exists():
                return candidate

    candidates = []
    for candidate in trials_dir.iterdir() if trials_dir.exists() else ():
        if not candidate.is_dir():
            continue
        if candidate.resolve() in known_trial_dirs:
            continue
        try:
            if candidate.stat().st_mtime + 5 < started_at:
                continue
        except OSError:
            continue
        if _trial_dir_matches_task(candidate, task_name):
            candidates.append(candidate)

    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def _get_harbor_trial_rewards(trial_dir: Path) -> dict[str, float | int] | None:
    result = _load_json_file(trial_dir / "result.json")
    if result is None:
        return None

    verifier_result = result.get("verifier_result") or {}
    rewards = verifier_result.get("rewards")
    if isinstance(rewards, dict):
        normalized = dict(rewards)
        reward = normalized.get("reward", 0.0)
        normalized.setdefault("score", reward)
        normalized.setdefault("score_unbounded", normalized["score"])
        return normalized
    return {"reward": 0.0, "score": 0.0, "score_unbounded": 0.0}


def _count_successful_submissions(trial_dir: Path) -> tuple[int, float | None]:
    submissions = trial_dir / "verifier" / "submissions.jsonl"
    if not submissions.exists():
        return 0, None

    successful = 0
    best = None
    for line in submissions.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
            score = float(record.get("score", 0.0))
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if record.get("status") == "done":
            successful += 1
            best = score if best is None else max(best, score)
    return successful, best


def _summarize_agent_exception(exception: dict) -> str | None:
    exception_type = exception.get("exception_type")
    message = str(exception.get("exception_message") or "").strip()
    if not exception_type and not message:
        return None
    if exception_type == "NonZeroAgentExitCodeError":
        if "exit 143" in message:
            return "agent exited with code 143 after producing a score"
        return "agent exited non-zero after producing a score"
    if exception_type == "AgentTimeoutError":
        return message or "agent timed out after producing a score"
    if message:
        return message.splitlines()[0][:240]
    return str(exception_type)


def _harbor_trial_summary_payload(trial_dir: Path) -> dict:
    result = _load_json_file(trial_dir / "result.json") or {}
    rewards = _get_harbor_trial_rewards(trial_dir) or {}
    exception = result.get("exception_info") or {}
    agent_result = result.get("agent_result") or {}
    agent_info = result.get("agent_info") or {}
    model_info = agent_info.get("model_info") or {}
    sidecar = (
        _load_json_file(trial_dir / "verifier" / "judge_result.json")
        or _load_json_file(trial_dir / "verifier" / "evaluation_result.json")
        or {}
    )
    successful_submissions, best_submission_reward = _count_successful_submissions(
        trial_dir
    )
    has_reward = rewards.get("reward") is not None
    agent_status = exception.get("exception_type") if exception else "completed"
    reward_metrics = {
        key: value
        for key, value in rewards.items()
        if key not in {"reward", "score", "score_unbounded"}
    }

    payload = {
        "reward": rewards.get("reward"),
        "score": rewards.get("score"),
        "score_unbounded": rewards.get("score_unbounded"),
        "metrics": reward_metrics or None,
        "trial_status": "scored" if has_reward else agent_status,
        "agent_status": agent_status,
        "agent_error_summary": _summarize_agent_exception(exception)
        if exception and has_reward
        else None,
        "error_message": exception.get("exception_message")
        if exception and not has_reward
        else None,
        "trial_name": result.get("trial_name"),
        "task_name": result.get("task_name"),
        "trial_dir": str(trial_dir),
        "agent": agent_info.get("name"),
        "agent_version": agent_info.get("version"),
        "model": model_info.get("name"),
        "model_provider": model_info.get("provider"),
        "n_input_tokens": agent_result.get("n_input_tokens"),
        "n_cache_tokens": agent_result.get("n_cache_tokens"),
        "n_output_tokens": agent_result.get("n_output_tokens"),
        "cost_usd": agent_result.get("cost_usd"),
        "successful_submissions": successful_submissions,
        "best_iterative_reward": best_submission_reward,
        "used_best_submission": bool(sidecar.get("used_best_submission")),
        "best_submission_reward": sidecar.get("best_submission_reward"),
        "started_at": result.get("started_at"),
        "finished_at": result.get("finished_at"),
    }
    return {key: value for key, value in payload.items() if value is not None}


def _print_harbor_trial_summary(trial_dir: Path) -> None:
    payload = _harbor_trial_summary_payload(trial_dir)
    rewards = _get_harbor_trial_rewards(trial_dir)

    print("\nFrontier-CS Harbor Summary")
    print("=" * 40)
    print(f"Trial directory: {trial_dir}")
    print(f"Trial status: {payload.get('trial_status', 'unknown')}")
    if payload.get("error_message"):
        print(f"Message: {payload['error_message']}")

    if rewards:
        print(f"Rewards: {rewards}")
    else:
        print("Rewards: unavailable")

    if payload.get("used_best_submission"):
        print(
            "Best submission fallback: "
            f"{payload.get('best_submission_reward', payload.get('reward'))}"
        )
    if payload.get("cost_usd") is not None:
        print(f"Cost USD: {payload['cost_usd']}")
    token_fields = [
        payload.get("n_input_tokens"),
        payload.get("n_cache_tokens"),
        payload.get("n_output_tokens"),
    ]
    if any(value is not None for value in token_fields):
        print(
            "Tokens: "
            f"input={payload.get('n_input_tokens')}, "
            f"cache={payload.get('n_cache_tokens')}, "
            f"output={payload.get('n_output_tokens')}"
        )

    reward_json = trial_dir / "verifier" / "reward.json"
    if reward_json.exists():
        print(f"Reward artifact: {reward_json}")

    if payload.get("successful_submissions") is not None:
        print(f"Iterative submissions: {payload['successful_submissions']} successful")
        if payload.get("best_iterative_reward") is not None:
            print(f"Best iterative reward: {payload['best_iterative_reward']}")


def _harbor_submission_event_key(event: dict) -> tuple[str, str, str, str]:
    submission_uuid = event.get("submission_uuid")
    if submission_uuid:
        return ("uuid", str(submission_uuid), "", "")
    return (
        str(event.get("timestamp") or ""),
        str(event.get("status") or ""),
        str(event.get("reward") or ""),
        str(event.get("code_chars") or ""),
    )


def _read_new_text(path: Path, file_offsets: dict[Path, int]) -> str:
    try:
        size = path.stat().st_size
        offset = file_offsets.get(path, 0)
        if size < offset:
            offset = 0
        if size == offset:
            return ""
        with path.open("r", encoding="utf-8", errors="replace") as f:
            f.seek(offset)
            chunk = f.read()
            file_offsets[path] = f.tell()
            return chunk
    except OSError:
        return ""


def _submission_log_event(line: str) -> dict | None:
    if not line.strip():
        return None
    try:
        record = json.loads(line)
    except json.JSONDecodeError:
        return None
    if record.get("status") != "done":
        return None
    return {
        "timestamp": record.get("ts"),
        "status": record.get("status"),
        "reward": record.get("score"),
        "score": record.get("score_raw", record.get("score")),
        "code_chars": record.get("code_chars"),
        "submission_uuid": record.get("submission_uuid"),
    }


def _poll_harbor_submission_events(
    *,
    trial_dir: Path | None,
    file_offsets: dict[Path, int],
    seen: set[tuple[str, str, str, str]],
) -> list[dict]:
    if trial_dir is None:
        return []

    events = []
    submissions_log = trial_dir / "agent" / "submissions.jsonl"
    if submissions_log.exists():
        for line in _read_new_text(submissions_log, file_offsets).splitlines():
            event = _submission_log_event(line)
            if event is None:
                continue
            key = _harbor_submission_event_key(event)
            if key in seen:
                continue
            seen.add(key)
            events.append(event)
    return events


def _parse_float(value: object) -> float | None:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _format_score(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.2f}"


def _format_reward(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.4f}"


def _score_bar(scores: list[float]) -> str:
    if not scores:
        return ""
    blocks = "▁▂▃▄▅▆▇█"
    lo = min(scores)
    hi = max(scores)
    if hi <= lo:
        return blocks[-1] * len(scores)
    return "".join(
        blocks[min(len(blocks) - 1, int((score - lo) / (hi - lo) * (len(blocks) - 1)))]
        for score in scores
    )


def _print_harbor_submission_event(
    index: int, event: dict, scores: list[float], previous_score: float | None
) -> None:
    timestamp = event.get("timestamp") or time.strftime(
        "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
    )
    score = _parse_float(event.get("score"))
    reward = _parse_float(event.get("reward"))
    best = max(scores) if scores else score
    code_chars = event.get("code_chars")
    suffix = f" code_chars={code_chars}" if code_chars is not None else ""
    print(
        "[frontier harbor] "
        f"submission #{index} {timestamp} "
        f"status={event.get('status')} score={_format_score(score)} "
        f"best={_format_score(best)} reward={_format_reward(reward)}{suffix}",
        file=sys.stderr,
        flush=True,
    )
    print(
        "[frontier harbor] "
        f"score bar: {_score_bar(scores)} "
        f"({_format_score(previous_score if previous_score is not None else 0.0)} -> "
        f"{_format_score(score)})",
        file=sys.stderr,
        flush=True,
    )


def _run_harbor_command_live(
    *,
    command: list[str],
    env: dict[str, str],
    args: argparse.Namespace,
    trials_dir: Path,
    task_name: str,
) -> tuple[int, str]:
    started_at = time.time()
    known_trial_dirs = {
        path.resolve()
        for path in trials_dir.iterdir()
        if path.is_dir()
    }
    process = subprocess.Popen(
        command,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=1,
    )
    assert process.stdout is not None

    lines: queue.Queue[str | None] = queue.Queue()

    def read_stdout() -> None:
        try:
            for line in process.stdout:
                lines.put(line)
        finally:
            lines.put(None)

    reader = threading.Thread(target=read_stdout, daemon=True)
    reader.start()

    stdout_parts: list[str] = []
    trial_dir: Path | None = None
    file_offsets: dict[Path, int] = {}
    seen_events: set[tuple[str, str, str, str]] = set()
    scores: list[float] = []
    submission_count = 0
    stdout_closed = False

    while True:
        try:
            line = lines.get(timeout=0.5)
            if line is None:
                stdout_closed = True
            else:
                stdout_parts.append(line)
                if args.verbose:
                    print(line, end="")
                stdout_text = "".join(stdout_parts)
                if trial_dir is None:
                    trial_dir = _find_live_harbor_trial_dir(
                        trials_dir=trials_dir,
                        task_name=task_name,
                        harbor_stdout=stdout_text,
                        known_trial_dirs=known_trial_dirs,
                        started_at=started_at,
                    )
        except queue.Empty:
            pass

        stdout_text = "".join(stdout_parts)
        if trial_dir is None:
            trial_dir = _find_live_harbor_trial_dir(
                trials_dir=trials_dir,
                task_name=task_name,
                harbor_stdout=stdout_text,
                known_trial_dirs=known_trial_dirs,
                started_at=started_at,
            )

        for event in _poll_harbor_submission_events(
            trial_dir=trial_dir,
            file_offsets=file_offsets,
            seen=seen_events,
        ):
            submission_count += 1
            score = _parse_float(event.get("score"))
            previous_score = scores[-1] if scores else 0.0
            if score is not None:
                scores.append(score)
            _print_harbor_submission_event(
                submission_count, event, scores, previous_score
            )

        if stdout_closed and process.poll() is not None:
            break

    reader.join(timeout=1)
    return process.returncode or 0, "".join(stdout_parts)


def run_harbor(args: argparse.Namespace) -> int:
    """Run Harbor wrapper commands."""
    if args.harbor_command != "trial":
        print("Error: Missing Harbor command. Try `frontier harbor trial --help`.", file=sys.stderr)
        return 1

    task_name = _harbor_task_name(args.track, args.problem_id)
    using_default_task_path = args.task_path is None
    task_path = args.task_path
    dataset_dir = args.dataset_dir or _default_harbor_dataset_dir(args.track)
    if task_path is None:
        task_path = dataset_dir / task_name

    should_generate = (
        using_default_task_path
        and task_path == dataset_dir / task_name
        and not args.no_generate
    )
    if should_generate:
        _progress(f"Generating task {task_name}")
        try:
            _generate_harbor_task(args.track, args.problem_id, dataset_dir)
        except RuntimeError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1

    if not task_path.exists():
        print(
            f"Error: Harbor task path not found: {task_path}\n"
            "Generate Harbor tasks first, or pass --task-path / --dataset-dir.",
            file=sys.stderr,
        )
        return 1

    trials_dir = args.trials_dir or _default_harbor_trials_dir()
    trials_dir.mkdir(parents=True, exist_ok=True)

    command = _harbor_command_prefix(args)
    command.extend(["trial", "start", "-p", str(task_path), "-a", args.agent])
    if args.model:
        command.extend(["-m", args.model])
    if args.agent_timeout is not None:
        command.extend(["--agent-timeout", str(args.agent_timeout)])
    if args.verifier_timeout is not None:
        command.extend(["--verifier-timeout", str(args.verifier_timeout)])
    command.extend(["--trials-dir", str(trials_dir)])
    if args.force_build:
        command.append("--force-build")
    if args.delete:
        command.append("--delete")

    env = os.environ.copy()
    try:
        env.update(_parse_harbor_env(args.env))
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    if args.track == "algorithmic" and "FRONTIER_CS_ALGORITHMIC_PATH" not in env:
        env["FRONTIER_CS_ALGORITHMIC_PATH"] = str(_repo_root() / "algorithmic")

    _progress(f"Starting Harbor trial {task_name}")
    if args.track == "2.0":
        _progress("Building/preparing Harbor environment; judge readiness appears at submission time")
    if args.verbose:
        print("Running Harbor trial...")
        print(" ".join(command))
    returncode, harbor_stdout = _run_harbor_command_live(
        command=command,
        env=env,
        args=args,
        trials_dir=trials_dir,
        task_name=task_name,
    )

    _progress("Reading trial artifacts")
    trial_dir = _find_harbor_trial_dir(
        trials_dir=trials_dir,
        task_name=task_name,
        harbor_stdout=harbor_stdout,
    )
    if trial_dir is None:
        print("Error: could not locate Harbor trial directory.", file=sys.stderr)
        return returncode or 1

    rewards = _get_harbor_trial_rewards(trial_dir)
    if rewards and "reward" in rewards:
        if args.json:
            print(json.dumps(_harbor_trial_summary_payload(trial_dir), indent=2))
        elif args.verbose:
            _print_harbor_trial_summary(trial_dir)
        else:
            print(rewards["reward"])
        return 0

    if args.verbose:
        _print_harbor_trial_summary(trial_dir)
    else:
        print(f"Error: no reward found in {trial_dir}", file=sys.stderr)

    return returncode or 1


def run_eval(args: argparse.Namespace) -> int:
    """Run eval command."""
    from .single_evaluator import SingleEvaluator

    track = args.track

    # Determine backend: explicit --backend or track default
    if args.backend:
        backend = args.backend
    else:
        # Default: skypilot for research, docker for algorithmic/2.0
        backend = "skypilot" if track == "research" else "docker"
    idle_timeout = None if args.keep_cluster else getattr(args, 'idle_timeout', 10)
    timeout = getattr(args, 'timeout', None)
    evaluator = SingleEvaluator(
        backend=backend,
        judge_url=args.judge_url,
        cloud=args.cloud,
        region=args.region,
        keep_cluster=getattr(args, 'keep_cluster', False),
        idle_timeout=idle_timeout,
        timeout=timeout,
    )

    # Get problem IDs
    problem_ids = get_problem_ids(args, evaluator, track)

    if not problem_ids:
        print("Error: No problems specified. Use --help for usage.", file=sys.stderr)
        return 1

    # Get solution code
    if args.code:
        code = args.code
    elif args.solution:
        solution_path = Path(args.solution)
        if not solution_path.exists():
            print(f"Error: Solution file not found: {solution_path}", file=sys.stderr)
            return 1
        code = solution_path.read_text(encoding="utf-8")
    else:
        print("Error: No solution provided.", file=sys.stderr)
        return 1

    # Run evaluations
    results = []
    eval_stdout = contextlib.nullcontext()
    if args.json:
        # Keep JSON clean: suppress human-readable prints and route runner stdout to stderr
        args.quiet = True
        eval_stdout = contextlib.redirect_stdout(sys.stderr)

    with eval_stdout:
        for pid in problem_ids:
            if not args.quiet:
                print(f"Evaluating {pid}...", end=" ", flush=True)

            result = evaluator.evaluate(track, pid, code)
            results.append(result)

            if not args.quiet:
                if result.success:
                    print(f"Score: {result.score}")
                else:
                    print(f"ERROR: {result.message}")

    # Output results
    if args.json:
        print_results_json(results)
    elif not args.quiet:
        print(f"\n{'='*60}")
        print("Summary")
        print("=" * 60)

        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]

        print(f"Total: {len(results)}")
        print(f"Successful: {len(successful)}")
        print(f"Failed: {len(failed)}")

        if successful:
            avg_score = sum(r.score for r in successful) / len(successful)
            print(f"Average Score: {avg_score:.2f}")

        if failed and args.verbose:
            print("\nFailed problems:")
            for r in failed:
                print(f"  {r.problem_id}: {r.message}")

    # Return non-zero if any failures
    return 0 if all(r.success for r in results) else 1


def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point."""
    if argv is None:
        argv = sys.argv[1:]

    parser = create_parser()
    args = parser.parse_args(argv)

    # Route to appropriate command handler
    if args.command == "eval":
        return run_eval(args)
    elif args.command == "batch":
        return run_batch(args)
    elif args.command == "list":
        return run_list(args)
    elif args.command == "show":
        return run_show(args)
    elif args.command == "harbor":
        return run_harbor(args)
    else:
        # No command specified, show help
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
