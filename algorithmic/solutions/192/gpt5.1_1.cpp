#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    vector<vector<int>> g(n);
    vector<pair<int,int>> edges;
    edges.reserve(m);

    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        g[u].push_back(v);
        g[v].push_back(u);
        edges.emplace_back(u, v);
    }

    // If no edges, any partition is optimal (score = 1)
    if (m == 0) {
        for (int i = 0; i < n; ++i) {
            if (i) cout << ' ';
            cout << 0;
        }
        cout << '\n';
        return 0;
    }

    // Degrees
    vector<int> deg(n);
    for (int i = 0; i < n; ++i) {
        deg[i] = (int)g[i].size();
    }

    // Random generator
    std::random_device rd;
    std::mt19937_64 rng(rd() ^ (uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count());

    vector<int> best_side(n);
    long long best_cut = -1;

    const int MAX_ATTEMPTS = 10;

    vector<int> side(n), out_deg(n), delta(n);

    for (int attempt = 0; attempt < MAX_ATTEMPTS; ++attempt) {
        // Random initial partition
        for (int i = 0; i < n; ++i) {
            side[i] = (int)(rng() & 1);
        }

        // Initialize out_deg and cut
        fill(out_deg.begin(), out_deg.end(), 0);
        long long cut = 0;
        for (auto &e : edges) {
            int u = e.first;
            int v = e.second;
            if (side[u] != side[v]) {
                ++cut;
                ++out_deg[u];
                ++out_deg[v];
            }
        }

        // Initialize deltas
        for (int i = 0; i < n; ++i) {
            delta[i] = deg[i] - 2 * out_deg[i];
        }

        // Local search: hill climbing with best single-vertex flip
        while (true) {
            int best_v = -1;
            int best_d = 0;
            for (int v = 0; v < n; ++v) {
                if (delta[v] > best_d) {
                    best_d = delta[v];
                    best_v = v;
                }
            }
            if (best_d <= 0) break; // local optimum

            int v = best_v;
            int old_side = side[v];
            int dv = delta[v];

            cut += dv;
            side[v] ^= 1;

            // Update neighbors and deltas
            for (int u : g[v]) {
                if (side[u] == old_side) {
                    // edge was internal, becomes crossing
                    ++out_deg[u];
                    delta[u] -= 2;
                    ++out_deg[v];
                } else {
                    // edge was crossing, becomes internal
                    --out_deg[u];
                    delta[u] += 2;
                    --out_deg[v];
                }
            }
            delta[v] = deg[v] - 2 * out_deg[v];
        }

        if (cut > best_cut) {
            best_cut = cut;
            best_side = side;
        }
    }

    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << best_side[i];
    }
    cout << '\n';

    return 0;
}