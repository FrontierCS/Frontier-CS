"""Summary printing utilities for solution generation."""

from typing import Callable, List, Optional

from .colors import bold, dim, red, green, yellow, solution_name as format_solution_name


def print_generation_summary(
    generated: List[str],
    failed: List[str],
    skipped: Optional[List[str]] = None,
    max_display: int = 5,
    format_name: Optional[Callable[[str], str]] = None,
) -> None:
    """Print a summary of generation results.

    Args:
        generated: List of successfully generated solution names
        failed: List of failed solution names (may include error in parentheses)
        skipped: Optional list of skipped solution names
        max_display: Maximum number of items to display per category
        format_name: Optional function to format solution names (defaults to format_solution_name)
    """
    if format_name is None:
        format_name = format_solution_name

    print(f"\n{bold('Summary:')}")
    line = "─" * 40
    print(dim(line))

    if generated:
        print(f"  {green('✓')} Generated: {green(bold(str(len(generated))))} solution(s)")
        for name in generated[:max_display]:
            print(f"    {dim('•')} {format_name(name)}")
        if len(generated) > max_display:
            print(f"    {dim(f'... and {len(generated) - max_display} more')}")
    else:
        print(f"  {dim('•')} No new solutions generated.")

    if skipped:
        print(f"  {yellow('○')} Skipped: {yellow(bold(str(len(skipped))))} existing (use {bold('--force')} to regenerate)")

    if failed:
        print(f"  {red('✗')} Failed: {red(bold(str(len(failed))))} solution(s)")
        for name in failed[:max_display]:
            print(f"    {dim('•')} {red(name)}")
        if len(failed) > max_display:
            print(f"    {dim(f'... and {len(failed) - max_display} more')}")

    print(dim(line))
