"""Each student's pair must come from a secret per-test seed, not from the round number (#212)."""
import hashlib
import math
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'algorithmic/problems/69/testdata'
TESTS = range(1, 11)
MASK64 = (1 << 64) - 1


class MT19937_64:
    """std::mt19937_64, written out from its definition in the C++ standard ([rand.eng.mers], [rand.predef])."""

    def __init__(self, seed):
        self.state = [seed & MASK64]
        for i in range(1, 312):
            prev = self.state[-1]
            self.state.append((6364136223846793005 * (prev ^ (prev >> 62)) + i) & MASK64)
        self.index = 312

    def __call__(self):
        if self.index == 312:
            mt = self.state
            for i in range(312):
                x = (mt[i] & 0xFFFFFFFF80000000) | (mt[(i + 1) % 312] & 0x7FFFFFFF)
                mt[i] = mt[(i + 156) % 312] ^ (x >> 1) ^ (0xB5026F5AA96619E9 if x & 1 else 0)
            self.index = 0
        y = self.state[self.index]
        self.index += 1
        y ^= (y >> 29) & 0x5555555555555555
        y ^= (y << 17) & 0x71D67FFFEDA60000
        y ^= (y << 37) & 0xFFF7EEE000000000
        y ^= y >> 43
        return y


@pytest.fixture(scope='module')
def interactor(tmp_path_factory):
    executable = tmp_path_factory.mktemp('problem69') / 'interactor'
    subprocess.run(['g++', '-std=gnu++17', '-O2', '-I' + str(ROOT / 'algorithmic/judge/include'),
                    str(ROOT / 'algorithmic/problems/69/interactor.cc'), '-o', str(executable)], check=True)
    return executable


def sizes(test):
    n, q = map(int, (DATA / f'{test}.in').read_text().split())
    return n, q


def reference_length(test):
    return int((DATA / f'{test}.ans').read_text().split()[0])


def seed(test):
    return int((DATA / f'{test}.ans').read_text().split()[1])


def student_pairs(test):
    """The pairs the statement promises: u then v, each uniform on [1, n], from the test's seed."""
    n, q = sizes(test)
    gen = MT19937_64(seed(test))
    usable = MASK64 // n * n

    def draw():
        while True:
            x = gen()
            if x < usable:
                return x % n + 1

    pairs = []
    for _ in range(q):
        u = draw()
        v = draw()
        pairs.append((u, v))
    return pairs


def formula_pairs(test):
    """The pairs the interactor used to ask: a function of the round number alone."""
    n, q = sizes(test)
    return [(j % n + 1, (j * 37 + 13) % n + 1) for j in range(q)]


def shortest_words(n):
    """X, O, XX, XO, ...: the n shortest distinct words, as in the issue. Many of their spells share a power."""
    words, length = [], 1
    while len(words) < n:
        words += [format(code, f'0{length}b').replace('0', 'X').replace('1', 'O') for code in range(2 ** length)]
        length += 1
    return words[:n]


def power(spell):
    return len({spell[i:j] for i in range(len(spell)) for j in range(i + 1, len(spell) + 1)})


def transcript(words, pairs):
    return ''.join(w + '\n' for w in words) + ''.join(f'{u} {v}\n' for u, v in pairs)


def play(interactor, tmp_path, test, contestant, ans=None):
    """Run the interactor on a test; the contestant's whole output is fed in at once (non-adaptive)."""
    ans_file = tmp_path / 'ans'
    ans_file.write_text((DATA / f'{test}.ans').read_text() if ans is None else ans)
    return subprocess.run([str(interactor), str(DATA / f'{test}.in'), str(tmp_path / 'transcript'), str(ans_file)],
                          input=contestant, text=True, capture_output=True, timeout=30)


def ratio(result):
    return float(re.search(r'Ratio: ([0-9.]+)', result.stderr).group(1))


def test_python_mt19937_64_matches_the_standard():
    # [rand.predef]: the 10000th consecutive call of a default-constructed (seed 5489) mt19937_64.
    gen = MT19937_64(5489)
    for _ in range(9999):
        gen()
    assert gen() == 9981545732273789042


def test_each_test_has_its_own_secret_seed():
    seeds = [seed(t) for t in TESTS]
    assert all(0 <= s < 2**63 for s in seeds), seeds
    assert len(set(seeds)) == len(seeds)
    for t in TESTS:
        assert re.fullmatch(r'[0-9]+\n[0-9]+\n', (DATA / f'{t}.ans').read_text())
        # The contestant only receives n and q.
        assert re.fullmatch(r'[0-9]+ [0-9]+\s*', (DATA / f'{t}.in').read_text())


# The program from #212 prints the shortest words and replays the old formula without reading a
# power. It used to be accepted on every test at 60 + ln(11683787 / 7996) = 67.29 points (test 1).
@pytest.mark.parametrize('test', TESTS)
def test_issue_replay_is_rejected(interactor, tmp_path, test):
    n, _ = sizes(test)
    result = play(interactor, tmp_path, test, transcript(shortest_words(n), formula_pairs(test)))
    assert result.returncode == 7, result.stderr
    assert result.stderr.startswith('points 0.0 wrong answer'), result.stderr
    assert 'wrong indices' in result.stderr and 'Ratio:' not in result.stderr


@pytest.mark.parametrize('test', TESTS)
def test_interactor_asks_the_seeded_pairs(interactor, tmp_path, test):
    n, q = sizes(test)
    words, pairs = shortest_words(n), student_pairs(test)
    runs = [play(interactor, tmp_path, test, transcript(words, pairs)) for _ in range(2)]
    for result in runs:
        assert result.returncode == 7, result.stderr
        replies = result.stdout.split()
        assert replies[:2] == [str(n), str(q)]
        assert replies[2:] == [str(power(words[u - 1] + words[v - 1])) for u, v in pairs]
        length = sum(map(len, words))
        assert f'All {q} answers valid. Total length = {length},' in result.stderr
        assert ratio(result) == pytest.approx((60 + math.log(reference_length(test) / length)) / 100, abs=1e-9)
    assert runs[0].stdout == runs[1].stdout and runs[0].stderr == runs[1].stderr


def test_pairs_do_not_depend_on_the_words(interactor, tmp_path):
    # The pairs are drawn before any word is read: other words get the same pairs.
    n, _ = sizes(4)
    words, pairs = shortest_words(n)[::-1], student_pairs(4)
    result = play(interactor, tmp_path, 4, transcript(words, pairs))
    assert result.returncode == 7 and 'All 1000 answers valid' in result.stderr, result.stderr
    assert result.stdout.split()[2:] == [str(power(words[u - 1] + words[v - 1])) for u, v in pairs]


def test_order_of_the_pair_matters(interactor, tmp_path):
    n, _ = sizes(2)
    pairs = student_pairs(2)
    j = next(j for j, (u, v) in enumerate(pairs) if u != v)
    pairs[j] = pairs[j][::-1]
    result = play(interactor, tmp_path, 2, transcript(shortest_words(n), pairs))
    assert result.returncode == 7 and result.stderr.startswith('points 0.0 '), result.stderr
    assert f' - Query {j + 1}: wrong indices' in result.stderr


# Pins the hidden pairs, so repeated judging gives the same results. Changing a seed or the
# drawing rule changes the pairs every submission is asked: update these only on purpose.
PAIRS_SHA256 = {1: '359fc6734b1234d5', 2: '8725d1d5a52c8e10', 3: '2c4638360c4a012a', 4: '930f74c638948f3b',
                5: '4f4c3b1c1566a423', 6: '29de03ab4d73f302', 7: '250e5c30600ef78f', 8: '8be6fa85c54451f7',
                9: 'ee015e3e8705d0e0', 10: '7768333d409738f1'}


def test_hidden_pairs_are_pinned():
    for t in TESTS:
        text = ''.join(f'{u} {v}\n' for u, v in student_pairs(t))
        assert hashlib.sha256(text.encode()).hexdigest()[:16] == PAIRS_SHA256[t], t


def test_pairs_are_spread_over_all_indices():
    sequences = {t: student_pairs(t) for t in TESTS}
    positions = []
    for t, pairs in sequences.items():
        n, q = sizes(t)
        assert len(pairs) == q and all(1 <= u <= n and 1 <= v <= n for u, v in pairs)
        assert pairs != formula_pairs(t)
        # q = 1000 uniform draws from n of about 1000 indices hit about 632 distinct ones.
        for side in (0, 1):
            assert 560 <= len({pair[side] for pair in pairs}) <= 700
            positions += [(pair[side] - 1) / (n - 1) for pair in pairs]
    # 20000 draws: the mean position is 0.5 with a standard deviation of about 0.002.
    assert abs(sum(positions) / len(positions) - 0.5) < 0.015
    assert len({tuple(pairs) for pairs in sequences.values()}) == len(sequences)


@pytest.mark.parametrize('test', [1, 10])
def test_secret_stays_out_of_the_output_and_the_log(interactor, tmp_path, test):
    n, q = sizes(test)
    words, secret, guessed = shortest_words(n), student_pairs(test), formula_pairs(test)
    accepted = play(interactor, tmp_path, test, transcript(words, secret))
    rejected = play(interactor, tmp_path, test, transcript(words, guessed))
    for result in (accepted, rejected):
        assert str(seed(test)) not in result.stdout + result.stderr
        assert result.stdout.split()[:2] == [str(n), str(q)]
    # A wrong answer names the contestant's pair, never the student's.
    j = next(j for j in range(q) if guessed[j] != secret[j])
    line = next(line for line in rejected.stderr.splitlines() if line.startswith(f' - Query {j + 1}:'))
    assert '(%d,%d)' % guessed[j] in line and '(%d,%d)' % secret[j] not in line


def test_missing_seed_is_a_judge_failure(interactor, tmp_path):
    n, _ = sizes(3)
    result = play(interactor, tmp_path, 3, transcript(shortest_words(n), formula_pairs(3)),
                  ans=f'{reference_length(3)}\n')
    assert result.returncode == 3, result.stderr
    assert result.stdout == ''
