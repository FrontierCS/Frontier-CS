#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    vector<pair<int,int>> edges;
    edges.reserve(m);
    vector<vector<int>> g(n);
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        edges.emplace_back(u, v);
        g[u].push_back(v);
        g[v].push_back(u);
    }

    if (m == 0) {
        for (int i = 0; i < n; ++i) {
            cout << 1 << (i + 1 < n ? ' ' : '\n');
        }
        return 0;
    }

    mt19937 rng((uint64_t)chrono::steady_clock::now().time_since_epoch().count());

    const int restarts = 5;
    const int maxPasses = 80;

    vector<int> bestColor(n, 0);
    long long bestConfEdges = (1LL << 60);

    vector<int> order(n);
    iota(order.begin(), order.end(), 0);

    for (int r = 0; r < restarts; ++r) {
        // Random initial colors
        vector<int> color(n);
        uniform_int_distribution<int> distColor(0, 2);
        for (int i = 0; i < n; ++i) {
            color[i] = distColor(rng);
        }

        // Neighbor color counts
        vector<array<int,3>> cnt(n);
        for (int i = 0; i < n; ++i) cnt[i] = {0,0,0};

        for (auto &e : edges) {
            int u = e.first;
            int v = e.second;
            int cu = color[u];
            int cv = color[v];
            cnt[u][cv]++;
            cnt[v][cu]++;
        }

        // Local search
        for (int pass = 0; pass < maxPasses; ++pass) {
            bool improved = false;
            shuffle(order.begin(), order.end(), rng);

            for (int idx = 0; idx < n; ++idx) {
                int v = order[idx];
                int curC = color[v];
                int curConf = cnt[v][curC];

                int bestC = curC;
                int bestConf = curConf;

                for (int c = 0; c < 3; ++c) {
                    if (c == curC) continue;
                    int cConf = cnt[v][c];
                    if (cConf < bestConf) {
                        bestConf = cConf;
                        bestC = c;
                    }
                }

                if (bestC != curC) {
                    improved = true;
                    // Update neighbors' counts
                    for (int u : g[v]) {
                        cnt[u][curC]--;
                        cnt[u][bestC]++;
                    }
                    color[v] = bestC;
                }
            }

            if (!improved) break;
        }

        // Compute number of conflicting edges
        long long confEdges = 0;
        for (auto &e : edges) {
            if (color[e.first] == color[e.second]) ++confEdges;
        }

        if (confEdges < bestConfEdges) {
            bestConfEdges = confEdges;
            bestColor = color;
        }
    }

    for (int i = 0; i < n; ++i) {
        cout << (bestColor[i] + 1) << (i + 1 < n ? ' ' : '\n');
    }

    return 0;
}