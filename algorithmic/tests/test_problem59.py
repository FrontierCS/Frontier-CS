"""The hidden array must come from a secret per-test seed, not testlib's fixed default (#208)."""
import hashlib
import math
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'algorithmic/problems/59/testdata'
TESTS = range(1, 11)

# The reproduction from #208: replay testlib's default-seeded rnd and answer with zero queries.
EXPLOIT = r'''
#include <bits/stdc++.h>
using namespace std;
struct Rnd {
    unsigned long long seed = 3905348978240129619ULL;
    static const unsigned long long MUL = 0x5DEECE66DULL, ADD = 0xBULL, MASK = (1ULL<<48)-1;
    static const long long LLMAX = 9223372036854775807LL;
    long long nextBits(int bits){
        if (bits <= 48){ seed=(seed*MUL+ADD)&MASK; return (long long)(seed>>(48-bits)); }
        long long left = nextBits(31) << 32;
        long long right = nextBits(32);
        return left ^ right;
    }
    long long next(long long n){
        const long long limit = LLMAX / n * n;
        long long bits; do{ bits=nextBits(63); }while(bits>=limit);
        return bits % n;
    }
    int next(int from,int to){ return (int)(next((long long)to - from + 1) + from); }
} rnd;
int main(){
    int n; if(!(cin>>n)) return 0;
    vector<int> a(n); iota(a.begin(),a.end(),1);
    for(int i=0;i<n;i++){ int j=rnd.next(i,min(n-1,i+2)); swap(a[i],a[j]); }
    cout<<"!"; for(int v:a) cout<<' '<<v; cout<<endl;
    return 0;
}
'''

# Knows the seed (passed as argv[1]) and rebuilds the array the statement describes.
ORACLE = r'''
#include <bits/stdc++.h>
int main(int argc, char** argv) {
    std::mt19937_64 gen(std::strtoull(argv[1], nullptr, 10));
    int n; if (std::scanf("%d", &n) != 1) return 1;
    std::vector<int> a(n); std::iota(a.begin(), a.end(), 1);
    for (int i = 0; i < n; i++) {
        int r = std::min(n - 1, i + 2);
        std::swap(a[i], a[i + (int)(gen() % (unsigned long long)(r - i + 1))]);
    }
    std::printf("!"); for (int v : a) std::printf(" %d", v); std::printf("\n");
}
'''


def build(directory, name, source=None):
    executable = directory / name
    if source is None:
        source = ROOT / 'algorithmic/problems/59/interactor.cpp'
    else:
        (directory / (name + '.cpp')).write_text(source)
        source = directory / (name + '.cpp')
    subprocess.run(['g++', '-std=gnu++17', '-O2', '-I' + str(ROOT / 'algorithmic/judge/include'),
                    str(source), '-o', str(executable)], check=True)
    return executable


@pytest.fixture(scope='module')
def programs(tmp_path_factory):
    directory = tmp_path_factory.mktemp('problem59')
    return {'interactor': build(directory, 'interactor'),
            'exploit': build(directory, 'exploit', EXPLOIT),
            'oracle': build(directory, 'oracle', ORACLE)}


def seed(test):
    return (DATA / f'{test}.ans').read_text().strip()


def answer(programs, name, test):
    """Output of a zero-query contestant that only reads n."""
    args = [str(programs[name])] + ([seed(test)] if name == 'oracle' else [])
    return subprocess.run(args, input=(DATA / f'{test}.in').read_text(), text=True,
                          capture_output=True, check=True, timeout=5).stdout


def play(programs, tmp_path, test, contestant, ans=None):
    """Run the interactor on a test; the contestant's whole output is fed in at once (non-adaptive)."""
    ans_file = tmp_path / 'ans'
    ans_file.write_text(seed(test) + '\n' if ans is None else ans)
    return subprocess.run([str(programs['interactor']), str(DATA / f'{test}.in'),
                           str(tmp_path / 'transcript'), str(ans_file)],
                          input=contestant, text=True, capture_output=True, timeout=10)


def ratio(result):
    return float(re.search(r'Ratio: ([0-9.]+)', result.stderr).group(1))


def test_each_test_has_its_own_secret_seed():
    seeds = [seed(t) for t in TESTS]
    assert all(re.fullmatch(r'[0-9]+', s) and int(s) < 2**63 for s in seeds), seeds
    assert len(set(seeds)) == len(seeds)
    # The contestant only receives the .in file, which must hold n alone.
    for t in TESTS:
        assert re.fullmatch(r'[0-9]+\s*', (DATA / f'{t}.in').read_text())


# Test 1 has n = 1, where the only array is (1) and zero queries is the honest answer.
@pytest.mark.parametrize('test', [t for t in TESTS if t != 1])
def test_issue_replay_is_rejected(programs, tmp_path, test):
    result = play(programs, tmp_path, test, answer(programs, 'exploit', test))
    assert result.returncode == 1, result.stderr
    assert 'Wrong final array' in result.stderr


@pytest.mark.parametrize('test', TESTS)
def test_array_is_fixed_by_the_seed(programs, tmp_path, test):
    final = answer(programs, 'oracle', test)
    values = list(map(int, final.split()[1:]))
    n = len(values)
    queries = ''.join(f'? {i} {i + 1}\n' for i in range(1, n))
    runs = [play(programs, tmp_path, test, queries + final) for _ in range(2)]
    for result in runs:
        assert result.returncode == 7, result.stderr
        replies = result.stdout.split()
        assert replies[0] == str(n)
        assert replies[1:] == ['<' if values[i] < values[i + 1] else '>' for i in range(n - 1)]
        points = 100 if n == 1 else 60 + math.log((n * 5 // 3 + 5) / (n - 1))
        assert ratio(result) == pytest.approx(points / 100, abs=1e-9)
    assert runs[0].stdout == runs[1].stdout and runs[0].stderr == runs[1].stderr


# Pins the hidden arrays, so repeated judging gives the same results. Changing a seed or
# the generator changes every score on this problem: update these only on purpose.
ARRAY_SHA256 = {1: '6929651cfa7ef638', 2: 'a0b0f48de997418c', 3: 'fd7599aa0e2a0bd9', 4: '65441a99d14bfa66',
                5: 'b4c7de6f59255de7', 6: 'e46573c8eba814ab', 7: 'ff7a1f66caa0e364', 8: '295e91118a0bc8b9',
                9: 'f453f2cd086e9164', 10: '93cab73c969610ac'}


def test_hidden_arrays_are_pinned(programs, tmp_path):
    for t in TESTS:
        assert hashlib.sha256(answer(programs, 'oracle', t).encode()).hexdigest()[:16] == ARRAY_SHA256[t], t
    result = play(programs, tmp_path, 2, '! 1 2 4 5 6 3 9 10 7 8\n')
    assert result.returncode == 7 and ratio(result) == 1.0, result.stderr


def test_tests_with_equal_n_get_different_arrays(programs):
    by_n = {}
    for t in TESTS:
        by_n.setdefault((DATA / f'{t}.in').read_text().strip(), []).append(answer(programs, 'oracle', t))
    assert len(by_n['30000']) == 8
    for arrays in by_n.values():
        assert len(set(arrays)) == len(arrays)


@pytest.mark.parametrize('test', [2, 3])
def test_seed_never_reaches_the_contestant_or_the_log(programs, tmp_path, test):
    for contestant in (answer(programs, 'oracle', test), answer(programs, 'exploit', test)):
        result = play(programs, tmp_path, test, contestant)
        assert seed(test) not in result.stdout + result.stderr
        assert result.stdout.split() == [(DATA / f'{test}.in').read_text().strip()]


def test_missing_seed_is_a_judge_failure(programs, tmp_path):
    result = play(programs, tmp_path, 3, answer(programs, 'exploit', 3), ans='')
    assert result.returncode == 3, result.stderr
    assert result.stdout == ''
