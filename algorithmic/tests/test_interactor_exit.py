"""Early contestant exits must produce verdicts, not OOM or SIGPIPE."""
from pathlib import Path
import os
import resource
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope='module')
def interactors(tmp_path_factory):
    directory = tmp_path_factory.mktemp('exit_interactors')
    result = {}
    for pid, source in [('101', 'interactor.cpp'), ('217', 'interactor.cc'), ('243', 'interactor.cc')]:
        binary = directory / pid
        subprocess.run(['g++', '-std=gnu++17', '-O2', '-I' + str(ROOT / 'algorithmic/judge/include'),
                        str(ROOT / 'algorithmic/problems' / pid / source), '-o', str(binary)], check=True)
        result[pid] = binary
    return result


def run_interactor(binary, directory, data, answer, contestant, closed_output=False):
    inf, transcript, ans = [directory / name for name in ('in', 'transcript', 'ans')]
    inf.write_text(data);ans.write_text(answer)
    output = subprocess.PIPE
    if closed_output:
        read_fd, output = os.pipe()
        os.close(read_fd)
    def limit():
        resource.setrlimit(resource.RLIMIT_AS, (128 * 1024**2, 128 * 1024**2))
    try:
        return subprocess.run([str(binary), str(inf), str(transcript), str(ans)],
                              input=contestant, text=True, stdout=output, stderr=subprocess.PIPE,
                              timeout=5, preexec_fn=limit)
    finally:
        if closed_output:os.close(output)


@pytest.mark.parametrize('contestant', ['', '\n# comment\n\n', '! 1 2\n', '! 1 2', '# comment'])
def test_incomplete_sticks_stop_at_eof(interactors, tmp_path, contestant):
    result = run_interactor(interactors['217'], tmp_path, '2 2\n1 2 1 2\n', '20 4\n', contestant)
    assert result.returncode == 1, result.stderr
    assert 'Participant output ended after' in result.stderr


def test_complete_sticks_still_score(interactors, tmp_path):
    result = run_interactor(interactors['217'], tmp_path, '2 1\n1 2\n', '10 2\n', '! 1 2\n')
    assert result.returncode == 7, result.stderr
    assert 'Ratio:' in result.stderr


@pytest.mark.parametrize('pid,data,answer,contestant,verdict', [
    ('101', '1 0\n1 2\n&\n', '', '! &\n', 7),
    ('101', '1 0\n1 2\n&\n', '', '! |\n', 1),
    ('243', '1 1\n.\n1 1 0\n', 'yes 1\n', 'yes 1 1\n', 7),
])
def test_closed_contestant_pipe_preserves_verdict(interactors, tmp_path, pid, data, answer, contestant, verdict):
    result = run_interactor(interactors[pid], tmp_path, data, answer, contestant, closed_output=True)
    assert result.returncode == verdict, result.stderr


def test_long_query_transcript_does_not_accumulate_in_memory(interactors, tmp_path):
    # Each query is valid. Retaining testlib's int-per-character history would
    # exceed the 128 MiB limit, though no single line is large.
    contestant = ('? 0' + ' ' * 4096 + '\n') * 10000 + '! 1 2\n! 3 4\n'
    result = run_interactor(interactors['217'], tmp_path, '2 2\n1 2 1 2\n', '20 4\n', contestant)
    assert result.returncode == 7, result.stderr
    assert 'Queries: 10000' in result.stderr
