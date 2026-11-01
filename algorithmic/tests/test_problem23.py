"""Every test must run the submitted A=B program; Tid % 100 == 0 used to be accepted unchecked (#205)."""
from pathlib import Path
import re
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'algorithmic/problems/23/testdata'
RELEASED = sorted(int(p.stem) for p in DATA.glob('*.in'))
# Every N.ans holds the same correct A=B program for the substring task.
REFERENCE = (DATA / '1.ans').read_text()
EMPTY, ONE_RULE = '', 'a=b\n'


@pytest.fixture(scope='module')
def checker(tmp_path_factory):
    executable = tmp_path_factory.mktemp('checker23') / 'checker'
    subprocess.run(['g++', '-std=gnu++17', '-O2', '-I' + str(ROOT / 'algorithmic/judge/include'),
                    str(ROOT / 'algorithmic/problems/23/check.cpp'), '-o', str(executable)], check=True)
    return executable


def check(checker, tmp_path, data, program):
    inf, out = tmp_path / 'in', tmp_path / 'out'
    inf.write_text(data)
    out.write_text(program)
    return subprocess.run([str(checker), str(inf), str(out), str(DATA / '1.ans')],
                          text=True, capture_output=True, timeout=30)


# Tid % 100 picks the test set, and set 0 is empty. The ids at the pinned commit
# c7ec558 were 0, 100 and 200, and each accepted any parseable program as "ok Test 0.".
@pytest.mark.parametrize('tid', [0, 100, 200, 2000000000])
@pytest.mark.parametrize('program', [EMPTY, ONE_RULE, REFERENCE], ids=['empty', 'one-rule', 'reference'])
def test_tid_divisible_by_100_is_never_accepted(checker, tmp_path, tid, program):
    result = check(checker, tmp_path, '%d\n' % tid, program)
    assert result.returncode == 3, result.stderr
    assert 'generates no test strings' in result.stderr


# 17 to 20 indexed past the 17 generators and crashed; 21 to 99 fell back to the
# empty set 0 and scored nan.
@pytest.mark.parametrize('tid', [17, 20, 21, 50, 1234567899])
def test_tid_without_a_test_set_is_a_data_error(checker, tmp_path, tid):
    result = check(checker, tmp_path, '%d\n' % tid, REFERENCE)
    assert result.returncode == 3, result.stderr
    assert result.stderr.startswith('FAIL Tid %d ' % tid), result.stderr


@pytest.mark.parametrize('test', RELEASED)
def test_released_tests_run_the_program(checker, tmp_path, test):
    data = (DATA / ('%d.in' % test)).read_text()
    for program in (EMPTY, ONE_RULE):
        result = check(checker, tmp_path, data, program)
        assert result.returncode == 1 and 'WA on Test case' in result.stderr, result.stderr
    result = check(checker, tmp_path, data, REFERENCE)
    assert result.returncode == 7, result.stderr
    assert 0 < float(re.search(r'Ratio: ([0-9.]+)', result.stderr).group(1)) <= 1
