"""Every test id must run the program; Tid % 100 == 0 used to be accepted unchecked (#205)."""
from pathlib import Path
import re
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'algorithmic/problems/23/testdata'
# 1.ans holds a correct A=B program for the substring task.
REFERENCE = (DATA / '1.ans').read_text()
EMPTY, ONE_RULE = '', 'a=b\n'


@pytest.fixture(scope='module')
def checker(tmp_path_factory):
    executable = tmp_path_factory.mktemp('checker23') / 'checker'
    subprocess.run(['g++', '-std=gnu++17', '-O2', '-I' + str(ROOT / 'algorithmic/judge/include'),
                    str(ROOT / 'algorithmic/problems/23/check.cpp'), '-o', str(executable)], check=True)
    return executable


def check(checker, tmp_path, tid, program):
    inf, out = tmp_path / 'in', tmp_path / 'out'
    inf.write_text('%d\n' % tid);out.write_text(program)
    return subprocess.run([str(checker), str(inf), str(out), str(DATA / '1.ans')],
                          text=True, capture_output=True, timeout=30)


def ratio(result):
    return float(re.search(r'Ratio: ([0-9.]+)', result.stderr).group(1))


# The ids at the pinned commit c7ec558 were 0, 100 and 200; 50 has no generator of its own.
@pytest.mark.parametrize('tid', [0, 100, 200, 50])
@pytest.mark.parametrize('program', [EMPTY, ONE_RULE])
def test_program_that_solves_nothing_is_wrong(checker, tmp_path, tid, program):
    result = check(checker, tmp_path, tid, program)
    assert result.returncode == 1, result.stderr
    assert 'WA on Test case' in result.stderr and 'Test 0.' not in result.stderr


@pytest.mark.parametrize('tid', [0, 100, 200, 50])
def test_correct_program_still_scores(checker, tmp_path, tid):
    result = check(checker, tmp_path, tid, REFERENCE)
    assert result.returncode == 7, result.stderr
    assert 0 < ratio(result) <= 1


def test_existing_test_ids_are_unchanged(checker, tmp_path):
    tid = int((DATA / '1.in').read_text().split()[0])
    assert check(checker, tmp_path, tid, EMPTY).returncode == 1
    result = check(checker, tmp_path, tid, REFERENCE)
    assert result.returncode == 7, result.stderr
    assert 0 < ratio(result) <= 1
