#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        int n;
        cin >> n;
        vector<int> val(n + 1), pos(n + 1);
        for (int i = 1; i <= n; ++i) {
            cin >> val[i];
        }
        for (int i = 1; i <= n; ++i) pos[val[i]] = i;

        vector<vector<pair<int,int>>> adj(n + 1);
        vector<vector<int>> edgeId(n + 1, vector<int>(n + 1, -1));
        for (int i = 1; i <= n - 1; ++i) {
            int u, v;
            cin >> u >> v;
            adj[u].push_back({v, i});
            adj[v].push_back({u, i});
            edgeId[u][v] = i;
            edgeId[v][u] = i;
        }

        vector<int> ops; ops.reserve(n * 10);

        vector<int> deg(n + 1);
        vector<char> alive(n + 1, 1);
        for (int i = 1; i <= n; ++i) deg[i] = (int)adj[i].size();
        queue<int> q;
        for (int i = 1; i <= n; ++i) if (deg[i] <= 1) q.push(i);

        vector<int> parent(n + 1);
        vector<char> vis(n + 1);

        auto bfs_build_parent = [&](int root) {
            fill(parent.begin(), parent.end(), -1);
            fill(vis.begin(), vis.end(), 0);
            queue<int> qq;
            qq.push(root);
            vis[root] = 1;
            parent[root] = 0;
            while (!qq.empty()) {
                int u = qq.front(); qq.pop();
                for (auto [v, id] : adj[u]) {
                    if (!alive[v]) continue;
                    if (!vis[v]) {
                        vis[v] = 1;
                        parent[v] = u;
                        qq.push(v);
                    }
                }
            }
        };

        int remaining = n;
        while (remaining > 0) {
            while (!q.empty()) {
                int v = q.front(); q.pop();
                if (!alive[v] || deg[v] > 1) continue;

                if (val[v] != v) {
                    bfs_build_parent(v);
                    int u = pos[v];
                    while (u != v) {
                        int w = parent[u];
                        // swap tokens on edge (u, w)
                        int a = val[u];
                        int b = val[w];
                        val[u] = b;
                        val[w] = a;
                        pos[a] = w;
                        pos[b] = u;
                        ops.push_back(edgeId[u][w]);
                        u = w;
                    }
                }

                // remove v
                alive[v] = 0;
                --remaining;
                for (auto [to, id] : adj[v]) {
                    if (!alive[to]) continue;
                    deg[to]--;
                    if (deg[to] <= 1) q.push(to);
                }
            }
            // In case queue gets empty (shouldn't in a tree unless done), break
            if (remaining > 0) {
                // find any alive node to push (should be leaf exists)
                for (int i = 1; i <= n; ++i) {
                    if (alive[i] && deg[i] <= 1) {
                        q.push(i);
                    }
                }
            }
        }

        cout << ops.size() << "\n";
        for (int id : ops) {
            cout << 1 << " " << id << "\n";
        }
    }
    return 0;
}