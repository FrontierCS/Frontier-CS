#include <bits/stdc++.h>
using namespace std;

struct Move {
    char d;
    int p;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    cin >> N;
    vector<string> g(N);
    for (int i = 0; i < N; i++) cin >> g[i];

    vector<Move> ops;
    auto addMoves = [&](char d, int p, int t) {
        ops.reserve(ops.size() + t);
        for (int i = 0; i < t; i++) ops.push_back({d, p});
    };

    auto existsX = [&]() -> bool {
        for (int i = 0; i < N; i++)
            for (int j = 0; j < N; j++)
                if (g[i][j] == 'x') return true;
        return false;
    };

    auto safeUp = [&](int i, int j) -> bool {
        for (int r = 0; r < i; r++) if (g[r][j] == 'o') return false;
        return true;
    };
    auto safeDown = [&](int i, int j) -> bool {
        for (int r = i + 1; r < N; r++) if (g[r][j] == 'o') return false;
        return true;
    };
    auto safeLeft = [&](int i, int j) -> bool {
        for (int c = 0; c < j; c++) if (g[i][c] == 'o') return false;
        return true;
    };
    auto safeRight = [&](int i, int j) -> bool {
        for (int c = j + 1; c < N; c++) if (g[i][c] == 'o') return false;
        return true;
    };

    auto countXUp = [&](int i, int j) -> int {
        int cnt = 0;
        for (int r = 0; r <= i; r++) cnt += (g[r][j] == 'x');
        return cnt;
    };
    auto countXDown = [&](int i, int j) -> int {
        int cnt = 0;
        for (int r = i; r < N; r++) cnt += (g[r][j] == 'x');
        return cnt;
    };
    auto countXLeft = [&](int i, int j) -> int {
        int cnt = 0;
        for (int c = 0; c <= j; c++) cnt += (g[i][c] == 'x');
        return cnt;
    };
    auto countXRight = [&](int i, int j) -> int {
        int cnt = 0;
        for (int c = j; c < N; c++) cnt += (g[i][c] == 'x');
        return cnt;
    };

    struct Action {
        bool ok = false;
        char dir = '?'; // 'U','D','L','R' net direction
        int i = -1, j = -1;
        int k = 0;      // shift count one-way
        int idx = 0;    // row/col index
        int cost = 0;
        int removedX = 0;
        long long score = LLONG_MIN;
    };

    auto applyAction = [&](const Action& a) {
        if (!a.ok) return;
        if (a.dir == 'U') {
            addMoves('U', a.idx, a.k);
            addMoves('D', a.idx, a.k);
            for (int r = 0; r <= a.i; r++) g[r][a.j] = '.';
        } else if (a.dir == 'D') {
            addMoves('D', a.idx, a.k);
            addMoves('U', a.idx, a.k);
            for (int r = a.i; r < N; r++) g[r][a.j] = '.';
        } else if (a.dir == 'L') {
            addMoves('L', a.idx, a.k);
            addMoves('R', a.idx, a.k);
            for (int c = 0; c <= a.j; c++) g[a.i][c] = '.';
        } else if (a.dir == 'R') {
            addMoves('R', a.idx, a.k);
            addMoves('L', a.idx, a.k);
            for (int c = a.j; c < N; c++) g[a.i][c] = '.';
        }
    };

    const int LIMIT = 4 * N * N; // 1600
    while (existsX()) {
        Action best;
        for (int i = 0; i < N; i++) for (int j = 0; j < N; j++) if (g[i][j] == 'x') {
            // U
            if (safeUp(i, j)) {
                Action a;
                a.ok = true; a.dir = 'U'; a.i = i; a.j = j;
                a.k = i + 1; a.idx = j;
                a.cost = 2 * a.k;
                a.removedX = countXUp(i, j);
                a.score = (long long)a.removedX * 1000 - a.cost;
                if (!best.ok || a.score > best.score || (a.score == best.score && a.cost < best.cost)) best = a;
            }
            // D
            if (safeDown(i, j)) {
                Action a;
                a.ok = true; a.dir = 'D'; a.i = i; a.j = j;
                a.k = N - i; a.idx = j;
                a.cost = 2 * a.k;
                a.removedX = countXDown(i, j);
                a.score = (long long)a.removedX * 1000 - a.cost;
                if (!best.ok || a.score > best.score || (a.score == best.score && a.cost < best.cost)) best = a;
            }
            // L
            if (safeLeft(i, j)) {
                Action a;
                a.ok = true; a.dir = 'L'; a.i = i; a.j = j;
                a.k = j + 1; a.idx = i;
                a.cost = 2 * a.k;
                a.removedX = countXLeft(i, j);
                a.score = (long long)a.removedX * 1000 - a.cost;
                if (!best.ok || a.score > best.score || (a.score == best.score && a.cost < best.cost)) best = a;
            }
            // R
            if (safeRight(i, j)) {
                Action a;
                a.ok = true; a.dir = 'R'; a.i = i; a.j = j;
                a.k = N - j; a.idx = i;
                a.cost = 2 * a.k;
                a.removedX = countXRight(i, j);
                a.score = (long long)a.removedX * 1000 - a.cost;
                if (!best.ok || a.score > best.score || (a.score == best.score && a.cost < best.cost)) best = a;
            }
        }

        if (!best.ok) break;

        if ((int)ops.size() + best.cost > LIMIT) break; // safety
        applyAction(best);
    }

    if ((int)ops.size() > LIMIT) ops.resize(LIMIT);
    for (auto &m : ops) {
        cout << m.d << ' ' << m.p << "\n";
    }
    return 0;
}