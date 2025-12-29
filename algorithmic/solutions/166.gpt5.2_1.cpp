#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    cin >> N;
    vector<vector<long long>> h(N, vector<long long>(N));
    for (int i = 0; i < N; i++) for (int j = 0; j < N; j++) cin >> h[i][j];

    vector<pair<int,int>> path;
    path.reserve(N * N);
    for (int i = 0; i < N; i++) {
        if (i % 2 == 0) {
            for (int j = 0; j < N; j++) path.push_back({i, j});
        } else {
            for (int j = N - 1; j >= 0; j--) path.push_back({i, j});
        }
    }

    vector<string> ops;
    ops.reserve(5000);

    auto move_adj = [&](pair<int,int> cur, pair<int,int> nxt) {
        int dx = nxt.first - cur.first;
        int dy = nxt.second - cur.second;
        if (dx == 1 && dy == 0) ops.push_back("D");
        else if (dx == -1 && dy == 0) ops.push_back("U");
        else if (dx == 0 && dy == 1) ops.push_back("R");
        else if (dx == 0 && dy == -1) ops.push_back("L");
        else {
            // should not happen
            // fallback: do nothing
        }
    };

    pair<int,int> cur = path[0];
    long long load = 0;

    // Phase 1: collect from positive cells
    for (int idx = 0; idx < (int)path.size(); idx++) {
        if (idx > 0) {
            move_adj(cur, path[idx]);
            cur = path[idx];
        }
        auto [x, y] = cur;
        if (h[x][y] > 0) {
            long long d = h[x][y];
            ops.push_back("+" + to_string(d));
            load += d;
            h[x][y] = 0;
        }
    }

    // Phase 2: deliver to negative cells by traversing back
    for (int idx = (int)path.size() - 1; idx >= 0; idx--) {
        if (idx < (int)path.size() - 1) {
            move_adj(cur, path[idx]);
            cur = path[idx];
        }
        auto [x, y] = cur;
        if (h[x][y] < 0) {
            long long d = -h[x][y];
            if (d > 0) {
                if (load < d) {
                    // Should not happen if sums are consistent; guard to avoid illegal output.
                    // In this unlikely case, skip (will incur diff, but keep legality).
                    // Alternatively could stop, but judge would treat as illegal if unload exceeds load.
                    // We'll try to unload only what we have.
                    d = load;
                }
                if (d > 0) {
                    ops.push_back("-" + to_string(d));
                    load -= d;
                    h[x][y] += d;
                }
            }
        }
    }

    // Output operations
    for (auto &s : ops) cout << s << "\n";
    return 0;
}