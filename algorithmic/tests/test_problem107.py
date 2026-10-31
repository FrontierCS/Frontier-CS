"""A guess must not pass the error check by overflowing 2 * d (#203)."""
import math
from pathlib import Path
import re
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'algorithmic/problems/107/testdata'


@pytest.fixture(scope='module')
def interactor(tmp_path_factory):
    executable = tmp_path_factory.mktemp('interactor107') / 'interactor'
    subprocess.run(['g++', '-std=gnu++17', '-O2', '-I' + str(ROOT / 'algorithmic/judge/include'),
                    str(ROOT / 'algorithmic/problems/107/interactor.cpp'), '-o', str(executable)], check=True)
    return executable


def play(interactor, tmp_path, data, answer, contestant):
    inf, transcript, ans = [tmp_path / name for name in ('in', 'transcript', 'ans')]
    inf.write_text(data);ans.write_text(answer)
    return subprocess.run([str(interactor), str(inf), str(transcript), str(ans)],
                          input=contestant, text=True, capture_output=True, timeout=5)


def ratio(result):
    return float(re.search(r'Ratio: ([0-9.]+)', result.stderr).group(1))


# 720720 has 240 divisors. In 32-bit arithmetic the first three guesses pass,
# because 2 * d wraps to a positive value.
@pytest.mark.parametrize('guess', [-1500000000, -1073741825, -2147483528, -2147483648, 2147483647])
def test_overflowing_guess_is_wrong(interactor, tmp_path, guess):
    result = play(interactor, tmp_path, '1\n720720\n', '240\n', '1 %d\n' % guess)
    assert result.returncode == 7, result.stderr
    assert 'Wrong guess' in result.stderr and ratio(result) == 0


def test_issue_repro_on_testdata_scores_zero(interactor, tmp_path):
    games = int((DATA / '1.in').read_text().split()[0])
    result = play(interactor, tmp_path, (DATA / '1.in').read_text(), (DATA / '1.ans').read_text(),
                  '1 -1500000000\n' * games)
    assert result.returncode == 7, result.stderr
    assert 'Wrong guess' in result.stderr and ratio(result) == 0


# Accepted iff |guess - divisors| <= 7 or 1/2 <= guess/divisors <= 2.
@pytest.mark.parametrize('x,divisors,guess,correct', [
    (720720, 240, 120, True), (720720, 240, 119, False), (720720, 240, 480, True), (720720, 240, 481, False),
    (1, 1, -6, True), (1, 1, -7, False), (1, 1, 8, True), (1, 1, 9, False),
])
def test_error_bounds_are_unchanged(interactor, tmp_path, x, divisors, guess, correct):
    result = play(interactor, tmp_path, '1\n%d\n' % x, '%d\n' % divisors, '1 %d\n' % guess)
    assert result.returncode == 7, result.stderr
    assert ('Wrong guess' not in result.stderr) == correct
    assert ratio(result) == (1 if correct else 0)


def test_query_count_still_scores(interactor, tmp_path):
    result = play(interactor, tmp_path, '1\n720720\n', '240\n', '0 16\n1 240\n')
    assert result.returncode == 7, result.stderr
    assert result.stdout.split() == ['1', '16']
    assert ratio(result) == pytest.approx((60 + math.log(40)) / 100, abs=1e-9)
