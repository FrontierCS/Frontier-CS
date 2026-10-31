"""Preserve checker semantics while removing dense resource bottlenecks."""
from pathlib import Path
import random
import math
import re
import resource
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[2]
BASELINE = '65117c9909c1e460796e43521c80eb4bf86fbcd2'


@pytest.fixture(scope='module')
def binaries(tmp_path_factory):
    directory = tmp_path_factory.mktemp('checker36_239')
    result = {}
    for pid, name in [('36', 'interactor.cpp'), ('239', 'chk.cc')]:
        path = f'algorithmic/problems/{pid}/{name}'
        original = directory / (pid + '_old.cpp')
        original.write_bytes(subprocess.check_output(['git', 'show', f'{BASELINE}:{path}'], cwd=ROOT))
        for variant, source in [('old', original), ('new', ROOT / path)]:
            binary = directory / (pid + '_' + variant)
            subprocess.run(['g++', '-std=gnu++17', '-O2', '-I' + str(ROOT / 'algorithmic/judge/include'),
                            str(source), '-o', str(binary)], check=True)
            result[pid, variant] = binary
    return result


def run36(binary, directory, n, queries, memory_limit=None):
    inf, transcript = directory / 'in', directory / 'transcript'
    inf.write_text(str(n) + '\n')
    data = ''.join('0 ' + str(len(q)) + ' ' + ' '.join(map(str, q)) + '\n' for q in queries) + f'1 {n}\n'
    def limit():
        resource.setrlimit(resource.RLIMIT_AS, (memory_limit, memory_limit))
    return subprocess.run([str(binary), str(inf), str(transcript)], input=data, text=True,
                          capture_output=True, timeout=15, preexec_fn=limit if memory_limit else None)


def test_collision_counts_and_scores_match_original(binaries, tmp_path):
    rng = random.Random(36)
    for n in [1, 2, 17, 101, 1000]:
        queries = [[rng.randint(1, 10**18) for _ in range(rng.randint(1, 100))] for _ in range(20)]
        old = run36(binaries['36', 'old'], tmp_path, n, queries)
        new = run36(binaries['36', 'new'], tmp_path, n, queries)
        assert (new.returncode, new.stdout) == (old.returncode, old.stdout)
        total = sum(map(len, queries))
        expected = .6 + math.log(1000000/total)/100
        actual = float(re.search(r'Ratio:\s*([0-9.]+)', new.stderr)[1])
        assert actual == pytest.approx(expected, abs=1e-11)


def test_billion_modulus_and_maximum_query_fit_small_memory(binaries, tmp_path):
    result = run36(binaries['36', 'new'], tmp_path, 10**9, [[1] * 10**6], 128 * 1024**2)
    assert result.returncode == 7, result.stderr
    assert result.stdout.strip() == '499999500000'
    assert 'Correct guess in 1000000 queries.' in result.stderr


def run239(binary, directory, n, edges, reference=100, timeout=10):
    inf, out, ans = [directory / name for name in ('in', 'out', 'ans')]
    inf.write_text(str(n) + '\n')
    ans.write_text(str(reference) + '\n')
    out.write_text(str(len(edges)) + '\n' + ''.join(f'{a} {b} {c}\n' for a, b, c in edges))
    return subprocess.run([str(binary), str(inf), str(out), str(ans)], text=True,
                          capture_output=True, timeout=timeout)


def test_sparse_bfs_preserves_original_verdicts_and_scores(binaries, tmp_path):
    rng = random.Random(239)
    for _ in range(60):
        n = rng.randint(0, 30)
        graph = {(i, i + 1) for i in range(n)}
        edges = []
        for _ in range(rng.randint(0, 100)):
            pairs = [(a, b, c) for a, b in graph for c in range(b + 1, n + 1) if (b, c) in graph]
            if not pairs:break
            a, b, c = rng.choice(sorted(pairs))
            edges.append((a, b, c));graph.add((a, c))
        old = run239(binaries['239', 'old'], tmp_path, n, edges)
        new = run239(binaries['239', 'new'], tmp_path, n, edges)
        assert new.returncode == old.returncode
        if new.returncode == 7:
            cost = len(edges)
            normalized = max(0, (300-cost)/200)
            expected = 1 if cost == 0 else (.6*normalized if cost >= 100 else .6+math.log(100/cost)/100)
            actual = float(re.search(r'Ratio:\s*([0-9.]+)', new.stderr)[1])
            assert actual == pytest.approx(expected, abs=1e-11)
        else:
            assert new.stderr == old.stderr


def test_large_valid_construction_finishes(binaries, tmp_path):
    edges = []
    def build(left, right):
        if right - left <= 1:return
        mid = (left + right) // 2
        for i in range(mid - 2, left - 1, -1):edges.append((i, i + 1, mid))
        for j in range(mid + 2, right + 1):edges.append((mid, j - 1, j))
        build(left, mid);build(mid, right)
    build(0, 4096)
    # Duplicate additions count toward the score, but not adjacency traversal.
    edges += edges[:10]
    result = run239(binaries['239', 'new'], tmp_path, 4096, edges, reference=len(edges), timeout=10)
    assert result.returncode == 7, result.stderr
    assert 'Ratio: 0.600000000000' in result.stderr
