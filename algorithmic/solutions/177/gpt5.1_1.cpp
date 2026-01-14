#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    vector<vector<int>> adj(n);
    vector<pair<int,int>> edges;
    edges.reserve(m);

    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        adj[u].push_back(v);
        adj[v].push_back(u);
        edges.emplace_back(u, v);
    }

    mt19937 rng((uint64_t)chrono::steady_clock::now().time_since_epoch().count());

    const int P = 20; // number of passes
    vector<int> best_col(n, 1), cur_col(n, 1), order(n);
    iota(order.begin(), order.end(), 0);

    int best_conflicts = INT_MAX;

    for (int pass = 0; pass < P; ++pass) {
        shuffle(order.begin(), order.end(), rng);
        fill(cur_col.begin(), cur_col.end(), 0);

        for (int idx = 0; idx < n; ++idx) {
            int v = order[idx];
            int cnt1 = 0, cnt2 = 0, cnt3 = 0;

            for (int u : adj[v]) {
                int c = cur_col[u];
                if (!c) continue;
                if (c == 1) ++cnt1;
                else if (c == 2) ++cnt2;
                else ++cnt3;
            }

            int bestColor = 1;
            int bestCnt = cnt1;
            if (cnt2 < bestCnt) { bestCnt = cnt2; bestColor = 2; }
            if (cnt3 < bestCnt) { bestCnt = cnt3; bestColor = 3; }
            cur_col[v] = bestColor;
        }

        int conflicts = 0;
        for (const auto &e : edges) {
            if (cur_col[e.first] == cur_col[e.second]) ++conflicts;
        }

        if (conflicts < best_conflicts) {
            best_conflicts = conflicts;
            best_col = cur_col;
            if (best_conflicts == 0) break;
        }
    }

    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << best_col[i];
    }
    cout << '\n';

    return 0;
}