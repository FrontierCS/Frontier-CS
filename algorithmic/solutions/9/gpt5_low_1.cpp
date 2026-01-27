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
        vector<int> p(n+1), pos(n+1);
        for (int i = 1; i <= n; ++i) {
            cin >> p[i];
            pos[p[i]] = i;
        }
        vector<pair<int,int>> edges(n); // 1..n-1
        vector<vector<pair<int,int>>> adj(n+1);
        for (int i = 1; i <= n-1; ++i) {
            int u,v;
            cin >> u >> v;
            edges[i] = {u,v};
            adj[u].push_back({v,i});
            adj[v].push_back({u,i});
        }
        // Root the tree at 1
        vector<int> parent(n+1, 0), depth(n+1, 0), parentEdge(n+1, 0);
        queue<int> q;
        parent[1] = 0; depth[1] = 0;
        q.push(1);
        while (!q.empty()) {
            int u = q.front(); q.pop();
            for (auto [v, id] : adj[u]) {
                if (v == parent[u]) continue;
                parent[v] = u;
                parentEdge[v] = id;
                depth[v] = depth[u] + 1;
                q.push(v);
            }
        }

        vector<int> ops; ops.reserve(n*n/2 + 5);

        auto apply_swap_edge = [&](int idx){
            int a = edges[idx].first;
            int b = edges[idx].second;
            int va = p[a], vb = p[b];
            swap(p[a], p[b]);
            pos[va] = b;
            pos[vb] = a;
        };

        for (int target = 1; target <= n; ++target) {
            while (pos[target] != target) {
                int v = pos[target];
                int w = target;
                vector<int> up, down;
                int vv = v, ww = w;
                while (depth[vv] > depth[ww]) {
                    up.push_back(parentEdge[vv]);
                    vv = parent[vv];
                }
                while (depth[ww] > depth[vv]) {
                    down.push_back(parentEdge[ww]);
                    ww = parent[ww];
                }
                while (vv != ww) {
                    up.push_back(parentEdge[vv]);
                    vv = parent[vv];
                    down.push_back(parentEdge[ww]);
                    ww = parent[ww];
                }
                // path is up followed by reverse(down)
                for (int id : up) {
                    ops.push_back(id);
                    apply_swap_edge(id);
                }
                for (int i = (int)down.size()-1; i >= 0; --i) {
                    int id = down[i];
                    ops.push_back(id);
                    apply_swap_edge(id);
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