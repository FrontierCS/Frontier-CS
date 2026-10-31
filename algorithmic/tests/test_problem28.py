"""The answer must be the dictionary itself, not any n distinct words (#204)."""
import math
from pathlib import Path
import re
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'algorithmic/problems/28/testdata'


@pytest.fixture(scope='module')
def interactor(tmp_path_factory):
    executable = tmp_path_factory.mktemp('interactor28') / 'interactor'
    subprocess.run(['g++', '-std=gnu++17', '-O2', '-I' + str(ROOT / 'algorithmic/judge/include'),
                    str(ROOT / 'algorithmic/problems/28/interactor.cc'), '-o', str(executable)], check=True)
    return executable


def words(letter, count):
    # The interactor's list for a letter: the first `count` ten-letter words that start with it.
    return [letter + 'aaaaaa' + ''.join(chr(97 + j // 26**k % 26) for k in (2, 1, 0)) for j in range(count)]


def play(interactor, tmp_path, data, contestant):
    inf, transcript, ans = [tmp_path / name for name in ('in', 'transcript', 'ans')]
    inf.write_text(data);ans.write_text('0\n')
    return subprocess.run([str(interactor), str(inf), str(transcript), str(ans)],
                          input=contestant, text=True, capture_output=True, timeout=5)


def ratio(result):
    return float(re.search(r'Ratio: ([0-9.]+)', result.stderr).group(1))


# Two words start with 'a' and two with 'c'.
SMALL = '1\n4\n2 0 2' + ' 0' * 23 + '\n'
DICTIONARY = words('a', 2) + words('c', 2)


@pytest.mark.parametrize('answer', [
    ['a0', 'a1', 'a2', 'a3'],
    DICTIONARY[:3] + ['c'],
    DICTIONARY[:3] + ['Aaaaaaaaaa'],
    DICTIONARY[:3] + ['baaaaaaaaa'],
    DICTIONARY[:3] + ['aaaaaaaaac'],
])
def test_word_outside_the_dictionary_is_wrong(interactor, tmp_path, answer):
    result = play(interactor, tmp_path, SMALL, 'answer ' + ' '.join(answer) + '\n')
    assert result.returncode == 1, result.stderr
    assert 'Invalid answer' in result.stderr


def test_repeated_word_is_wrong(interactor, tmp_path):
    answer = [DICTIONARY[0]] + DICTIONARY[:3]
    result = play(interactor, tmp_path, SMALL, 'answer ' + ' '.join(answer) + '\n')
    assert result.returncode == 1, result.stderr
    assert 'Repeated answer' in result.stderr


# The first character used to index s[] and num[] unchecked; only '{' to '~'
# landed in the four spare rows.
@pytest.mark.parametrize('prefix', ['A', '0a', '\x7f', '{'])
def test_prefix_without_a_leading_letter_matches_nothing(interactor, tmp_path, prefix):
    result = play(interactor, tmp_path, SMALL, 'query %s 1\nanswer %s\n' % (prefix, ' '.join(DICTIONARY)))
    assert result.returncode == 7, result.stderr
    assert result.stdout.split()[2:] == ['0']
    assert ratio(result) == pytest.approx((60 + math.log(2400)) / 100, abs=1e-9)


def test_dictionary_in_any_order_scores(interactor, tmp_path):
    result = play(interactor, tmp_path, SMALL, 'query a 2\nquery c 2\nanswer ' + ' '.join(DICTIONARY[::-1]) + '\n')
    assert result.returncode == 7, result.stderr
    assert result.stdout.split()[2:] == ['2'] + DICTIONARY[:2] + ['2'] + DICTIONARY[2:]
    assert ratio(result) == pytest.approx((60 + math.log(2400 / 4)) / 100, abs=1e-9)


@pytest.mark.parametrize('test', range(1, 11))
def test_full_dictionary_of_each_test_is_accepted(interactor, tmp_path, test):
    data = (DATA / ('%d.in' % test)).read_text()
    counts = list(map(int, data.split()[2:28]))
    answer = [w for i, count in enumerate(counts) for w in words(chr(97 + i), count)]
    result = play(interactor, tmp_path, data, 'answer ' + ' '.join(answer) + '\n')
    assert result.returncode == 7, result.stderr
    assert ratio(result) == 1
