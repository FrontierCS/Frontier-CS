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
        edges.emplace_back(u, v);
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    mt19937 rng((unsigned)chrono::steady_clock::now().time_since_epoch().count());

    vector<int> color(n + 1);
    vector<int> bestColor(n + 1);
    long long bestConf = (long long)4e18;

    const int RESTARTS = 3;
    const int MAX_SWEEPS = 50;

    // cnt[v][c] = number of neighbors of v that currently have color c (1..3)
    vector<array<int, 4>> cnt(n + 1);

    for (int rs = 0; rs < RESTARTS; ++rs) {
        // Random initial coloring
        for (int v = 1; v <= n; ++v) {
            color[v] = (int)(rng() % 3) + 1;
        }

        // Initialize neighbor color counts
        for (int v = 1; v <= n; ++v) {
            cnt[v][1] = cnt[v][2] = cnt[v][3] = 0;
        }
        for (const auto &e : edges) {
            int u = e.first;
            int v = e.second;
            cnt[u][ color[v] ]++;
            cnt[v][ color[u] ]++;
        }

        // Local search (hill climbing)
        vector<int> order(n);
        for (int i = 0; i < n; ++i) order[i] = i + 1;

        for (int sweep = 0; sweep < MAX_SWEEPS; ++sweep) {
            shuffle(order.begin(), order.end(), rng);
            bool changed = false;

            for (int idx = 0; idx < n; ++idx) {
                int v = order[idx];
                int cur = color[v];
                int bestC = cur;
                int bestDelta = 0;

                int curConf = cnt[v][cur];
                for (int c = 1; c <= 3; ++c) {
                    if (c == cur) continue;
                    int delta = -curConf + cnt[v][c];
                    if (delta < bestDelta) {
                        bestDelta = delta;
                        bestC = c;
                    }
                }

                if (bestDelta < 0) {
                    int old = cur;
                    int neu = bestC;
                    color[v] = neu;
                    changed = true;

                    // Update neighbor counts
                    const auto &neighbors = adj[v];
                    for (int u : neighbors) {
                        cnt[u][old]--;
                        cnt[u][neu]++;
                    }
                }
            }

            if (!changed) break;
        }

        // Evaluate conflicts for this restart
        long long conf = 0;
        for (const auto &e : edges) {
            if (color[e.first] == color[e.second]) conf++;
        }

        if (conf < bestConf) {
            bestConf = conf;
            bestColor = color;
            if (conf == 0) break; // can't do better
        }
    }

    for (int v = 1; v <= n; ++v) {
        if (v > 1) cout << ' ';
        cout << bestColor[v];
    }
    cout << '\n';

    return 0;
}