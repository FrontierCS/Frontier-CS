#include <bits/stdc++.h>
using namespace std;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(nullptr);
    cout.tie(nullptr);

    int t;
    cin >> t;
    while (t--) {
        int n;
        cin >> n;
        vector<vector<int>> adj(n + 1);
        for (int i = 0; i < n - 1; i++) {
            int u, v;
            cin >> u >> v;
            adj[u].push_back(v);
            adj[v].push_back(u);
        }

        vector<int> parent(n + 1, 0), depth(n + 1, 0);
        vector<int> in(n + 1, 0), out(n + 1, 0);
        int timer = 0;
        function<void(int, int)> dfs = [&](int u, int p) {
            parent[u] = p;
            in[u] = ++timer;
            for (int v : adj[u]) {
                if (v == p) continue;
                depth[v] = depth[u] + 1;
                dfs(v, u);
            }
            out[u] = timer;
        };
        dfs(1, 0);

        auto in_subtree = [&](int x, int v) -> bool {
            return in[x] <= in[v] && in[v] <= out[x];
        };

        vector<int> active;
        for (int i = 1; i <= n; i++) active.push_back(i);

        vector<int> vis(n + 1, 0);
        int current_time = 0;

        while (active.size() > 1) {
            int best_x = -1, best_val = 1e9, best_depth = 1e9;
            bool found_optimal = false;

            for (int x : active) {
                current_time++;
                int size1 = 0, size0 = 0;
                for (int v : active) {
                    if (in_subtree(x, v)) {
                        size1++;
                    } else {
                        int p = (v == 1) ? 1 : parent[v];
                        if (vis[p] != current_time) {
                            vis[p] = current_time;
                            size0++;
                        }
                    }
                }
                int val = max(size1, size0);
                if (val < best_val || (val == best_val && depth[x] < best_depth)) {
                    best_val = val;
                    best_x = x;
                    best_depth = depth[x];
                }
                if (val == 1) {
                    found_optimal = true;
                    break;
                }
            }

            cout << "? " << best_x << endl;
            cout.flush();
            int r;
            cin >> r;

            if (r == 1) {
                vector<int> new_active;
                for (int v : active) {
                    if (in_subtree(best_x, v)) {
                        new_active.push_back(v);
                    }
                }
                active = move(new_active);
            } else {
                vector<int> new_active;
                current_time++;
                for (int v : active) {
                    if (!in_subtree(best_x, v)) {
                        int p = (v == 1) ? 1 : parent[v];
                        if (vis[p] != current_time) {
                            vis[p] = current_time;
                            new_active.push_back(p);
                        }
                    }
                }
                active = move(new_active);
            }
        }

        cout << "! " << active[0] << endl;
        cout.flush();
    }
    return 0;
}