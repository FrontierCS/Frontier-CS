#include <bits/stdc++.h>
using namespace std;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    cin >> n >> m;
    vector<vector<int>> adj(n);
    for (int i = 0; i < m; i++) {
        int u, v;
        cin >> u >> v;
        u--; v--;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    // If no edges, any coloring works.
    if (m == 0) {
        for (int i = 0; i < n; i++) {
            cout << 1 << " \n"[i == n - 1];
        }
        return 0;
    }

    const int RESTARTS = 10;
    const int MAX_PASSES = 20;

    random_device rd;
    mt19937 rng(rd());

    vector<int> best_color(n);
    int best_conflicts = m; // worst case: all edges conflict

    for (int restart = 0; restart < RESTARTS; restart++) {
        vector<int> color(n);
        for (int i = 0; i < n; i++) {
            color[i] = rng() % 3;
        }

        // Compute initial conflicts
        int conflicts = 0;
        for (int u = 0; u < n; u++) {
            for (int v : adj[u]) {
                if (v > u) continue;
                if (color[u] == color[v]) conflicts++;
            }
        }

        // Local improvement passes
        for (int pass = 0; pass < MAX_PASSES; pass++) {
            bool improved = false;
            vector<int> order(n);
            iota(order.begin(), order.end(), 0);
            shuffle(order.begin(), order.end(), rng);

            for (int u : order) {
                int cnt[3] = {0, 0, 0};
                for (int v : adj[u]) {
                    cnt[color[v]]++;
                }
                int cur = color[u];
                int best = cur;
                int minc = cnt[cur];
                for (int c = 0; c < 3; c++) {
                    if (c == cur) continue;
                    if (cnt[c] < minc) {
                        minc = cnt[c];
                        best = c;
                    } else if (cnt[c] == minc && (rng() % 2)) {
                        best = c;
                    }
                }
                if (best != cur) {
                    conflicts += cnt[best] - cnt[cur];
                    color[u] = best;
                    improved = true;
                }
            }

            if (!improved) break;
            if (conflicts == 0) break;
        }

        if (conflicts < best_conflicts) {
            best_conflicts = conflicts;
            best_color = color;
        }
        if (best_conflicts == 0) break;
    }

    for (int i = 0; i < n; i++) {
        cout << best_color[i] + 1 << " \n"[i == n - 1];
    }

    return 0;
}