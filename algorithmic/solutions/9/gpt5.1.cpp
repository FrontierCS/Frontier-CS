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

        vector<int> p(n + 1);
        for (int i = 1; i <= n; ++i) cin >> p[i];

        vector<vector<int>> g(n + 1);
        vector<int> eu(n), ev(n);
        for (int i = 1; i <= n - 1; ++i) {
            int u, v;
            cin >> u >> v;
            eu[i] = u;
            ev[i] = v;
            g[u].push_back(v);
            g[v].push_back(u);
        }

        // Edge ID matrix for O(1) lookup
        vector<vector<int>> edgeID(n + 1, vector<int>(n + 1, -1));
        for (int i = 1; i <= n - 1; ++i) {
            int u = eu[i], v = ev[i];
            edgeID[u][v] = i;
            edgeID[v][u] = i;
        }

        // Leaf peeling order
        vector<int> deg(n + 1);
        for (int i = 1; i <= n; ++i) deg[i] = (int)g[i].size();
        vector<int> order;
        order.reserve(n);
        queue<int> q;
        for (int i = 1; i <= n; ++i) {
            if (deg[i] <= 1) q.push(i);
        }
        vector<bool> removed(n + 1, false);
        while (!q.empty()) {
            int v = q.front();
            q.pop();
            if (removed[v]) continue;
            removed[v] = true;
            order.push_back(v);
            for (int to : g[v]) {
                if (!removed[to]) {
                    if (--deg[to] == 1) q.push(to);
                }
            }
        }
        if ((int)order.size() != n) {
            for (int i = 1; i <= n; ++i)
                if (!removed[i]) order.push_back(i);
        }

        // Active vertices
        vector<bool> active(n + 1, true);

        // Token positions
        vector<int> pos(n + 1);
        for (int v = 1; v <= n; ++v) {
            int tok = p[v];
            pos[tok] = v;
        }

        vector<int> ops;
        ops.reserve((size_t)n * (size_t)n);

        vector<int> parent(n + 1);

        // Process vertices in leaf-peeling order except last
        for (int idx = 0; idx < n - 1; ++idx) {
            int v = order[idx];
            if (!active[v]) continue;
            if (p[v] == v) {
                active[v] = false;
                continue;
            }
            int start = pos[v];

            // BFS on active subgraph from start to v
            fill(parent.begin(), parent.end(), -1);
            queue<int> qq;
            parent[start] = start;
            qq.push(start);
            while (!qq.empty()) {
                int x = qq.front();
                qq.pop();
                if (x == v) break;
                for (int y : g[x]) {
                    if (!active[y]) continue;
                    if (parent[y] != -1) continue;
                    parent[y] = x;
                    qq.push(y);
                }
            }

            // Reconstruct path from start to v
            int x = v;
            vector<int> path;
            while (x != start) {
                path.push_back(x);
                x = parent[x];
            }
            path.push_back(start);
            reverse(path.begin(), path.end());

            // Perform swaps along the path
            for (int i = 0; i + 1 < (int)path.size(); ++i) {
                int a = path[i];
                int b = path[i + 1];
                int eid = edgeID[a][b];
                ops.push_back(eid);
                int tokA = p[a], tokB = p[b];
                p[a] = tokB;
                p[b] = tokA;
                pos[tokA] = b;
                pos[tokB] = a;
            }

            active[v] = false;
        }

        // Output operations
        cout << ops.size() << "\n";
        for (int eid : ops) {
            cout << 1 << " " << eid << "\n";
        }
    }

    return 0;
}