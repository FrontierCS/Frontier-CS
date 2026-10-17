"""Use real interactive comparisons to verify the executable budget reference."""
import math
from pathlib import Path
import re
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def binary(tmp_path_factory):
    target = tmp_path_factory.mktemp("problem59_budget") / "interactor"
    subprocess.run(["g++", "-std=c++17", "-O2",
                    "-I" + str(ROOT / "algorithmic/judge/include"),
                    str(ROOT / "algorithmic/problems/59/interactor.cpp"),
                    "-o", str(target)], check=True)
    return target


def play(binary, directory, queries, wrong=False):
    n = 1 if queries == 0 else 2
    inp = directory / "input"
    ans = directory / "answer"
    inp.write_text(f"{n}\n")
    ans.write_text("")
    p = subprocess.Popen([str(binary), str(inp), str(directory / "transcript"), str(ans)],
                         stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, text=True)
    try:
        assert p.stdout.readline().strip() == str(n)
        if n == 2:
            p.stdin.write("? 1 2\n")
            p.stdin.flush()
            comparison = p.stdout.readline().strip()
            assert comparison in {"<", ">"}
            values = [1, 2] if comparison == "<" else [2, 1]
            if wrong:
                values.reverse()
            commands = "? 1 2\n" * (queries - 1)
        else:
            values, commands = [1], ""
        commands += "! " + " ".join(map(str, values)) + "\n"
        _, error = p.communicate(commands, timeout=5)
        return p.returncode, error
    finally:
        if p.poll() is None:
            p.kill()
            p.wait()


@pytest.mark.parametrize("queries", [0, 1, 2, 8])
def test_zero_halving_and_budget_anchor(binary, tmp_path, queries):
    status, message = play(binary, tmp_path, queries)
    assert status == 7, message
    points = 100 * float(re.search(r"Ratio:\s*([0-9.]+)", message)[1])
    expected = 100 if queries == 0 else 60 + math.log(8 / queries)
    assert points == pytest.approx(expected, abs=1e-9)


@pytest.mark.parametrize("queries,wrong", [(9, False), (1, True)])
def test_excess_queries_and_wrong_answer_rejected(binary, tmp_path, queries, wrong):
    status, message = play(binary, tmp_path, queries, wrong)
    assert status == 1, message
