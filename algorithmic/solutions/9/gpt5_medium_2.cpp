#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int T;
    if(!(cin >> T)) return 0;
    while (T--) {
        int n;
        cin >> n;
        vector<int> p(n+1);
        for (int i = 1; i <= n; ++i) cin >> p[i];
        vector<int> eu(n), ev(n);
        vector<vector<pair<int,int>>> adj(n+1);
        for (int i = 1; i <= n-1; ++i) {
            int u, v;
            cin >> u >> v;
            eu[i] = u; ev[i] = v;
            adj[u].push_back({v, i});
            adj[v].push_back({u, i});
        }
        // Root the tree at 1 and prepare LCA
        int LOG = 0;
        while ((1 << LOG) <= n) ++LOG;
        vector<vector<int>> up(LOG, vector<int>(n+1, 0));
        vector<int> depth(n+1, 0);
        vector<int> parentEdge(n+1, 0);
        vector<int> parent(n+1, 0);
        vector<int> vis(n+1, 0);
        // BFS/DFS
        stack<int> st;
        st.push(1);
        parent[1] = 0;
        vis[1] = 1;
        depth[1] = 0;
        while (!st.empty()) {
            int u = st.top(); st.pop();
            for (auto [v, id] : adj[u]) {
                if (!vis[v]) {
                    vis[v] = 1;
                    parent[v] = u;
                    parentEdge[v] = id;
                    depth[v] = depth[u] + 1;
                    st.push(v);
                }
            }
        }
        for (int i = 1; i <= n; ++i) up[0][i] = parent[i];
        for (int k = 1; k < LOG; ++k) {
            for (int i = 1; i <= n; ++i) {
                up[k][i] = up[k-1][i] ? up[k-1][ up[k-1][i] ] : 0;
            }
        }
        auto lca = [&](int a, int b) {
            if (depth[a] < depth[b]) swap(a,b);
            int diff = depth[a] - depth[b];
            for (int k = 0; k < LOG; ++k) if (diff & (1<<k)) a = up[k][a];
            if (a == b) return a;
            for (int k = LOG-1; k >= 0; --k) {
                if (up[k][a] != up[k][b]) {
                    a = up[k][a];
                    b = up[k][b];
                }
            }
            return parent[a];
        };
        auto pathEdges = [&](int a, int b, vector<int>& out) {
            out.clear();
            int L = lca(a,b);
            int x = a;
            while (x != L) {
                out.push_back(parentEdge[x]);
                x = parent[x];
            }
            vector<int> tmp;
            x = b;
            while (x != L) {
                tmp.push_back(parentEdge[x]);
                x = parent[x];
            }
            for (int i = (int)tmp.size()-1; i >= 0; --i) out.push_back(tmp[i]);
        };

        // posOfVal
        vector<int> pos(n+1, 0);
        for (int i = 1; i <= n; ++i) pos[p[i]] = i;

        // Active degrees and leaves
        vector<int> deg(n+1, 0);
        for (int i = 1; i <= n; ++i) deg[i] = (int)adj[i].size();
        vector<char> active(n+1, 1);
        deque<int> dq;
        for (int i = 1; i <= n; ++i) if (deg[i] <= 1) dq.push_back(i);

        vector<int> ops; ops.reserve(n * 100); // rough reserve

        auto do_swap_edge = [&](int eid) {
            int u = eu[eid], v = ev[eid];
            int valU = p[u], valV = p[v];
            swap(p[u], p[v]);
            pos[valU] = v;
            pos[valV] = u;
        };

        int activeCnt = n;
        vector<int> epath;
        while (activeCnt > 0) {
            while (!dq.empty() && (!active[dq.front()] || deg[dq.front()] > 1)) dq.pop_front();
            if (dq.empty()) {
                // In case, pick any active node
                int u = 1;
                while (u <= n && !active[u]) ++u;
                if (u > n) break;
                dq.push_back(u);
                continue;
            }
            int u = dq.front(); dq.pop_front();
            if (!active[u]) continue;
            // move value u to vertex u
            if (pos[u] != u) {
                pathEdges(pos[u], u, epath);
                for (int eid : epath) {
                    ops.push_back(eid);
                    do_swap_edge(eid);
                }
            }
            // remove u
            active[u] = 0;
            --activeCnt;
            for (auto [v, id] : adj[u]) {
                if (active[v]) {
                    deg[v]--;
                    if (deg[v] <= 1) dq.push_back(v);
                }
            }
        }

        // Output
        cout << (int)ops.size() << "\n";
        for (int eid : ops) {
            cout << 1 << " " << eid << "\n";
        }
    }
    return 0;
}