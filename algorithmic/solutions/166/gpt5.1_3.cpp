#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    if (!(cin >> N)) return 0;
    vector<vector<int>> h(N, vector<int>(N));
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) cin >> h[i][j];
    }

    vector<pair<int,int>> posCells, negCells;
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            if (i == 0 && j == 0) continue;
            if (h[i][j] > 0) posCells.emplace_back(i, j);
            else if (h[i][j] < 0) negCells.emplace_back(i, j);
        }
    }

    vector<string> ops;
    int ci = 0, cj = 0;      // current position
    long long load = 0;      // current load on truck
    vector<vector<int>> hcur = h;

    auto go = [&](int ni, int nj) {
        while (ci < ni) { ops.emplace_back("D"); ++ci; }
        while (ci > ni) { ops.emplace_back("U"); --ci; }
        while (cj < nj) { ops.emplace_back("R"); ++cj; }
        while (cj > nj) { ops.emplace_back("L"); --cj; }
    };

    // Stage 1: move all positive soil (excluding (0,0)) to (0,0)
    for (auto [i, j] : posCells) {
        if (hcur[i][j] <= 0) continue; // safety
        go(i, j);
        int d = hcur[i][j];
        if (d > 0) {
            ops.emplace_back("+" + to_string(d));
            load += d;
            hcur[i][j] -= d; // becomes 0
            go(0, 0);
            ops.emplace_back("-" + to_string(d));
            load -= d;
            hcur[0][0] += d;
        }
    }

    // Stage 2: distribute soil from (0,0) to all negative cells
    for (auto [i, j] : negCells) {
        if (hcur[i][j] >= 0) continue; // safety
        int d = -hcur[i][j];
        if (d <= 0) continue;
        go(0, 0);
        ops.emplace_back("+" + to_string(d));
        load += d;
        hcur[0][0] -= d;
        go(i, j);
        ops.emplace_back("-" + to_string(d));
        load -= d;
        hcur[i][j] += d; // becomes 0
        go(0, 0);
    }

    // Output operations (one per line, no T)
    for (const string &s : ops) {
        cout << s << '\n';
    }

    return 0;
}