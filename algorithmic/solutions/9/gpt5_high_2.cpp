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
        vector<pair<int,int>> edges(n);
        vector<vector<pair<int,int>>> adj(n + 1);
        for (int i = 1; i <= n - 1; ++i) {
            int u, v;
            cin >> u >> v;
            edges[i] = {u, v};
            adj[u].push_back({v, i});
            adj[v].push_back({u, i});
        }
        int LOG = 0;
        while ((1 << LOG) <= n) ++LOG;
        vector<int> depth(n + 1, 0), parent(n + 1, 0), edgeFrom(n + 1, 0);
        // DFS to set parents, depths, and edgeFrom
        vector<int> st;
        st.push_back(1);
        parent[1] = 0;
        depth[1] = 0;
        while (!st.empty()) {
            int u = st.back(); st.pop_back();
            for (auto [v, id] : adj[u]) {
                if (v == parent[u]) continue;
                parent[v] = u;
                depth[v] = depth[u] + 1;
                edgeFrom[v] = id;
                st.push_back(v);
            }
        }
        vector<vector<int>> up(LOG, vector<int>(n + 1, 0));
        for (int v = 1; v <= n; ++v) up[0][v] = parent[v];
        for (int k = 1; k < LOG; ++k) {
            for (int v = 1; v <= n; ++v) {
                up[k][v] = up[k-1][v] ? up[k-1][ up[k-1][v] ] : 0;
            }
        }
        auto lca = [&](int a, int b) {
            if (depth[a] < depth[b]) swap(a, b);
            int diff = depth[a] - depth[b];
            for (int k = 0; k < LOG; ++k) if (diff & (1 << k)) a = up[k][a];
            if (a == b) return a;
            for (int k = LOG - 1; k >= 0; --k) {
                if (up[k][a] != up[k][b]) {
                    a = up[k][a];
                    b = up[k][b];
                }
            }
            return parent[a];
        };

        vector<int> ops;
        ops.reserve(n * 10); // rough reserve

        auto do_swap_edge = [&](int eid) {
            int a = edges[eid].first;
            int b = edges[eid].second;
            int valA = p[a], valB = p[b];
            p[a] = valB; p[b] = valA;
            pos[valA] = b; pos[valB] = a;
            ops.push_back(eid);
        };

        for (int i = 1; i <= n; ++i) {
            while (p[i] != i) {
                int src = pos[i];
                int L = lca(src, i);
                int cur = src;
                while (cur != L) {
                    int e = edgeFrom[cur];
                    do_swap_edge(e);
                    cur = parent[cur];
                }
                // Now i is at L
                vector<int> downEdges;
                int w = i;
                while (w != L) {
                    downEdges.push_back(edgeFrom[w]);
                    w = parent[w];
                }
                for (int idx = (int)downEdges.size() - 1; idx >= 0; --idx) {
                    do_swap_edge(downEdges[idx]);
                }
            }
        }

        cout << ops.size() << '\n';
        for (int e : ops) {
            cout << 1 << ' ' << e << '\n';
        }
    }
    return 0;
}