#!/usr/bin/env python3
"""
CLI interface for Frontier-CS evaluation.

Usage:
    # Single problem evaluation
    frontier-eval flash_attn solution.py
    frontier-eval --algorithmic 1 solution.cpp

    # With SkyPilot
    frontier-eval flash_attn solution.py --skypilot

    # All problems for a solution
    frontier-eval --all-problems solution.py

    # Specific problems
    frontier-eval --problems flash_attn,cross_entropy solution.py

    # List problems
    frontier-eval --list
    frontier-eval --list --algorithmic

    # Batch evaluation (requires pairs file)
    frontier-eval batch --pairs-file pairs.txt
    frontier-eval batch --resume --results-dir results/batch1
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import List, Optional

from .evaluator import FrontierCSEvaluator
from .runner import EvaluationResult

logger = logging.getLogger(__name__)


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser."""
    parser = argparse.ArgumentParser(
        prog="frontier-eval",
        description="Evaluate solutions for Frontier-CS problems",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Evaluate a research problem
  frontier-eval flash_attn solution.py

  # Evaluate an algorithmic problem
  frontier-eval --algorithmic 1 solution.cpp

  # Evaluate with SkyPilot (cloud)
  frontier-eval flash_attn solution.py --skypilot

  # Evaluate multiple problems
  frontier-eval --problems flash_attn,cross_entropy solution.py

  # Evaluate all research problems
  frontier-eval --all-problems solution.py

  # List available problems
  frontier-eval --list
        """,
    )

    # Problem and solution arguments (as options to avoid conflict with subcommands)
    parser.add_argument(
        "problem_id",
        nargs="?",
        default=None,
        help="Problem ID (e.g., flash_attn, gemm_optimization/squares)",
    )
    parser.add_argument(
        "solution",
        nargs="?",
        default=None,
        help="Path to solution file",
    )

    # Problem selection
    problem_group = parser.add_argument_group("Problem Selection")
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
    backend_group = parser.add_argument_group("Backend Options")
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
        "--judge-url",
        type=str,
        default="http://localhost:8081",
        help="Judge server URL for algorithmic problems",
    )

    # Evaluation options
    eval_group = parser.add_argument_group("Evaluation Options")
    eval_group.add_argument(
        "--timeout",
        type=int,
        help="Timeout in seconds per problem",
    )
    eval_group.add_argument(
        "--code",
        type=str,
        help="Solution code as string (alternative to file)",
    )

    # Output options
    output_group = parser.add_argument_group("Output Options")
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

    # Info commands
    info_group = parser.add_argument_group("Info Commands")
    info_group.add_argument(
        "--list",
        action="store_true",
        help="List available problems",
    )
    info_group.add_argument(
        "--show",
        action="store_true",
        help="Show problem statement",
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Batch subcommand
    batch_parser = subparsers.add_parser(
        "batch",
        help="Batch evaluation with incremental progress",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Evaluate from pairs file
  frontier-eval batch --pairs-file pairs.txt

  # Evaluate specific pairs
  frontier-eval batch --pairs "sol1:flash_attn,sol2:cross_entropy"

  # Resume interrupted evaluation
  frontier-eval batch --resume --results-dir results/batch1

  # Check evaluation status
  frontier-eval batch --status --results-dir results/batch1

Pairs file format (solution:problem per line):
  gpt5_flash_attn:flash_attn
  claude_sonnet_4_5_cross_entropy:cross_entropy
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

    batch_output = batch_parser.add_argument_group("Output Options")
    batch_output.add_argument(
        "--results-dir",
        type=Path,
        default=Path("results/batch"),
        help="Directory for results and state (default: results/batch)",
    )

    batch_backend = batch_parser.add_argument_group("Backend Options")
    batch_backend.add_argument(
        "--skypilot",
        action="store_true",
        help="Use SkyPilot for cloud evaluation",
    )
    batch_backend.add_argument(
        "--max-concurrent",
        type=int,
        default=1,
        help="Maximum concurrent evaluations (default: 1)",
    )
    batch_backend.add_argument(
        "--timeout",
        type=int,
        help="Timeout per evaluation in seconds",
    )
    batch_backend.add_argument(
        "--bucket-url",
        type=str,
        help="Bucket URL for result storage (s3://... or gs://...). "
             "Results are written directly to the bucket by each worker and "
             "synced incrementally. Enables reliable resume across runs.",
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
        help="Retry all failed pairs",
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
        data.append({
            "problem_id": r.problem_id,
            "score": r.score,
            "status": r.status.value,
            "message": r.message,
            "duration_seconds": r.duration_seconds,
        })
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

    # Create batch evaluator
    backend = "skypilot" if args.skypilot else "docker"
    bucket_url = getattr(args, "bucket_url", None)
    batch = BatchEvaluator(
        results_dir=args.results_dir,
        backend=backend,
        max_concurrent=args.max_concurrent,
        timeout=args.timeout,
        bucket_url=bucket_url,
    )

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
        print("\nAggregated Results by Model")
        print("=" * 60)
        by_model = batch.state.aggregate_by_model()
        for model, stats in sorted(by_model.items()):
            avg = f"{stats['avg_score']:.4f}" if stats['avg_score'] is not None else "N/A"
            print(f"  {model}: {stats['successful']}/{stats['total']} successful, avg={avg}")

        print("\nAggregated Results by Problem")
        print("=" * 60)
        by_problem = batch.state.aggregate_by_problem()
        for problem, stats in sorted(by_problem.items()):
            avg = f"{stats['avg_score']:.4f}" if stats['avg_score'] is not None else "N/A"
            print(f"  {problem}: {stats['successful']}/{stats['total']} successful, avg={avg}")
        return 0

    # Handle export-failed command
    if args.export_failed:
        count = batch.state.export_failed(args.export_failed)
        print(f"Exported {count} failed pairs to {args.export_failed}")
        return 0

    # Handle retry-failed command
    if args.retry_failed:
        print(f"\nRetrying failed pairs from {args.results_dir}")
        state = batch.retry_failed()
        print(f"\nComplete: {state.success_count}/{state.total_pairs} successful")
        return 0 if state.error_count == 0 else 1

    # Handle resume command
    if args.resume:
        print(f"\nResuming batch evaluation from {args.results_dir}")
        state = batch.resume()
        print(f"\nComplete: {state.success_count}/{state.total_pairs} successful")
        return 0 if state.error_count == 0 else 1

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

        print(f"\nBatch evaluation: {len(pairs)} pairs")
        state = batch.evaluate_pairs(pairs, resume=resume)

    elif args.pairs_file:
        # Mode: pairs file
        if not args.pairs_file.exists():
            print(f"Error: Pairs file not found: {args.pairs_file}", file=sys.stderr)
            return 1

        print(f"\nBatch evaluation from pairs file: {args.pairs_file}")
        state = batch.evaluate_pairs_file(args.pairs_file, resume=resume)

    else:
        print("Error: Specify input with --pairs or --pairs-file", file=sys.stderr)
        return 1

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

    return 0 if state.error_count == 0 else 1


def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point."""
    if argv is None:
        argv = sys.argv[1:]

    # Handle subcommands first by checking if first arg is a subcommand
    subcommands = {"batch"}
    if argv and argv[0] in subcommands:
        parser = create_parser()
        args = parser.parse_args(argv)
        if args.command == "batch":
            return run_batch(args)

    # For single evaluations, create a parser without subcommands
    # to avoid argparse confusion with positional args
    parser = create_parser()
    # Inject a dummy command to satisfy the subparser
    args = parser.parse_args(argv + ["batch", "--status"]) if not any(a in argv for a in subcommands) else parser.parse_args(argv)
    # Reset command since we used a dummy
    args.command = None
    args.status = False

    # Determine track
    track = "algorithmic" if args.algorithmic else "research"

    # Create evaluator
    backend = "skypilot" if args.skypilot else "docker"
    evaluator = FrontierCSEvaluator(
        backend=backend,
        judge_url=args.judge_url,
        cloud=args.cloud,
        region=args.region,
    )

    # Handle info commands
    if args.list:
        if args.algorithmic:
            # Only list algorithmic problems in compact format
            problems = evaluator.list_problems("algorithmic")
            print(f"\nAlgorithmic Problems ({len(problems)} total):\n")
            # Display 10 IDs per line
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
            # List both tracks separately - research first, then algorithmic
            # Get research problems (excluding algorithmic)
            all_research = evaluator.list_problems("research")
            research_problems = [p for p in all_research if not p.startswith("algorithmic/")]
            print(f"\nResearch Problems ({len(research_problems)} total):\n")
            for p in research_problems:
                print(f"  {p}")
            
            # Get algorithmic problems - show in compact format (multiple per line)
            alg_problems = evaluator.list_problems("algorithmic")
            print(f"\nAlgorithmic Problems ({len(alg_problems)} total):\n")
            # Display 10 IDs per line
            ids_per_line = 10
            for i in range(0, len(alg_problems), ids_per_line):
                line_ids = alg_problems[i:i+ids_per_line]
                print("  " + ", ".join(line_ids))
        return 0

    if args.show:
        if not args.problem_id:
            print("Error: --show requires a problem_id", file=sys.stderr)
            return 1
        statement = evaluator.get_problem_statement(track, args.problem_id)
        if statement:
            print(statement)
        else:
            print(f"Problem not found: {args.problem_id}", file=sys.stderr)
            return 1
        return 0

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
        print("Error: No solution provided. Use --code or provide a file path.", file=sys.stderr)
        return 1

    # Run evaluations
    results = []
    for pid in problem_ids:
        if not args.quiet:
            print(f"Evaluating {pid}...", end=" ", flush=True)

        result = evaluator.evaluate(track, pid, code, timeout=args.timeout)
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


if __name__ == "__main__":
    sys.exit(main())
