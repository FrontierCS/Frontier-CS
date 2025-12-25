"""Colorful terminal output utilities."""

import sys

# ANSI color codes
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"

# Colors
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
WHITE = "\033[37m"

# Bright colors
BRIGHT_RED = "\033[91m"
BRIGHT_GREEN = "\033[92m"
BRIGHT_YELLOW = "\033[93m"
BRIGHT_BLUE = "\033[94m"
BRIGHT_MAGENTA = "\033[95m"
BRIGHT_CYAN = "\033[96m"

# Check if terminal supports colors
_USE_COLOR = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


def _c(text: str, color: str) -> str:
    """Apply color to text if terminal supports it."""
    if not _USE_COLOR:
        return text
    return f"{color}{text}{RESET}"


def bold(text: str) -> str:
    return _c(text, BOLD)


def dim(text: str) -> str:
    return _c(text, DIM)


def red(text: str) -> str:
    return _c(text, RED)


def green(text: str) -> str:
    return _c(text, GREEN)


def yellow(text: str) -> str:
    return _c(text, YELLOW)


def blue(text: str) -> str:
    return _c(text, BLUE)


def magenta(text: str) -> str:
    return _c(text, MAGENTA)


def cyan(text: str) -> str:
    return _c(text, CYAN)


def success(text: str) -> str:
    return _c(text, BRIGHT_GREEN)


def error(text: str) -> str:
    return _c(text, BRIGHT_RED)


def warning(text: str) -> str:
    return _c(text, BRIGHT_YELLOW)


def info(text: str) -> str:
    return _c(text, BRIGHT_CYAN)


def header(text: str) -> str:
    return _c(text, BOLD + BRIGHT_MAGENTA)


def section(text: str) -> str:
    return _c(text, BOLD + CYAN)


def model_name(text: str) -> str:
    return _c(text, BRIGHT_BLUE)


def problem_name(text: str) -> str:
    return _c(text, YELLOW)


def solution_name(text: str) -> str:
    return _c(text, GREEN)


# Semantic printers
def print_header(text: str) -> None:
    line = "=" * 60
    print(f"\n{header(line)}")
    print(header(text))
    print(f"{header(line)}\n")


def print_section(text: str) -> None:
    print(section(text))


def print_success(text: str) -> None:
    print(success(f"✓ {text}"))


def print_error(text: str) -> None:
    print(error(f"✗ {text}"))


def print_warning(text: str) -> None:
    print(warning(f"⚠ {text}"))


def print_info(text: str) -> None:
    print(info(f"→ {text}"))
