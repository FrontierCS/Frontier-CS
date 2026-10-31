"""The problem 59 interactor must not be solvable with zero queries (#208).

Before the fix the interactor built its hidden array with testlib's rng at the
fixed default seed and never reseeded, so a program replaying that stream scored
100 without asking a single comparison. The fix reads a per-test secret seed from
the (hidden) answer file. These tests reconstruct the array the interactor will
use from the committed secret seed and feed it back with no queries: the array
from the committed seed is accepted, while the array from the old default seed is
rejected on every non-trivial test, proving the exploit is defeated.
"""
import os
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "algorithmic/problems/59/testdata"
TESTS = list(range(1, 11))

# testlib random_t: java-style 48-bit LCG.
_MUL, _ADD, _MASK = 0x5DEECE66D, 0xB, (1 << 48) - 1
_LLMAX = 9223372036854775807
_DEFAULT_SEED = 3905348978240129619


class _Rng:
    def __init__(self, secret=None):
        # registerInteraction leaves the default seed; setSeed(s) xors with the multiplier.
        self.s = _DEFAULT_SEED if secret is None else ((secret ^ _MUL) & _MASK)

    def _bits(self, bits):
        if bits <= 48:
            self.s = (self.s * _MUL + _ADD) & _MASK
            return self.s >> (48 - bits)
        return (self._bits(31) << 32) ^ self._bits(32)  # lowerBitCount = 32 (version = -1)

    def _next(self, n):
        limit = _LLMAX // n * n
        while True:
            b = self._bits(63)
            if b < limit:
                return b % n

    def nrange(self, a, b):
        return a + self._next(b - a + 1)


def _hidden_array(n, secret):
    rng = _Rng(secret)
    a = list(range(1, n + 1))
    for i in range(n):
        j = rng.nrange(i, min(n - 1, i + 2))
        a[i], a[j] = a[j], a[i]
    return a


@pytest.fixture(scope="module")
def interactor(tmp_path_factory):
    exe = tmp_path_factory.mktemp("interactor59") / "interactor"
    subprocess.run(
        ["g++", "-std=gnu++17", "-O2", "-I" + str(ROOT / "algorithmic/judge/include"),
         str(ROOT / "algorithmic/problems/59/interactor.cpp"), "-o", str(exe)],
        check=True,
    )
    return exe


def _play(interactor, t, array):
    """Send `array` as the final answer with no queries; return (returncode, stderr)."""
    inf, ans = DATA / f"{t}.in", DATA / f"{t}.ans"
    proc = subprocess.Popen(
        [str(interactor), str(inf), os.devnull, str(ans)],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    n = int(proc.stdout.readline())
    proc.stdin.write("! " + " ".join(map(str, array)) + "\n")
    proc.stdin.flush()
    proc.stdin.close()
    err = proc.stderr.read()
    proc.wait()
    return proc.returncode, n, err


@pytest.mark.parametrize("t", TESTS)
def test_correct_array_is_accepted(interactor, t):
    secret = int((DATA / f"{t}.ans").read_text().split()[0])
    n = int((DATA / f"{t}.in").read_text().split()[0])
    rc, got_n, err = _play(interactor, t, _hidden_array(n, secret))
    assert got_n == n
    assert rc == 7, err  # testlib _points: a correct answer scores
    assert "Ratio: 1.0" in err


@pytest.mark.parametrize("t", TESTS)
def test_default_seed_replay_is_rejected(interactor, t):
    n = int((DATA / f"{t}.in").read_text().split()[0])
    if n < 2:
        pytest.skip("n=1 has a unique array, so no seed can distinguish it")
    rc, _, err = _play(interactor, t, _hidden_array(n, None))
    assert rc != 7, "zero-query default-seed replay must no longer score (#208)"
    assert "Wrong final array" in err
