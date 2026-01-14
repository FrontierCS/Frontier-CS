#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    int T;
    cin >> T;
    while (T--) {
        int n;
        cin >> n;
        vector<int> p(n + 1);
        for (int i = 1; i <= n; ++i) {
            cin >> p[i];
        }
        vector<tuple<int, int, int>> edges; // (u, v, idx)
        vector<vector<int>> adj(n + 1);
        for (int i = 1; i <= n - 1; ++i) {
            int u, v;
            cin >> u >> v;
            edges.emplace_back(u, v, i);
            adj[u].push_back(v);
            adj[v].push_back(u);
        }
        // Precompute all-pairs distances
        vector<vector<int>> dist(n + 1, vector<int>(n + 1, -1));
        for (int s = 1; s <= n; ++s) {
            queue<int> q;
            dist[s][s] = 0;
            q.push(s);
            while (!q.empty()) {
                int u = q.front();
                q.pop();
                for (int v : adj[u]) {
                    if (dist[s][v] == -1) {
                        dist[s][v] = dist[s][u] + 1;
                        q.push(v);
                    }
                }
            }
        }
        // Process operations
        vector<vector<int>> operations;
        while (true) {
            bool sorted = true;
            for (int i = 1; i <= n; ++i) {
                if (p[i] != i) {
                    sorted = false;
                    break;
                }
            }
            if (sorted) break;

            vector<bool> used(n + 1, false);
            vector<int> matching;
            // First pass: direct swaps (both values are at each other's target)
            for (auto &[u, v, idx] : edges) {
                if (!used[u] && !used[v] && p[u] == v && p[v] == u) {
                    matching.push_back(idx);
                    used[u] = used[v] = true;
                }
            }
            // Second pass: positive gain swaps
            for (auto &[u, v, idx] : edges) {
                if (!used[u] && !used[v]) {
                    int gain = (dist[u][p[u]] + dist[v][p[v]]) - (dist[u][p[v]] + dist[v][p[u]]);
                    if (gain > 0) {
                        matching.push_back(idx);
                        used[u] = used[v] = true;
                    }
                }
            }
            // Third pass: fallback – any edge with at least one misplaced endpoint
            if (matching.empty()) {
                for (auto &[u, v, idx] : edges) {
                    if (!used[u] && !used[v] && (p[u] != u || p[v] != v)) {
                        matching.push_back(idx);
                        used[u] = used[v] = true;
                        break; // take only one
                    }
                }
            }
            // Emergency: should not happen, but take any edge if still empty
            if (matching.empty()) {
                for (auto &[u, v, idx] : edges) {
                    if (!used[u] && !used[v]) {
                        matching.push_back(idx);
                        break;
                    }
                }
            }
            // Apply the swaps of this operation
            for (int idx : matching) {
                int u = get<0>(edges[idx - 1]);
                int v = get<1>(edges[idx - 1]);
                swap(p[u], p[v]);
            }
            operations.push_back(matching);
        }
        // Output
        cout << operations.size() << "\n";
        for (auto &matching : operations) {
            cout << matching.size();
            for (int idx : matching) {
                cout << " " << idx;
            }
            cout << "\n";
        }
    }
    return 0;
}