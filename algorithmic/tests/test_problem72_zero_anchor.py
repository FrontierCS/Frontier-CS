"""Native regressions for the puzzle checker's zero-reference ln coefficient."""
import math
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def checker(tmp_path_factory):
    executable = tmp_path_factory.mktemp("puzzle72_zero_reference") / "checker"
    subprocess.run([
        "g++", "-std=c++17", "-O2", "-I" + str(ROOT / "algorithmic/judge/include"),
        str(ROOT / "algorithmic/problems/72/chk.cc"), "-o", str(executable),
    ], check=True)
    return executable


def run_checker(checker, tmp_path, reference, claimed=2):
    # A real, valid length-two red car at the exit needs the two exit moves.
    # No formation moves are necessary; the checker independently runs BFS.
    board = [[0] * 6 for _ in range(6)]
    board[2][4] = board[2][5] = 1
    inp, out, ans = (tmp_path / name for name in ("input", "output", "answer"))
    inp.write_text("\n".join(" ".join(map(str, row)) for row in board) + "\n")
    out.write_text(f"{claimed} 0\n")
    ans.write_text(f"{reference} 0\n")
    result = subprocess.run([str(checker), str(inp), str(out), str(ans)],
                            capture_output=True, text=True, timeout=10)
    return result


@pytest.mark.parametrize("reference,expected", [
    (0, 60 + math.log(3)),    # Explicit degenerate reference: coefficient one.
    (1, 60 + math.log(2)),    # Positive reference: physical objective ratio 2/1.
    (2, 60),                # At the physical reference.
    (3, 45),                # Unchanged shifted low branch: 60*(2+1)/(3+1).
])
def test_native_coefficient_and_low_branch(checker, tmp_path, reference, expected):
    result = run_checker(checker, tmp_path, reference)
    assert result.returncode == 7, result.stderr
    ratio = re.search(r"Ratio: ([0-9.]+)", result.stderr)
    assert ratio, result.stderr
    assert 100 * float(ratio[1]) == pytest.approx(expected, abs=1e-9)


def test_zero_reference_does_not_bypass_correctness(checker, tmp_path):
    result = run_checker(checker, tmp_path, reference=0, claimed=3)
    assert result.returncode == 1
    assert "does not match actual" in result.stderr
