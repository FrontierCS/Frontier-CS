#!/usr/bin/env python3
"""
CLI interface for Frontier-CS evaluation.

Usage:
    # Single problem evaluation
    frontier eval flash_attn solution.py
    frontier eval --algorithmic 1 solution.cpp

    # Auto-detect problem from filename
    frontier eval solutions/flash_attn.gpt5.py

    # With SkyPilot
    frontier eval flash_attn solution.py --skypilot

    # All problems for a solution
    frontier eval --all-problems solution.py

    # List problems
    frontier list
    frontier list --algorithmic

    # Batch evaluation (scans solutions/ by default)
    frontier batch
    frontier batch --solutions-dir path/to/solutions
    frontier batch --resume --results-dir results/batch1
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import List, Optional

from .evaluator import FrontierCSEvaluator
from .runner import EvaluationResult
from .gen.solution_format import parse_solution_filename

logger = logging.getLogger(__name__)


def detect_solution_file(path: Path) -> tuple[bool, Optional[str], Optional[Path]]:
    """
    Detect if a path is a solution file with format {problem}.{model}.py.

    Returns:
        (is_solution, problem, solution_file)
        - is_solution: True if path matches the solution file format
        - problem: Problem ID parsed from filename (or None)
        - solution_file: The solution file Path (or None)
    """
    if not path.is_file():
        return False, None, None

    parsed = parse_solution_filename(path.name)
    if not parsed:
        return False, None, None

    problem, _, _ = parsed
    return True, problem, path


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

Examples:
  frontier eval flash_attn solution.py
  frontier eval --algorithmic 1 solution.cpp
  frontier batch --solutions-dir solutions/
  frontier list --algorithmic
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
  # Evaluate with problem ID and solution file
  frontier eval flash_attn solution.py
  frontier eval --algorithmic 1 solution.cpp

  # Auto-detect problem from filename
  frontier eval solutions/flash_attn.gpt5.py

  # Evaluate with SkyPilot (cloud)
  frontier eval flash_attn solution.py --skypilot

  # Evaluate multiple problems
  frontier eval --problems flash_attn,cross_entropy solution.py
  frontier eval --all-problems solution.py
        """,
    )

    # Positional arguments for eval
    eval_parser.add_argument(
        "problem_id",
        nargs="?",
        default=None,
        help="Problem ID (e.g., flash_attn) or solution file (e.g., flash_attn.gpt5.py)",
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
        "--algorithmic",
        action="store_true",
        help="Evaluate algorithmic problem (expects numeric ID)",
    )
    problem_group.add_argument(
        "--research",
        action="store_true",
        help="Evaluate research problem (default track)",
    )
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
        "--skypilot",
        action="store_true",
        help="Use SkyPilot for cloud evaluation",
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
  # Evaluate all solutions (scans solutions/ directory)
  frontier batch

  # Evaluate from specific solutions directory
  frontier batch --solutions-dir path/to/solutions

  # Evaluate specific pairs
  frontier batch --pairs "flash_attn.gpt5.py:flash_attn"

  # Resume interrupted evaluation
  frontier batch --resume --results-dir results/batch1

  # Check evaluation status
  frontier batch --status --results-dir results/batch1

Solution files use format: {problem}.{model}.py (e.g., flash_attn.gpt5.py)
        """,
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

    batch_output = batch_parser.add_argument_group("Output Options")
    batch_output.add_argument(
        "--results-dir",
        type=Path,
        default=Path("results/batch"),
        help="Directory for results and state (default: results/batch)",
    )

    batch_track = batch_parser.add_argument_group("Track Selection")
    batch_track.add_argument(
        "--algorithmic",
        action="store_true",
        help="Evaluate algorithmic track (C++ solutions)",
    )
    batch_track.add_argument(
        "--judge-url",
        type=str,
        default="http://localhost:8081",
        help="Judge server URL for algorithmic problems",
    )

    batch_backend = batch_parser.add_argument_group("Backend Options")
    batch_backend.add_argument(
        "--skypilot",
        action="store_true",
        help="Use SkyPilot for cloud evaluation",
    )
    batch_backend.add_argument(
        "--clusters",
        type=int,
        help="Number of SkyPilot clusters (research + skypilot only, default: same as --workers)",
    )
    batch_backend.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of parallel workers/concurrent evaluations (default: 1)",
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
        "--algorithmic",
        action="store_true",
        help="List algorithmic problems only",
    )
    list_parser.add_argument(
        "--research",
        action="store_true",
        help="List research problems only",
    )

    # ==========================================================================
    # SHOW subcommand
    # ==========================================================================
    show_parser = subparsers.add_parser(
        "show",
        help="Show problem statement",
    )
    show_parser.add_argument(
        "problem_id",
        help="Problem ID to show",
    )
    show_parser.add_argument(
        "--algorithmic",
        action="store_true",
        help="Show algorithmic problem",
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
    evaluator: FrontierCSEvaluator,
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
    from .batch import BatchEvaluator
    from .batch.pair import Pair

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="[%(levelname)s] %(message)s",
    )

    # Determine backend
    backend = "skypilot" if args.skypilot else "docker"

    track = "algorithmic" if getattr(args, "algorithmic", False) else "research"
    bucket_url = getattr(args, "bucket_url", None)
    keep_cluster = getattr(args, "keep_cluster", False)
    idle_timeout = None if keep_cluster else getattr(args, "idle_timeout", 10)
    judge_url = getattr(args, "judge_url", None)

    # Get workers and clusters
    workers = args.workers
    clusters = args.clusters  # None means same as workers

    # Create batch evaluator
    problems_dir = getattr(args, "problems_dir", None)
    timeout = getattr(args, "timeout", 1000)
    # Build kwargs, only include timeout if explicitly set (otherwise use BatchEvaluator default)
    batch_kwargs = dict(
        results_dir=args.results_dir,
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
        print(f"Results exported to {args.results_dir}")
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
        results_dir = Path(args.results_dir)
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
        print(f"\nRetrying failed pairs from {args.results_dir}")
        state = batch.retry_failed()
        print(f"\nComplete: {state.success_count}/{state.total_pairs} successful")
        # Return 0 even if some evaluations failed - individual errors are expected
        return 0

    # Handle resume command
    if args.resume:
        print(f"\nResuming batch evaluation from {args.results_dir}")
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

        solutions_dir = args.solutions_dir
        if solutions_dir is None:
            # Use base_dir from batch evaluator
            base_dir = Path(__file__).parents[2]  # src/frontier_cs/cli.py -> repo root
            track_dir = "algorithmic" if track == "algorithmic" else "research"
            solutions_dir = base_dir / track_dir / "solutions"

        if not solutions_dir.is_dir():
            track_dir = "algorithmic" if track == "algorithmic" else "research"
            print(f"Error: No solutions directory found. Expected {track_dir}/solutions/", file=sys.stderr)
            print("Use --solutions-dir or --pairs-file to specify", file=sys.stderr)
            return 1

        # Determine problems_dir for validation
        probs_dir = problems_dir
        if probs_dir is None:
            base_dir = Path(__file__).parents[2]
            track_dir = "algorithmic" if track == "algorithmic" else "research"
            probs_dir = base_dir / track_dir / "problems"

        pairs = scan_solutions_dir(solutions_dir, problems_dir=probs_dir)
        if not pairs:
            print(f"Error: No solution files found in {solutions_dir}", file=sys.stderr)
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
    print(f"Results saved to: {args.results_dir}")
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
    evaluator = FrontierCSEvaluator(backend="docker")

    if args.algorithmic:
        # Only list algorithmic problems in compact format
        problems = evaluator.list_problems("algorithmic")
        print(f"\nAlgorithmic Problems ({len(problems)} total):\n")
        ids_per_line = 10
        for i in range(0, len(problems), ids_per_line):
            line_ids = problems[i:i+ids_per_line]
            print("  " + ", ".join(line_ids))
    elif args.research:
        # Only list research problems
        all_research = evaluator.list_problems("research")
        research_problems = [p for p in all_research if not p.startswith("algorithmic/")]
        print(f"\nResearch Problems ({len(research_problems)} total):\n")
        for p in research_problems:
            print(f"  {p}")
    else:
        # List both tracks
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
    return 0


def run_show(args: argparse.Namespace) -> int:
    """Run show command."""
    evaluator = FrontierCSEvaluator(backend="docker")
    track = "algorithmic" if args.algorithmic else "research"
    statement = evaluator.get_problem_statement(track, args.problem_id)
    if statement:
        print(statement)
    else:
        print(f"Problem not found: {args.problem_id}", file=sys.stderr)
        return 1
    return 0


def run_eval(args: argparse.Namespace) -> int:
    """Run eval command."""
    # Determine track
    track = "algorithmic" if args.algorithmic else "research"

    # Create evaluator
    backend = "skypilot" if args.skypilot else "docker"
    idle_timeout = None if args.keep_cluster else getattr(args, 'idle_timeout', 10)
    timeout = getattr(args, 'timeout', None)
    evaluator = FrontierCSEvaluator(
        backend=backend,
        judge_url=args.judge_url,
        cloud=args.cloud,
        region=args.region,
        keep_cluster=getattr(args, 'keep_cluster', False),
        idle_timeout=idle_timeout,
        timeout=timeout,
    )

    # Auto-detect solution file format: {problem}.{model}.py
    solution_file_mode = False
    detected_problem = None
    detected_solution_file = None

    if args.problem_id:
        candidate = Path(args.problem_id)
        is_solution, detected_problem, detected_solution_file = detect_solution_file(candidate)
        if is_solution:
            solution_file_mode = True
            if not args.quiet:
                print(f"Detected solution file: {candidate}")
                print(f"  Problem (from filename): {detected_problem}")

    # Get problem IDs
    if solution_file_mode:
        if args.problems:
            problem_ids = [p.strip() for p in args.problems.split(",")]
        elif detected_problem:
            problem_ids = [detected_problem]
        else:
            print("Error: Could not parse problem from filename", file=sys.stderr)
            return 1
    else:
        problem_ids = get_problem_ids(args, evaluator, track)

    if not problem_ids:
        print("Error: No problems specified. Use --help for usage.", file=sys.stderr)
        return 1

    # Get solution code
    if args.code:
        code = args.code
    elif solution_file_mode and detected_solution_file:
        code = detected_solution_file.read_text(encoding="utf-8")
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
    else:
        # No command specified, show help
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
