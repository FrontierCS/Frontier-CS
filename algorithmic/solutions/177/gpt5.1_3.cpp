#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    vector<vector<int>> adj(n);
    vector<pair<int, int>> edges;
    edges.reserve(m);

    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        adj[u].push_back(v);
        adj[v].push_back(u);
        edges.emplace_back(u, v);
    }

    mt19937 rng((unsigned)chrono::steady_clock::now().time_since_epoch().count());

    const int MAX_RESTARTS = 6;
    const int MAX_PASSES = 30;

    vector<int> col(n), bestCol(n);
    long long bestConf = (long long)m + 1;

    vector<int> order(n);
    iota(order.begin(), order.end(), 0);

    for (int restart = 0; restart < MAX_RESTARTS; ++restart) {
        // Initialization
        if (restart == 0) {
            // Greedy initialization based on degree
            vector<int> degOrder(n);
            iota(degOrder.begin(), degOrder.end(), 0);
            sort(degOrder.begin(), degOrder.end(), [&](int a, int b) {
                return adj[a].size() > adj[b].size();
            });
            fill(col.begin(), col.end(), 0);
            for (int v : degOrder) {
                int c1 = 0, c2 = 0, c3 = 0;
                for (int u : adj[v]) {
                    int cu = col[u];
                    if (cu == 1) ++c1;
                    else if (cu == 2) ++c2;
                    else if (cu == 3) ++c3;
                }
                int bestColor = 1;
                int bestC = c1;
                if (c2 < bestC) { bestC = c2; bestColor = 2; }
                if (c3 < bestC) { bestC = c3; bestColor = 3; }
                col[v] = bestColor;
            }
        } else {
            // Random initialization
            for (int i = 0; i < n; ++i) {
                col[i] = (int)(rng() % 3) + 1;
            }
        }

        // Local search passes
        for (int pass = 0; pass < MAX_PASSES; ++pass) {
            bool improved = false;
            shuffle(order.begin(), order.end(), rng);

            for (int idx = 0; idx < n; ++idx) {
                int v = order[idx];
                if (adj[v].empty()) continue;

                int c1 = 0, c2 = 0, c3 = 0;
                for (int u : adj[v]) {
                    int cu = col[u];
                    if (cu == 1) ++c1;
                    else if (cu == 2) ++c2;
                    else ++c3;
                }

                int curColor = col[v];
                int curConf = (curColor == 1 ? c1 : (curColor == 2 ? c2 : c3));
                int bestColor = curColor;
                int bestC = curConf;

                if (c1 < bestC) { bestC = c1; bestColor = 1; }
                if (c2 < bestC) { bestC = c2; bestColor = 2; }
                if (c3 < bestC) { bestC = c3; bestColor = 3; }

                if (bestColor != curColor && bestC < curConf) {
                    col[v] = bestColor;
                    improved = true;
                }
            }

            if (!improved) break;
        }

        // Compute conflicts for this restart
        long long b = 0;
        for (auto &e : edges) {
            if (col[e.first] == col[e.second]) ++b;
        }
        if (b < bestConf) {
            bestConf = b;
            bestCol = col;
        }
    }

    for (int i = 0; i < n; ++i) {
        cout << bestCol[i] << (i + 1 < n ? ' ' : '\n');
    }

    return 0;
}