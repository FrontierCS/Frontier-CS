"""Each round's pair must come from a secret per-test seed, not from the round number."""
import hashlib
import math
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'algorithmic/problems/69/testdata'
TESTS = range(1, 11)

# Knows the seed (argv[1]) and prints the q (argv[3]) pairs that the interactor draws for n (argv[2]).
ORACLE = r'''
#include <bits/stdc++.h>
int main(int argc, char** argv) {
    std::mt19937_64 gen(std::strtoull(argv[1], nullptr, 10));
    const unsigned long long n = std::strtoull(argv[2], nullptr, 10);
    const int q = std::atoi(argv[3]);
    const unsigned long long limit = ULLONG_MAX - ULLONG_MAX % n;
    auto draw = [&]() {
        unsigned long long x = gen();
        while (x >= limit) x = gen();
        return x % n + 1;
    };
    for (int j = 0; j < q; j++) {
        unsigned long long u = draw();
        unsigned long long v = draw();
        std::printf("%llu %llu\n", u, v);
    }
}
'''


def build(directory, name, source=None):
    executable = directory / name
    if source is None:
        source = ROOT / 'algorithmic/problems/69/interactor.cc'
    else:
        (directory / (name + '.cpp')).write_text(source)
        source = directory / (name + '.cpp')
    subprocess.run(['g++', '-std=gnu++17', '-O2', '-I' + str(ROOT / 'algorithmic/judge/include'),
                    str(source), '-o', str(executable)], check=True)
    return executable


@pytest.fixture(scope='module')
def programs(tmp_path_factory):
    directory = tmp_path_factory.mktemp('problem69')
    return {'interactor': build(directory, 'interactor'), 'oracle': build(directory, 'oracle', ORACLE)}


def sizes(test):
    n, q = map(int, (DATA / f'{test}.in').read_text().split())
    return n, q


def reference_length(test):
    return int((DATA / f'{test}.ans').read_text().split()[0])


def seed(test):
    return (DATA / f'{test}.ans').read_text().split()[1]


def shortest_words(n):
    """X, O, XX, XO, ...: the n shortest distinct words. Many of their spells share a power."""
    words, length = [], 1
    while len(words) < n:
        for code in range(2 ** length):
            words.append(format(code, f'0{length}b').replace('0', 'X').replace('1', 'O'))
        length += 1
    return words[:n]


def formula_pairs(n, q):
    """The pairs the interactor used to ask: a function of the round number alone."""
    return [(j % n + 1, (j * 37 + 13) % n + 1) for j in range(q)]


def seeded_pairs(programs, test):
    n, q = sizes(test)
    out = subprocess.run([str(programs['oracle']), seed(test), str(n), str(q)], text=True,
                         capture_output=True, check=True, timeout=5).stdout
    return [tuple(map(int, line.split())) for line in out.splitlines()]


def transcript(words, pairs):
    return '\n'.join(words) + '\n' + ''.join(f'{u} {v}\n' for u, v in pairs)


def power(spell):
    return len({spell[i:j] for i in range(len(spell)) for j in range(i + 1, len(spell) + 1)})


def play(programs, tmp_path, test, contestant, ans=None):
    """Run the interactor on a test; the contestant's whole output is fed in at once."""
    ans_file = tmp_path / 'ans'
    ans_file.write_text((DATA / f'{test}.ans').read_text() if ans is None else ans)
    return subprocess.run([str(programs['interactor']), str(DATA / f'{test}.in'),
                           str(tmp_path / 'transcript'), str(ans_file)],
                          input=contestant, text=True, capture_output=True, timeout=30)


def ratio(result):
    return float(re.search(r'Ratio: ([0-9.]+)', result.stderr).group(1))


def test_each_test_has_its_own_secret_seed():
    seeds = [seed(t) for t in TESTS]
    assert all(re.fullmatch(r'[0-9]+', s) and int(s) < 2**63 for s in seeds), seeds
    assert len(set(seeds)) == len(seeds)
    # The contestant only receives n and q.
    for t in TESTS:
        assert re.fullmatch(r'[0-9]+ [0-9]+\s*', (DATA / f'{t}.in').read_text())


# This transcript does not depend on any power. With the old pairs it was accepted on every
# test. On test 1 its words total 7996 letters against a reference of 11683787, which earned
# 60 + ln(11683787 / 7996) = 67.29 points.
@pytest.mark.parametrize('test', TESTS)
def test_pairs_computed_from_the_round_number_are_rejected(programs, tmp_path, test):
    n, q = sizes(test)
    result = play(programs, tmp_path, test, transcript(shortest_words(n), formula_pairs(n, q)))
    assert result.returncode == 7, result.stderr
    assert 'wrong indices' in result.stderr
    # quitp(0.0) without a Ratio field: the judge engine scores the case 0.
    assert result.stderr.startswith('points 0.0 ') and 'Ratio:' not in result.stderr


@pytest.mark.parametrize('test', TESTS)
def test_seeded_pairs_are_asked_and_accepted(programs, tmp_path, test):
    n, q = sizes(test)
    words, pairs = shortest_words(n), seeded_pairs(programs, test)
    runs = [play(programs, tmp_path, test, transcript(words, pairs)) for _ in range(2)]
    for result in runs:
        assert result.returncode == 7, result.stderr
        replies = result.stdout.split()
        assert replies[:2] == [str(n), str(q)]
        assert replies[2:] == [str(power(words[u - 1] + words[v - 1])) for u, v in pairs]
        length = sum(map(len, words))
        assert f'All {q} answers valid. Total length = {length},' in result.stderr
        points = 60 + math.log(reference_length(test) / length)
        assert ratio(result) == pytest.approx(points / 100, abs=1e-9)
    assert runs[0].stdout == runs[1].stdout and runs[0].stderr == runs[1].stderr


def test_order_of_the_pair_still_matters(programs, tmp_path):
    n, q = sizes(1)
    pairs = seeded_pairs(programs, 1)
    j = next(j for j, (u, v) in enumerate(pairs) if u != v)
    pairs[j] = pairs[j][::-1]
    result = play(programs, tmp_path, 1, transcript(shortest_words(n), pairs))
    assert result.returncode == 7 and 'Ratio:' not in result.stderr, result.stderr
    assert f'Query {j + 1}: wrong indices' in result.stderr


# Pins the hidden pairs, so repeated judging gives the same results. Changing a seed or the
# drawing rule changes which pairs every submission is asked: update these only on purpose.
PAIRS_SHA256 = {1: '8559c738a6012b76', 2: '5ac1755709d5a20e', 3: 'a5e46d05f572a007', 4: '2f8b568e91c1517a',
                5: 'b5be729b0f53db70', 6: '1913751d5efbcd72', 7: 'd35004d11ce4796f', 8: 'dfdb2d0d9ce271aa',
                9: '742324df82b2df4d', 10: 'c18e8101996dc723'}


def test_hidden_pairs_are_pinned(programs):
    for t in TESTS:
        text = ''.join(f'{u} {v}\n' for u, v in seeded_pairs(programs, t))
        assert hashlib.sha256(text.encode()).hexdigest()[:16] == PAIRS_SHA256[t], t


def test_pairs_are_spread_over_all_indices(programs):
    sequences = [seeded_pairs(programs, t) for t in TESTS]
    for t, pairs in zip(TESTS, sequences):
        n, q = sizes(t)
        assert len(pairs) == q and all(1 <= u <= n and 1 <= v <= n for u, v in pairs)
        # 1000 uniform draws from about 1000 indices hit 632 distinct ones on average.
        assert 550 <= len({u for u, _ in pairs}) <= 700
        assert 550 <= len({v for _, v in pairs}) <= 700
        assert pairs != formula_pairs(n, q)
    assert len({tuple(pairs) for pairs in sequences}) == len(sequences)


@pytest.mark.parametrize('test', [1, 10])
def test_seed_and_pairs_stay_out_of_the_output(programs, tmp_path, test):
    n, q = sizes(test)
    words, secret, guessed = shortest_words(n), seeded_pairs(programs, test), formula_pairs(n, q)
    accepted = play(programs, tmp_path, test, transcript(words, secret))
    rejected = play(programs, tmp_path, test, transcript(words, guessed))
    for result in (accepted, rejected):
        assert seed(test) not in result.stdout + result.stderr
        assert result.stdout.split()[:2] == [str(n), str(q)]
    # A wrong answer is reported without naming the pair that was asked.
    j = next(j for j in range(q) if guessed[j] != secret[j])
    line = next(line for line in rejected.stderr.splitlines() if line.startswith(f' - Query {j + 1}:'))
    assert '(%d,%d)' % guessed[j] in line and '(%d,%d)' % secret[j] not in line


def test_missing_seed_is_a_judge_failure(programs, tmp_path):
    n, q = sizes(3)
    result = play(programs, tmp_path, 3, transcript(shortest_words(n), formula_pairs(n, q)),
                  ans=f'{reference_length(3)}\n')
    assert result.returncode == 3, result.stderr
    assert result.stdout == ''
