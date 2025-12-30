#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    long long m;
    if (!(cin >> n >> m)) return 0;

    vector<vector<int>> adj(n);
    vector<pair<int,int>> edges;
    edges.reserve(m);

    for (long long i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        adj[u].push_back(v);
        adj[v].push_back(u);
        edges.emplace_back(u, v);
    }

    // Initial greedy coloring
    vector<int> color(n, 1);
    for (int v = 0; v < n; ++v) {
        int cnt_local[4] = {0, 0, 0, 0};
        for (int u : adj[v]) {
            if (u < v) {
                ++cnt_local[color[u]];
            }
        }
        int bestc = 1;
        int bestv = cnt_local[1];
        for (int c = 2; c <= 3; ++c) {
            if (cnt_local[c] < bestv) {
                bestv = cnt_local[c];
                bestc = c;
            }
        }
        color[v] = bestc;
    }

    // Build neighbor color counts and initial conflict count
    vector<array<int,4>> cnt(n); // cnt[v][c] = number of neighbors of v with color c
    long long conflicts = 0;
    for (auto &e : edges) {
        int u = e.first;
        int v = e.second;
        int cu = color[u];
        int cv = color[v];
        ++cnt[u][cv];
        ++cnt[v][cu];
        if (cu == cv) ++conflicts;
    }

    // Local search: single-vertex recoloring improvements
    mt19937 rng((uint32_t)chrono::steady_clock::now().time_since_epoch().count());
    vector<int> order(n);
    iota(order.begin(), order.end(), 0);

    const int max_passes = 20;
    for (int iter = 0; iter < max_passes; ++iter) {
        bool improved = false;
        shuffle(order.begin(), order.end(), rng);
        for (int idx = 0; idx < n; ++idx) {
            int v = order[idx];
            int oldc = color[v];
            int bestc = oldc;
            int best_conf = cnt[v][oldc];

            // Try all colors
            for (int c = 1; c <= 3; ++c) {
                int c_conf = cnt[v][c];
                if (c_conf < best_conf) {
                    best_conf = c_conf;
                    bestc = c;
                }
            }

            if (bestc != oldc) {
                int delta = cnt[v][bestc] - cnt[v][oldc]; // <= 0
                if (delta < 0) {
                    improved = true;
                    conflicts += delta;

                    // Update neighbor color counts
                    for (int u : adj[v]) {
                        --cnt[u][oldc];
                        ++cnt[u][bestc];
                    }
                    color[v] = bestc;
                }
            }
        }
        if (!improved) break;
    }

    // Output colors (1..3)
    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << color[i];
    }
    cout << '\n';

    return 0;
}