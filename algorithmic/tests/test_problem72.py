"""Compare packed-state BFS against an independent board-state search."""
import collections
import random
import subprocess
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope='module')
def solver(tmp_path_factory):
    directory = tmp_path_factory.mktemp('puzzle72')
    source = directory / 'test.cpp'
    source.write_text('#define main checker_main\n#include "' + str(ROOT / 'algorithmic/problems/72/chk.cc') + '"\n#undef main\nint main(){disableFinalizeGuard();int cases;std::cin>>cases;while(cases--){for(int i=1;i<=6;i++)for(int j=1;j<=6;j++)std::cin>>board[i][j];parseBoard();std::cout<<solvePuzzle()<<"\\n";}}\n')
    executable = directory / 'solve'
    subprocess.run(['g++', '-std=gnu++17', '-O2', '-I' + str(ROOT / 'algorithmic/judge/include'), str(source), '-o', str(executable)], check=True)
    return executable


def reference(board):
    initial = tuple(board)
    ids = sorted(set(board) - {0})
    horizontal = {i: (board.index(i) // 6 == (35 - board[::-1].index(i)) // 6) for i in ids}
    queue = collections.deque([(initial, 0)])
    seen = {initial}
    while queue:
        current, distance = queue.popleft()
        if current[17] == 1:return distance + 2
        for vehicle in ids:
            cells = [i for i, value in enumerate(current) if value == vehicle]
            for direction in [-1, 1]:
                delta = direction if horizontal[vehicle] else direction * 6
                moved = [i + delta for i in cells]
                if any(j < 0 or j >= 36 or (horizontal[vehicle] and i // 6 != j // 6) for i, j in zip(cells, moved)):continue
                if any(current[j] not in (0, vehicle) for j in moved):continue
                after = list(current)
                for i in cells:after[i] = 0
                for i in moved:after[i] = vehicle
                state = tuple(after)
                if state not in seen:seen.add(state);queue.append((state, distance + 1))
    return -1


def test_random_small_puzzles_match_independent_bfs(solver):
    rng = random.Random(72)
    cases = []
    for _ in range(80):
        board = [0] * 36
        pos = rng.randrange(5)
        board[12 + pos] = board[13 + pos] = 1
        vehicle = 2
        for _ in range(12):
            horizontal = rng.choice([False, True]);length = rng.choice([2, 3])
            row, col = rng.randrange(6), rng.randrange(6)
            if (col if horizontal else row) + length > 6:continue
            cells = [(row + (0 if horizontal else k)) * 6 + col + (k if horizontal else 0) for k in range(length)]
            if any(board[i] for i in cells):continue
            for i in cells:board[i] = vehicle
            vehicle += 1
            if vehicle == 5:break
        cases.append(board)
    data = str(len(cases)) + '\n' + '\n'.join(' '.join(map(str, b)) for b in cases) + '\n'
    result = subprocess.run([str(solver)], input=data, text=True, capture_output=True, timeout=30, check=True)
    assert list(map(int, result.stdout.split())) == [reference(board) for board in cases]
