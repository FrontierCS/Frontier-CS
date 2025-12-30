#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    if (!(cin >> N)) return 0;
    vector<string> C(N);
    for (int i = 0; i < N; i++) cin >> C[i];

    vector<vector<int>> isFuku(N, vector<int>(N, 0));
    vector<pair<int,int>> onis;
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            if (C[i][j] == 'o') isFuku[i][j] = 1;
            else if (C[i][j] == 'x') onis.emplace_back(i, j);
        }
    }

    struct Move { char dir; int p; };
    vector<Move> ops;
    ops.reserve(4 * N * N);

    for (auto &oj : onis) {
        int i = oj.first;
        int j = oj.second;

        struct Cand { char dir; int d; };
        vector<Cand> cand;

        // Up
        bool ok = true;
        for (int r = 0; r < i; r++) {
            if (isFuku[r][j]) { ok = false; break; }
        }
        if (ok) cand.push_back({'U', i + 1});

        // Down
        ok = true;
        for (int r = i + 1; r < N; r++) {
            if (isFuku[r][j]) { ok = false; break; }
        }
        if (ok) cand.push_back({'D', N - i});

        // Left
        ok = true;
        for (int c = 0; c < j; c++) {
            if (isFuku[i][c]) { ok = false; break; }
        }
        if (ok) cand.push_back({'L', j + 1});

        // Right
        ok = true;
        for (int c = j + 1; c < N; c++) {
            if (isFuku[i][c]) { ok = false; break; }
        }
        if (ok) cand.push_back({'R', N - j});

        if (cand.empty()) continue; // should not happen with valid input

        Cand best = cand[0];
        for (auto &c : cand) if (c.d < best.d) best = c;

        char dir = best.dir;
        int d = best.d;

        if (dir == 'U') {
            for (int k = 0; k < d; k++) ops.push_back({'U', j});
            for (int k = 0; k < d; k++) ops.push_back({'D', j});
        } else if (dir == 'D') {
            for (int k = 0; k < d; k++) ops.push_back({'D', j});
            for (int k = 0; k < d; k++) ops.push_back({'U', j});
        } else if (dir == 'L') {
            for (int k = 0; k < d; k++) ops.push_back({'L', i});
            for (int k = 0; k < d; k++) ops.push_back({'R', i});
        } else { // 'R'
            for (int k = 0; k < d; k++) ops.push_back({'R', i});
            for (int k = 0; k < d; k++) ops.push_back({'L', i});
        }
    }

    int limit = 4 * N * N;
    if ((int)ops.size() > limit) {
        ops.resize(limit);
    }

    for (auto &m : ops) {
        cout << m.dir << ' ' << m.p << '\n';
    }

    return 0;
}