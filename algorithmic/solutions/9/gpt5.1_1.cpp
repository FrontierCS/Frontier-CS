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

        vector<vector<pair<int,int>>> adj(n + 1);
        vector<int> eu(n), ev(n); // 1..n-1
        for (int i = 1; i <= n - 1; ++i) {
            int u, v;
            cin >> u >> v;
            eu[i] = u;
            ev[i] = v;
            adj[u].push_back({v, i});
            adj[v].push_back({u, i});
        }

        // Root the tree at 1
        vector<int> parent(n + 1), parentEdge(n + 1), depth(n + 1);
        stack<int> st;
        parent[1] = 0;
        parentEdge[1] = 0;
        depth[1] = 0;
        st.push(1);
        while (!st.empty()) {
            int u = st.top();
            st.pop();
            for (auto &pr : adj[u]) {
                int v = pr.first, eidx = pr.second;
                if (v == parent[u]) continue;
                parent[v] = u;
                parentEdge[v] = eidx;
                depth[v] = depth[u] + 1;
                st.push(v);
            }
        }

        vector<int> ops;
        ops.reserve(2LL * n * n);

        auto getPathVertices = [&](int a, int b) {
            vector<int> up, down;
            int u = a, v = b;
            while (u != v) {
                if (depth[u] >= depth[v]) {
                    up.push_back(u);
                    u = parent[u];
                } else {
                    down.push_back(v);
                    v = parent[v];
                }
            }
            up.push_back(u); // LCA
            reverse(down.begin(), down.end());
            up.insert(up.end(), down.begin(), down.end());
            return up;
        };

        auto addTransposition = [&](int a, int b) {
            if (a == b) return;
            auto path = getPathVertices(a, b);
            int L = (int)path.size() - 1;
            if (L <= 0) return;
            vector<int> edges;
            edges.reserve(L);
            for (int i = 0; i < L; ++i) {
                int x = path[i], y = path[i + 1];
                int eidx;
                if (parent[x] == y) eidx = parentEdge[x];
                else eidx = parentEdge[y];
                edges.push_back(eidx);
            }
            for (int e : edges) ops.push_back(e);
            int sz = (int)edges.size();
            for (int i = sz - 2; i >= 0; --i) {
                ops.push_back(edges[i]);
            }
        };

        vector<int> seen(n + 1, 0);
        for (int i = 1; i <= n; ++i) {
            if (!seen[i]) {
                int cur = i;
                vector<int> cyc;
                while (!seen[cur]) {
                    seen[cur] = 1;
                    cyc.push_back(cur);
                    cur = p[cur];
                }
                if (cyc.size() <= 1) continue;
                int c1 = cyc[0];
                for (size_t j = 1; j < cyc.size(); ++j) {
                    int a = c1, b = cyc[j];
                    addTransposition(a, b);
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