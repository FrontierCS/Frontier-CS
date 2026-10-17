"""Native valid-partition regressions for problem45's original 60-point cost."""
import math
from pathlib import Path
import re
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]
CYCLE = '8 8 2 0\n1 2\n2 3\n3 4\n4 5\n5 6\n6 7\n7 8\n8 1\n'
TWO = '1 1 1 1 2 2 2 2\n'  # EC=CV=2
FOUR = '1 1 2 2 1 1 2 2\n'  # EC=CV=4


@pytest.fixture(scope='module')
def checker(tmp_path_factory):
    target = tmp_path_factory.mktemp('original_anchor45') / 'checker'
    subprocess.run(['g++', '-std=c++17', '-O2',
                    '-I' + str(ROOT / 'algorithmic/judge/include'),
                    str(ROOT / 'algorithmic/problems/45/chk.cc'),
                    '-o', str(target)], check=True)
    return target


def run(checker, tmp_path, output, answer, data=CYCLE, valid=True):
    paths = [tmp_path / name for name in ['input', 'output', 'answer']]
    for path, text in zip(paths, [data, output, answer]):
        path.write_text(text)
    proc = subprocess.run([str(checker), *map(str, paths)],
                          capture_output=True, text=True, timeout=10)
    if not valid:
        assert proc.returncode == 1
        assert 'Balance violated' in proc.stderr
        return
    assert proc.returncode == 7, proc.stderr
    return 100 * float(re.search(r'Ratio:\s*([0-9.]+)', proc.stderr)[1])


@pytest.mark.parametrize('answer,expected', [
    ('0 0 8 8\n', 50),   # original lower band, not the erroneous30
    ('0 0 10 10\n', 60), # .4*baseline=4
    ('2 2 7 7\n', 60),  # general anchor .4B+.6R=4
])
def test_original_lower_band_and_reference(checker, tmp_path, answer, expected):
    assert run(checker, tmp_path, FOUR, answer) == pytest.approx(expected, abs=1e-9)


def test_halving_both_costs_adds_one_ln2(checker, tmp_path):
    reference = run(checker, tmp_path, FOUR, '0 0 10 10\n')
    improved = run(checker, tmp_path, TWO, '0 0 10 10\n')
    assert improved - reference == pytest.approx(math.log(2), abs=1e-9)


def test_two_metric_mean_preserves_half_weight(checker, tmp_path):
    # Different baselines put both metrics above60. Doubling only EC's
    # physical reference doubles only its improvement factor.
    first = run(checker, tmp_path, TWO, '0 0 10 10\n')
    second = run(checker, tmp_path, TWO, '0 0 20 10\n')
    assert second - first == pytest.approx(math.log(2)/2, abs=1e-9)


def test_mixed_lower_and_upper_metrics(checker, tmp_path):
    score = run(checker, tmp_path, TWO, '0 0 10 4\n')
    assert score == pytest.approx((60 + math.log(2) + 50)/2, abs=1e-9)


@pytest.mark.parametrize('answer,expected', [('2 2 2 2\n', 100), ('1 1 1 1\n', 0)])
def test_original_degenerate_binary_branch(checker, tmp_path, answer, expected):
    assert run(checker, tmp_path, TWO, answer) == pytest.approx(expected, abs=1e-9)


def test_valid_zero_cost(checker, tmp_path):
    disconnected = '8 4 2 0\n1 2\n3 4\n5 6\n7 8\n'
    assert run(checker, tmp_path, TWO, '0 0 10 10\n', disconnected) == 100


def test_balance_validation_precedes_zero_cost(checker, tmp_path):
    run(checker, tmp_path, '1 1 1 1 1 1 1 1\n', '0 0 10 10\n', valid=False)
