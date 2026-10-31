"""Native regression: a missing positive physical anchor must not restore 2*ln."""
import math
from pathlib import Path
import re
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope='module')
def binaries(tmp_path_factory):
    directory = tmp_path_factory.mktemp('zero_anchor_ln')
    result = {}
    for pid in [163, 164, 167, 168]:
        target = directory / str(pid)
        subprocess.run(['g++', '-std=c++17', '-O2',
                        '-I' + str(ROOT / 'algorithmic/judge/include'),
                        str(ROOT / f'algorithmic/problems/{pid}/chk.cc'),
                        '-o', str(target)], check=True)
        result[pid] = target
    return result


CASES = [
    (163, '2 1\n1 1\n1 1\n', '1 0\n0 0\n', 4),
    (164, '2 2\n1\n2\n', '1 1\n1 0\n2 0\n', 9998),
    (167, '1\n100 100\n1000 1000\n',
     '4\n99 99\n101 99\n101 101\n99 101\n', 2),
    (168, '2 1 1\n1 1\n0 1\n0 0\n1 0\n', '-1 0\n', 4),
]


def run_checker(binary, tmp_path, data, output, baseline, reference):
    inp, out, ans = [tmp_path / name for name in ['input', 'output', 'answer']]
    inp.write_text(data)
    out.write_text(output)
    ans.write_text(f'{baseline} {reference}\n')
    result = subprocess.run([str(binary), str(inp), str(out), str(ans)],
                            capture_output=True, text=True, timeout=15)
    assert result.returncode == 7, result.stderr
    return float(re.search(r'Ratio:\s*([0-9.]+)', result.stderr)[1])


@pytest.mark.parametrize('pid,data,output,value', [case for case in CASES if case[0] != 164])
def test_zero_anchor_fallback_has_one_ln(binaries, tmp_path, pid, data, output, value):
    # R=1 gives a zero physical anchor. In 163/168, B=0 is an
    # accepted synthetic calibration rather than a realizable baseline reward.
    ratio = run_checker(binaries[pid], tmp_path, data, output, 0, 1)
    assert ratio == pytest.approx(.6 + math.log(value) / 100, abs=1e-11)
    assert ratio != pytest.approx(.6 + 2 * math.log(value) / 100, abs=1e-11)


@pytest.mark.parametrize('pid,data,output,value', CASES)
def test_lower_band_unchanged(binaries, tmp_path, pid, data, output, value):
    ratio = run_checker(binaries[pid], tmp_path, data, output, 0, 2 * value)
    assert ratio == pytest.approx(.3, abs=1e-11)


def test_valid_zero_energy_still_takes_priority(binaries, tmp_path):
    ratio = run_checker(binaries[164], tmp_path, '2 2\n1\n2\n',
                        '1 0\n2 0\n', 0, 1)
    assert ratio == 1
