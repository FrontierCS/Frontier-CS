#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    vector<vector<int>> adj(n + 1);
    vector<pair<int, int>> edges;
    edges.reserve(m);

    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
        edges.emplace_back(u, v);
    }

    if (m == 0) {
        // Any coloring is perfect
        for (int i = 1; i <= n; ++i) {
            cout << 1 << (i == n ? '\n' : ' ');
        }
        return 0;
    }

    mt19937 rng((uint32_t)chrono::steady_clock::now().time_since_epoch().count());

    const int ATTEMPTS = 3;
    const int MAX_ITERS = 20;

    vector<int> color(n + 1);
    vector<int> countSame(n + 1);
    vector<int> order(n);
    vector<int> bestColor(n + 1);
    long long bestConf = (long long)4e18;

    for (int attempt = 0; attempt < ATTEMPTS; ++attempt) {
        // Initialize
        fill(color.begin(), color.end(), 0);
        fill(countSame.begin(), countSame.end(), 0);
        for (int i = 0; i < n; ++i) order[i] = i + 1;
        shuffle(order.begin(), order.end(), rng);

        // Greedy initial coloring
        for (int idx = 0; idx < n; ++idx) {
            int v = order[idx];
            int cnt[4] = {0, 0, 0, 0};
            for (int u : adj[v]) {
                int cu = color[u];
                if (cu != 0) cnt[cu]++;
            }
            int bestC = 1;
            int bestVal = cnt[1];
            for (int c = 2; c <= 3; ++c) {
                if (cnt[c] < bestVal) {
                    bestVal = cnt[c];
                    bestC = c;
                }
            }
            color[v] = bestC;
        }

        // Initial same-color counts
        for (auto &e : edges) {
            int u = e.first, v = e.second;
            if (color[u] == color[v]) {
                countSame[u]++;
                countSame[v]++;
            }
        }

        // Local search
        for (int it = 0; it < MAX_ITERS; ++it) {
            bool changed = false;
            shuffle(order.begin(), order.end(), rng);
            for (int idx = 0; idx < n; ++idx) {
                int v = order[idx];
                if (adj[v].empty()) continue;

                int oldC = color[v];
                int currSame = countSame[v];

                int cnt[4] = {0, 0, 0, 0};
                for (int u : adj[v]) {
                    int cu = color[u];
                    cnt[cu]++;
                }

                int bestC = oldC;
                int bestSame = currSame;
                for (int c = 1; c <= 3; ++c) {
                    if (cnt[c] < bestSame) {
                        bestSame = cnt[c];
                        bestC = c;
                    }
                }

                if (bestC != oldC) {
                    for (int u : adj[v]) {
                        int cu = color[u];
                        if (cu == oldC) countSame[u]--;
                        if (cu == bestC) countSame[u]++;
                    }
                    color[v] = bestC;
                    countSame[v] = bestSame;
                    changed = true;
                }
            }
            if (!changed) break;
        }

        // Compute conflicts
        long long conflicts = 0;
        for (auto &e : edges) {
            int u = e.first, v = e.second;
            if (color[u] == color[v]) conflicts++;
        }

        if (conflicts < bestConf) {
            bestConf = conflicts;
            bestColor = color;
        }
    }

    for (int i = 1; i <= n; ++i) {
        cout << bestColor[i] << (i == n ? '\n' : ' ');
    }

    return 0;
}