#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    cin >> T;
    while (T--) {
        int n;
        cin >> n;
        vector<int> p(n + 1);
        for (int i = 1; i <= n; i++) cin >> p[i];

        vector<pair<int, int>> edges(n - 1);
        vector<vector<int>> adj(n + 1);
        for (int i = 0; i < n - 1; i++) {
            int u, v;
            cin >> u >> v;
            edges[i] = {u, v};
            adj[u].push_back(v);
            adj[v].push_back(u);
        }

        // Precompute all-pairs distances in the tree
        vector<vector<int>> dist(n + 1, vector<int>(n + 1, -1));
        for (int s = 1; s <= n; s++) {
            queue<int> q;
            dist[s][s] = 0;
            q.push(s);
            while (!q.empty()) {
                int u = q.front(); q.pop();
                for (int v : adj[u]) {
                    if (dist[s][v] == -1) {
                        dist[s][v] = dist[s][u] + 1;
                        q.push(v);
                    }
                }
            }
        }

        vector<int> cur = p;                     // current numbers on vertices
        vector<vector<int>> operations;          // list of operations

        while (true) {
            // Check if we have reached the identity permutation
            bool sorted = true;
            for (int i = 1; i <= n; i++) {
                if (cur[i] != i) {
                    sorted = false;
                    break;
                }
            }
            if (sorted) break;

            // Compute delta (gain) for each edge
            vector<pair<int, int>> deltas;       // (delta, edge_index)
            for (int idx = 0; idx < n - 1; idx++) {
                int u = edges[idx].first, v = edges[idx].second;
                int x = cur[u], y = cur[v];
                int delta = (dist[u][y] + dist[v][x]) - (dist[u][x] + dist[v][y]);
                deltas.emplace_back(delta, idx);
            }
            sort(deltas.begin(), deltas.end());   // sort by delta ascending

            // Collect edges with non‑positive delta
            vector<pair<int, int>> neg_edges;
            for (auto& pr : deltas) {
                if (pr.first <= 0) neg_edges.push_back(pr);
            }

            vector<bool> used(n + 1, false);
            vector<int> selected;

            // Greedily pick a matching from non‑positive edges
            for (auto& pr : neg_edges) {
                int idx = pr.second;
                int u = edges[idx].first, v = edges[idx].second;
                if (!used[u] && !used[v]) {
                    selected.push_back(idx);
                    used[u] = used[v] = true;
                }
            }

            // If no edge was selected, take the one with the smallest delta
            if (selected.empty()) {
                int idx = deltas[0].second;
                selected.push_back(idx);
            }

            // Apply the swaps of this operation
            for (int idx : selected) {
                int u = edges[idx].first, v = edges[idx].second;
                swap(cur[u], cur[v]);
            }

            // Store the operation (edge indices are 1‑based in the output)
            vector<int> op;
            for (int idx : selected) op.push_back(idx + 1);
            operations.push_back(op);
        }

        // Output the solution
        cout << operations.size() << "\n";
        for (auto& op : operations) {
            cout << op.size();
            for (int e : op) cout << " " << e;
            cout << "\n";
        }
    }
    return 0;
}