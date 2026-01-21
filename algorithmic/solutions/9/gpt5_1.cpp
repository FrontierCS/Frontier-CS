#include <bits/stdc++.h>
using namespace std;

struct Edge {
    int u, v;
};

int lca(int u, int v, const vector<int>& depth, const vector<vector<int>>& up, int LOG) {
    if (depth[u] < depth[v]) swap(u, v);
    int diff = depth[u] - depth[v];
    for (int k = 0; k < LOG; ++k) {
        if (diff & (1 << k)) u = up[k][u];
    }
    if (u == v) return u;
    for (int k = LOG - 1; k >= 0; --k) {
        if (up[k][u] != up[k][v]) {
            u = up[k][u];
            v = up[k][v];
        }
    }
    return up[0][u];
}

vector<int> getPathEdges(int u, int v, const vector<int>& parent, const vector<int>& epar, const vector<int>& depth, const vector<vector<int>>& up, int LOG) {
    int L = lca(u, v, depth, up, LOG);
    vector<int> upEdges, downEdges, pathEdges;
    int x = u;
    while (x != L) {
        upEdges.push_back(epar[x]);
        x = parent[x];
    }
    int y = v;
    while (y != L) {
        downEdges.push_back(epar[y]);
        y = parent[y];
    }
    pathEdges.reserve(upEdges.size() + downEdges.size());
    for (int id : upEdges) pathEdges.push_back(id);
    for (int i = (int)downEdges.size() - 1; i >= 0; --i) pathEdges.push_back(downEdges[i]);
    return pathEdges;
}

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
        vector<Edge> edges(n); // 1..n-1 used
        vector<vector<pair<int,int>>> adj(n + 1);
        for (int i = 1; i <= n - 1; ++i) {
            int u, v;
            cin >> u >> v;
            edges[i] = {u, v};
            adj[u].push_back({v, i});
            adj[v].push_back({u, i});
        }
        int root = 1;
        // Build parent, depth, epar, up table
        vector<int> parent(n + 1, 0), depth(n + 1, 0), epar(n + 1, 0);
        queue<int> q;
        q.push(root);
        parent[root] = 0;
        depth[root] = 0;
        epar[root] = 0;
        while (!q.empty()) {
            int u = q.front(); q.pop();
            for (auto [v, id] : adj[u]) {
                if (v == parent[u]) continue;
                parent[v] = u;
                depth[v] = depth[u] + 1;
                epar[v] = id;
                q.push(v);
            }
        }
        int LOG = 1;
        while ((1 << LOG) <= n) ++LOG;
        vector<vector<int>> up(LOG, vector<int>(n + 1, 0));
        for (int i = 1; i <= n; ++i) up[0][i] = parent[i];
        for (int k = 1; k < LOG; ++k) {
            for (int i = 1; i <= n; ++i) {
                up[k][i] = up[k - 1][ up[k - 1][i] ];
            }
        }
        // Initialize positions
        vector<int> valAt(n + 1), pos(n + 1);
        for (int i = 1; i <= n; ++i) {
            valAt[i] = p[i];
            pos[p[i]] = i;
        }
        // Active degrees and leaves
        vector<int> degActive(n + 1, 0);
        vector<char> active(n + 1, 1);
        for (int i = 1; i <= n; ++i) degActive[i] = (int)adj[i].size();
        queue<int> leaves;
        for (int i = 1; i <= n; ++i) {
            if (i != root && degActive[i] == 1) leaves.push(i);
        }
        vector<int> ans; ans.reserve(n * 4);
        while (!leaves.empty()) {
            int leaf = leaves.front(); leaves.pop();
            if (!active[leaf]) continue;
            if (leaf == root) continue;
            int start = pos[leaf];
            if (start != leaf) {
                vector<int> pathEdges = getPathEdges(start, leaf, parent, epar, depth, up, LOG);
                int cur = start;
                for (int ed : pathEdges) {
                    int a = edges[ed].u, b = edges[ed].v;
                    int nxt = (a == cur ? b : a);
                    // swap tokens at cur and nxt
                    int va = valAt[cur], vb = valAt[nxt];
                    pos[va] = nxt;
                    pos[vb] = cur;
                    valAt[cur] = vb;
                    valAt[nxt] = va;
                    ans.push_back(ed);
                    cur = nxt;
                }
            }
            // Now leaf token is in place
            active[leaf] = 0;
            for (auto [nei, id] : adj[leaf]) {
                if (active[nei]) {
                    degActive[nei]--;
                    if (nei != root && degActive[nei] == 1) leaves.push(nei);
                }
            }
        }
        // Output
        cout << ans.size() << '\n';
        for (int id : ans) {
            cout << 1 << ' ' << id << '\n';
        }
    }
    return 0;
}