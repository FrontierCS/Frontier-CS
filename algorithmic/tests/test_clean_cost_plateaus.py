"""Native checks: completed-task upper scores scale actual cost, including reward floors."""
import math
from pathlib import Path
import re
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope='module')
def binaries(tmp_path_factory):
    directory = tmp_path_factory.mktemp('clean_cost_plateaus')
    result = {}
    for pid in (164, 165):
        target = directory / str(pid)
        subprocess.run(['g++', '-std=c++17', '-O2',
                        '-I' + str(ROOT / 'algorithmic/judge/include'),
                        str(ROOT / f'algorithmic/problems/{pid}/chk.cc'),
                        '-o', str(target)], check=True)
        result[pid] = target
    return result


def submission(pid, cost):
    if pid == 164:
        # Official n=200,m=10 dimensions; ascending removals are already possible.
        data = '200 10\n' + ''.join(' '.join(map(str, range(20*i+20, 20*i, -1)))+'\n'
                                        for i in range(10))
        moves, remainder = divmod(cost, 21)
        if remainder == 1:
            moves -= 1
            remainder += 21
        output = '20 1\n' * moves
        if remainder % 2:
            output += '2 1\n'  # moving the top two boxes costs 3
            remainder -= 3
        output += '1 1\n' * (remainder // 2)
        output += ''.join(f'{i} 0\n' for i in range(1, 201))
        return data, output
    # Alternate two adjacent keys: first key costs1, each subsequent key costs2.
    # A final repeated key adds1 when an even cost is requested.
    data = '2 1 0 0\nAB\nCD\nABABA\n'
    pairs = (cost-1)//2
    output = '0 0\n' + ''.join(f'0 {i%2}\n' for i in range(1, pairs+1))
    if cost % 2 == 0:
        output += f'0 {pairs%2}\n'
    return data, output


def points(binary, tmp_path, data, output, baseline, reference):
    inp, out, ans = [tmp_path / x for x in ('input', 'output', 'answer')]
    inp.write_text(data); out.write_text(output); ans.write_text(f'{baseline} {reference}\n')
    p = subprocess.run([str(binary), str(inp), str(out), str(ans)],
                       capture_output=True, text=True, timeout=15)
    assert p.returncode == 7, p.stderr
    return 100*float(re.search(r'Ratio:\s*([0-9.]+)', p.stderr)[1])


@pytest.mark.parametrize('pid,reference,anchor', [(164, 1, 9999), (165, 1001, 8999),
                                                (164, 9000, 1000), (165, 9000, 1000)])
def test_halving_actual_cost_adds_ln2(binaries, tmp_path, pid, reference, anchor):
    scores = [points(binaries[pid], tmp_path, *submission(pid, c), 0, reference)
              for c in (100, 200)]
    assert scores[0] == pytest.approx(60+math.log(anchor/100), abs=1e-9)
    assert scores[0]-scores[1] == pytest.approx(math.log(2), abs=1e-9)


@pytest.mark.parametrize('pid,cost,reference', [(164,9999,1),(164,10000,1),
                                              (165,8999,1001),(165,9000,1001)])
def test_old_sixty_point_plateau_stays_sixty(binaries, tmp_path, pid, cost, reference):
    assert points(binaries[pid], tmp_path, *submission(pid,cost),0,reference) == pytest.approx(60)


@pytest.mark.parametrize('pid', [164,165])
def test_positive_lower_band_is_preserved(binaries,tmp_path,pid):
    # cost200 => raw reward9800; reference9900 gives a below60 linear score.
    assert points(binaries[pid],tmp_path,*submission(pid,200),0,9900) == pytest.approx(60*9800/9900,abs=1e-9)


def test_incomplete_typing_keeps_coverage_score(binaries,tmp_path):
    data='2 2 0 0\nAB\nCD\nABABA\nCCCCC\n'
    output='0 0\n0 1\n0 0\n0 1\n0 0\n' # only one target string present
    assert points(binaries[165],tmp_path,data,output,0,1001) == pytest.approx(60*1000/1001,abs=1e-9)
