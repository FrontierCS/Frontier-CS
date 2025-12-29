#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    cin >> N;
    vector<vector<long long>> h(N, vector<long long>(N));
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) cin >> h[i][j];
    }

    vector<string> ops;
    int cr = 0, cc = 0;
    long long load = 0;

    auto addOp = [&](const string& s) { ops.push_back(s); };

    auto moveTo = [&](int tr, int tc) {
        while (cr < tr) { addOp("D"); cr++; }
        while (cr > tr) { addOp("U"); cr--; }
        while (cc < tc) { addOp("R"); cc++; }
        while (cc > tc) { addOp("L"); cc--; }
    };

    vector<pair<int,int>> path;
    path.reserve(N * N);
    for (int i = 0; i < N; i++) {
        if (i % 2 == 0) {
            for (int j = 0; j < N; j++) path.push_back({i, j});
        } else {
            for (int j = N - 1; j >= 0; j--) path.push_back({i, j});
        }
    }

    // Phase 1: collect all positive soil
    for (auto [r, c] : path) {
        moveTo(r, c);
        if (h[r][c] > 0) {
            long long d = h[r][c];
            addOp("+" + to_string(d));
            load += d;
            h[r][c] = 0;
        }
    }

    // Return to (0,0)
    moveTo(0, 0);

    // Phase 2: distribute to all negative cells
    for (auto [r, c] : path) {
        moveTo(r, c);
        if (h[r][c] < 0) {
            long long d = -h[r][c];
            if (d > 0) {
                addOp("-" + to_string(d));
                load -= d;
                h[r][c] = 0;
            }
        }
    }

    // Output operations
    for (auto &s : ops) cout << s << "\n";
    return 0;
}