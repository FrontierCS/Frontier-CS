"""Validate released permutation data and the interactor's query-limit boundary."""
from pathlib import Path
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[2]
PROBLEM = ROOT / 'algorithmic/problems/82'


def test_all_released_inputs_have_a_header_and_valid_permutation():
    for path in (PROBLEM / 'testdata').glob('*.in'):
        n, *permutation = map(int, path.read_text().split())
        assert 3 <= n <= 2048, path
        assert len(permutation) == n, path
        assert sorted(permutation) == list(range(n)), path


@pytest.fixture(scope='module')
def interactor(tmp_path_factory):
    executable = tmp_path_factory.mktemp('interactor82') / 'interactor'
    subprocess.run(['g++', '-std=gnu++17', '-O2',
                    '-I' + str(ROOT / 'algorithmic/judge/include'),
                    str(PROBLEM / 'interactor.cc'), '-o', str(executable)], check=True)
    return executable


@pytest.mark.parametrize('queries', [0, 4269, 4270])
def test_query_limit(interactor, tmp_path, queries):
    inf, ans, transcript = [tmp_path / name for name in ('in', 'ans', 'transcript')]
    inf.write_text('3\n0 1 2\n')
    ans.write_text('2\n')
    result = subprocess.run([str(interactor), str(inf), str(transcript), str(ans)],
                            input='? 1 2\n' * queries + '! 0 1 2\n',
                            text=True, capture_output=True, timeout=10)
    assert result.returncode == 7, result.stderr
    output = result.stdout.splitlines()
    assert output[0] == '3'
    if queries <= 4269:
        assert len(output) == queries + 1
        assert 'Accepted.' in result.stderr
    else:
        assert len(output) == 4271
        assert output[-1] == '-1'
        assert 'attempted query 4270 > 4269' in result.stderr
        assert 'Ratio: 0.000000000000' in result.stderr
