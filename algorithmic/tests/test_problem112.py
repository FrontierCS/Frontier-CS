"""A claimed distance must be finite: testlib reads 1e400 as inf (#202)."""
import math
from pathlib import Path
import re
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'algorithmic/problems/112/testdata'
N = int((DATA / '12.in').read_text())


@pytest.fixture(scope='module')
def checker(tmp_path_factory):
    executable = tmp_path_factory.mktemp('checker112') / 'checker'
    subprocess.run(['g++', '-std=gnu++17', '-O2', '-I' + str(ROOT / 'algorithmic/judge/include'),
                    str(ROOT / 'algorithmic/problems/112/chk.cc'), '-o', str(executable)], check=True)
    return executable


def spread(n):
    # Fibonacci lattice on the unit sphere.
    points = []
    for i in range(n):
        z = 1 - (2 * i + 1) / n
        theta = i * math.pi * (3 - math.sqrt(5))
        points.append((math.sqrt(1 - z * z) * math.cos(theta), math.sqrt(1 - z * z) * math.sin(theta), z))
    return points


def output(claim, points):
    return claim + '\n' + ''.join('%.17g %.17g %.17g\n' % p for p in points)


def check(checker, tmp_path, text):
    out = tmp_path / 'output'
    out.write_text(text)
    return subprocess.run([str(checker), str(DATA / '12.in'), str(out), str(DATA / '12.ans')],
                          text=True, capture_output=True, timeout=10)


@pytest.mark.parametrize('claim', ['1e400', '1e309'])
@pytest.mark.parametrize('placement', ['origin', 'spread'])
def test_infinite_claim_is_wrong(checker, tmp_path, claim, placement):
    points = [(0.0, 0.0, 0.0)] * N if placement == 'origin' else spread(N)
    result = check(checker, tmp_path, output(claim, points))
    assert result.returncode == 1, result.stderr
    assert 'not a finite number' in result.stderr


def test_infinite_coordinate_is_wrong(checker, tmp_path):
    # The sphere check rejects it, since inf * inf is inf; testlib never reads a NaN.
    result = check(checker, tmp_path, '0\n1e400 0 0\n' + '0 0 0\n' * (N - 1))
    assert result.returncode == 1, result.stderr
    assert 'outside the unit sphere' in result.stderr


def test_matching_claim_still_scores(checker, tmp_path):
    points = spread(N)
    claim = min(math.dist(p, q) for i, p in enumerate(points) for q in points[:i])
    result = check(checker, tmp_path, output(repr(claim), points))
    assert result.returncode == 7, result.stderr
    ref = float((DATA / '12.ans').read_text().split()[0])
    lower = 60 * claim / ref
    expected = lower if lower <= 60 else min(100, 60 + math.log(claim / ref))
    assert float(re.search(r'Ratio: ([0-9.]+)', result.stderr).group(1)) == pytest.approx(expected / 100, abs=1e-9)
