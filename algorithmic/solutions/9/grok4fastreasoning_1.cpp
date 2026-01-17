#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int T;
    cin >> T;
    for (int t = 0; t < T; ++t) {
        int n;
        cin >> n;
        vector<int> p(n + 1);
        for (int i = 1; i <= n; ++i) {
            cin >> p[i];
        }
        vector<pair<int, int>> edge_list(n);
        vector<vector<pair<int, int>>> edge_adj(n + 1);
        for (int i = 1; i <= n - 1; ++i) {
            int u, v;
            cin >> u >> v;
            edge_list[i] = {u, v};
            edge_adj[u].emplace_back(v, i);
            edge_adj[v].emplace_back(u, i);
        }
        // Build tree_adj for dist
        vector<vector<int>> tree_adj(n + 1);
        for (int i = 1; i <= n - 1; ++i) {
            int u = edge_list[i].first, v = edge_list[i].second;
            tree_adj[u].push_back(v);
            tree_adj[v].push_back(u);
        }
        // Precompute all pairs dist
        vector<vector<int>> dist(n + 1, vector<int>(n + 1, -1));
        for (int s = 1; s <= n; ++s) {
            vector<int> d(n + 1, -1);
            d[s] = 0;
            queue<int> q;
            q.push(s);
            while (!q.empty()) {
                int u = q.front();
                q.pop();
                for (int v : tree_adj[u]) {
                    if (d[v] == -1) {
                        d[v] = d[u] + 1;
                        q.push(v);
                    }
                }
            }
            for (int i = 1; i <= n; ++i) {
                dist[s][i] = d[i];
            }
        }
        // Current label
        vector<int> label = p;
        // Operations
        vector<vector<int>> operations;
        bool is_sorted = false;
        while (!is_sorted) {
            bool check_sorted = true;
            for (int i = 1; i <= n; ++i) {
                if (label[i] != i) {
                    check_sorted = false;
                    break;
                }
            }
            is_sorted = check_sorted;
            if (is_sorted) break;
            // Collect prio and norm
            vector<int> prio, norm;
            for (int eid = 1; eid <= n - 1; ++eid) {
                int u = edge_list[eid].first;
                int v = edge_list[eid].second;
                int lu = label[u], lv = label[v];
                int tu = lu, tv = lv;
                int old_du = dist[u][tu];
                int new_du = dist[v][tu];
                int d1 = new_du - old_du;
                int old_dv = dist[v][tv];
                int new_dv = dist[u][tv];
                int d2 = new_dv - old_dv;
                int del = d1 + d2;
                if (del <= 0) {
                    if (del == -2) {
                        prio.push_back(eid);
                    } else { // del == 0
                        bool can = false;
                        if (d1 == 1) {
                            if (old_du == 0) can = true;
                        } else if (d2 == 1) {
                            if (old_dv == 0) can = true;
                        }
                        if (can) {
                            norm.push_back(eid);
                        }
                    }
                }
            }
            // Build selected
            vector<int> selected;
            vector<bool> used(n + 1, false);
            auto add_if_possible = [&](int eid) -> bool {
                int u = edge_list[eid].first;
                int v = edge_list[eid].second;
                if (!used[u] && !used[v]) {
                    selected.push_back(eid);
                    used[u] = true;
                    used[v] = true;
                    return true;
                }
                return false;
            };
            for (int eid : prio) {
                add_if_possible(eid);
            }
            for (int eid : norm) {
                add_if_possible(eid);
            }
            if (selected.empty()) {
                // Should not happen
                break;
            }
            // Record
            operations.push_back(selected);
            // Perform swaps
            for (int eid : selected) {
                int u = edge_list[eid].first;
                int v = edge_list[eid].second;
                swap(label[u], label[v]);
            }
        }
        // Output
        cout << operations.size() << '\n';
        for (auto& op : operations) {
            cout << op.size();
            for (int e : op) {
                cout << " " << e;
            }
            cout << '\n';
        }
    }
    return 0;
}