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

    vector<pair<int,int>> order;
    order.reserve(N * N);
    for (int i = 0; i < N; i++) {
        if (i % 2 == 0) {
            for (int j = 0; j < N; j++) order.push_back({i, j});
        } else {
            for (int j = N - 1; j >= 0; j--) order.push_back({i, j});
        }
    }

    vector<string> ops;
    ops.reserve(50000);

    int cr = 0, cc = 0;
    long long load = 0;

    auto moveTo = [&](int tr, int tc) {
        while (cr < tr) { ops.push_back("D"); cr++; }
        while (cr > tr) { ops.push_back("U"); cr--; }
        while (cc < tc) { ops.push_back("R"); cc++; }
        while (cc > tc) { ops.push_back("L"); cc--; }
    };

    // Phase 1: collect all positive soil
    for (auto [r, c] : order) {
        moveTo(r, c);
        if (h[r][c] > 0) {
            long long d = h[r][c];
            ops.push_back("+" + to_string(d));
            load += d;
            h[r][c] = 0;
        }
    }

    // Phase 2: fill all negative cells (reverse traversal)
    for (int idx = (int)order.size() - 1; idx >= 0; idx--) {
        auto [r, c] = order[idx];
        moveTo(r, c);
        if (h[r][c] < 0) {
            long long d = -h[r][c];
            if (d > load) d = load; // should not happen, but keep output legal
            if (d > 0) {
                ops.push_back("-" + to_string(d));
                load -= d;
                h[r][c] += d;
            }
        }
    }

    // If any residual load remains (shouldn't), unload at (0,0)
    moveTo(0, 0);
    if (load > 0) {
        ops.push_back("-" + to_string(load));
        load = 0;
    }

    for (auto &s : ops) cout << s << "\n";
    return 0;
}