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

        vector<int> U(n), V(n); // 1..n-1 used
        vector<vector<pair<int,int>>> adj(n + 1);
        for (int i = 1; i <= n - 1; ++i) {
            int u, v;
            cin >> u >> v;
            U[i] = u; V[i] = v;
            adj[u].push_back({v, i});
            adj[v].push_back({u, i});
        }

        // Root the tree at 1 and compute parent, depth, and parent edge
        vector<int> parent(n + 1, 0), depth(n + 1, 0), pedge(n + 1, 0);
        vector<char> vis(n + 1, false);
        vector<int> q;
        q.push_back(1);
        vis[1] = true;
        parent[1] = 0; pedge[1] = 0; depth[1] = 0;
        for (int i = 0; i < (int)q.size(); ++i) {
            int u = q[i];
            for (auto [v, ei] : adj[u]) {
                if (!vis[v]) {
                    vis[v] = true;
                    parent[v] = u;
                    pedge[v] = ei;
                    depth[v] = depth[u] + 1;
                    q.push_back(v);
                }
            }
        }

        // Position of each label
        vector<int> pos(n + 1);
        for (int u = 1; u <= n; ++u) pos[p[u]] = u;

        // Remaining graph degrees and membership
        vector<int> deg(n + 1, 0);
        for (int u = 1; u <= n; ++u) deg[u] = (int)adj[u].size();
        vector<char> inR(n + 1, true);
        int rem = n;

        deque<int> leaves;
        for (int u = 1; u <= n; ++u) if (deg[u] <= 1) leaves.push_back(u);

        vector<int> ops;

        auto do_swap = [&](int e) {
            int a = U[e], b = V[e];
            ops.push_back(e);
            int va = p[a], vb = p[b];
            p[a] = vb; p[b] = va;
            pos[va] = b; pos[vb] = a;
        };

        auto move_token_along_path = [&](int start, int target) {
            int x = start, y = target;
            vector<int> up, down;
            while (depth[x] > depth[y]) { up.push_back(pedge[x]); x = parent[x]; }
            while (depth[y] > depth[x]) { down.push_back(pedge[y]); y = parent[y]; }
            while (x != y) {
                up.push_back(pedge[x]); x = parent[x];
                down.push_back(pedge[y]); y = parent[y];
            }
            for (int e : up) do_swap(e);
            for (int i = (int)down.size() - 1; i >= 0; --i) do_swap(down[i]);
        };

        while (rem > 1) {
            while (!leaves.empty() && (!inR[leaves.front()] || deg[leaves.front()] != 1)) leaves.pop_front();
            if (leaves.empty()) {
                for (int u = 1; u <= n; ++u)
                    if (inR[u] && deg[u] == 1) leaves.push_back(u);
                if (leaves.empty()) break;
            }
            int v = leaves.front(); leaves.pop_front();
            if (!inR[v] || deg[v] != 1) continue;

            int cur = pos[v];
            if (cur != v) move_token_along_path(cur, v);

            inR[v] = false;
            --rem;

            int neighbor = 0;
            for (auto [to, ei] : adj[v]) if (inR[to]) { neighbor = to; break; }
            deg[v] = 0;
            if (neighbor) {
                --deg[neighbor];
                if (deg[neighbor] == 1) leaves.push_back(neighbor);
            }
        }

        cout << ops.size() << "\n";
        for (int e : ops) {
            cout << 1 << " " << e << "\n";
        }
    }

    return 0;
}