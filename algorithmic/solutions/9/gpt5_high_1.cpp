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
        vector<int> p(n + 1), pos(n + 1);
        for (int i = 1; i <= n; ++i) {
            cin >> p[i];
            pos[p[i]] = i;
        }
        vector<int> eu(n), ev(n); // edges indexed from 1..n-1
        vector<vector<pair<int,int>>> g(n + 1);
        for (int i = 1; i <= n - 1; ++i) {
            int u, v;
            cin >> u >> v;
            eu[i] = u; ev[i] = v;
            g[u].push_back({v, i});
            g[v].push_back({u, i});
        }

        // BFS to compute parent, depth, parentEdge
        vector<int> parent(n + 1, 0), depth(n + 1, 0), parentEdge(n + 1, 0);
        vector<char> vis(n + 1, 0);
        queue<int> q;
        q.push(1);
        vis[1] = 1;
        while (!q.empty()) {
            int u = q.front(); q.pop();
            for (auto [v, eid] : g[u]) {
                if (!vis[v]) {
                    vis[v] = 1;
                    parent[v] = u;
                    parentEdge[v] = eid;
                    depth[v] = depth[u] + 1;
                    q.push(v);
                }
            }
        }

        vector<char> active(n + 1, 1);
        vector<int> deg(n + 1, 0);
        queue<int> leaves;
        for (int i = 1; i <= n; ++i) {
            deg[i] = (int)g[i].size();
            if (deg[i] <= 1) leaves.push(i);
        }

        vector<int> ops; ops.reserve(n * 2);

        auto doSwap = [&](int eid) {
            int u = eu[eid], v = ev[eid];
            int t1 = p[u], t2 = p[v];
            swap(p[u], p[v]);
            pos[t1] = v;
            pos[t2] = u;
            ops.push_back(eid);
        };

        auto moveTo = [&](int t) {
            int u = pos[t];
            int v = t;
            if (u == v) return;
            vector<int> up, down;
            while (u != v) {
                if (depth[u] > depth[v]) {
                    up.push_back(parentEdge[u]);
                    u = parent[u];
                } else if (depth[v] > depth[u]) {
                    down.push_back(parentEdge[v]);
                    v = parent[v];
                } else {
                    up.push_back(parentEdge[u]);
                    u = parent[u];
                    down.push_back(parentEdge[v]);
                    v = parent[v];
                }
            }
            for (int eid : up) doSwap(eid);
            for (int i = (int)down.size() - 1; i >= 0; --i) doSwap(down[i]);
        };

        int cntActive = n;
        while (cntActive > 1) {
            int t = -1;
            while (!leaves.empty()) {
                int x = leaves.front(); leaves.pop();
                if (active[x] && deg[x] == 1) { t = x; break; }
            }
            if (t == -1) {
                // Should not happen in a tree, but safeguard:
                for (int i = 1; i <= n; ++i) {
                    if (active[i] && deg[i] == 1) { t = i; break; }
                }
                if (t == -1) break;
            }
            moveTo(t);
            active[t] = 0;
            --cntActive;
            for (auto [w, eid] : g[t]) {
                if (active[w]) {
                    deg[w]--;
                    if (deg[w] == 1) leaves.push(w);
                }
            }
        }

        cout << ops.size() << '\n';
        for (int eid : ops) {
            cout << 1 << ' ' << eid << '\n';
        }
    }
    return 0;
}