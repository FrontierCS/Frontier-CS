"""Physical zero and completion-stage regressions for the ln reference rule."""
import math
from pathlib import Path
import re
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope='module')
def binaries(tmp_path_factory):
    directory = tmp_path_factory.mktemp('ln_boundary_bins')
    result = {}
    for pid, filename in [(3, 'interactor.cc'), (150, 'chk.cc')]:
        target = directory/str(pid)
        subprocess.run(['g++', '-std=c++17', '-O2',
                        '-I'+str(ROOT/'algorithmic/judge/include'),
                        str(ROOT/f'algorithmic/problems/{pid}/{filename}'),
                        '-o', str(target)], check=True)
        result[pid] = target
    return result


@pytest.mark.parametrize('mode', ['zero', 'wrong', 'empty_batch', 'one_flip'])
def test_zero_rounds_is_distinct_from_shifted_composite_cost(binaries, tmp_path, mode):
    data = ROOT/'algorithmic/problems/3/testdata'
    answer = (data/'1.ans').read_text().strip()
    if mode == 'wrong':
        tokens = answer.split()
        tokens[0], tokens[1] = tokens[1], tokens[0]
        answer = ' '.join(tokens)
    prefix = {'zero': '', 'wrong': '', 'empty_batch': '0\n', 'one_flip': '1\n1\n'}[mode]
    proc = subprocess.run([str(binaries[3]), str(data/'1.in'),
                           str(tmp_path/'transcript'), str(data/'1.ans')],
                          input=prefix+'-1\n'+answer+'\n',
                          capture_output=True, text=True, timeout=15)
    if mode == 'wrong':
        assert proc.returncode == 1
        assert 'Final answer is incorrect' in proc.stderr
        return
    assert proc.returncode == 7, proc.stderr
    ratio = float(re.search(r'Ratio:\s*([0-9.]+)', proc.stderr)[1])
    if mode == 'zero':
        assert ratio == 1
    else:
        cost = 2 if mode == 'empty_batch' else 4
        assert ratio == pytest.approx(.6+math.log(19*15000001/cost)/100, abs=1e-11)
        assert ratio < 1


@pytest.mark.parametrize('reference,grid,expected', [
    (40000000, 'AA\nAA\n', .6+math.log(.5/.4)/100),
    (40000000, 'AB\nAB\n', .6+math.log(1/.4)/100),
    (40000000, 'AB\n..\n', .6+math.log(2/.4)/100),
    (40000000, '..\n..\n', 0),
    (100000000, 'AB\nAB\n', .6),
    (100000000, 'AB\n..\n', .6+math.log(2)/100),
])
def test_completed_grid_compares_occupied_cells_not_rounded_reward(
        binaries, tmp_path, reference, grid, expected):
    inp, out, ans = [tmp_path/name for name in ['input', 'output', 'answer']]
    inp.write_text('2 2\nA\nB\n')
    out.write_text(grid)
    ans.write_text(f'0 {reference}\n')
    proc = subprocess.run([str(binaries[150]), str(inp), str(out), str(ans)],
                          capture_output=True, text=True, timeout=15)
    assert proc.returncode == 7, proc.stderr
    ratio = float(re.search(r'Ratio:\s*([0-9.]+)', proc.stderr)[1])
    assert ratio == pytest.approx(expected, abs=1e-11)
