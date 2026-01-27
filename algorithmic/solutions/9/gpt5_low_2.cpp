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

        vector<vector<pair<int,int>>> adj(n+1);
        unordered_map<long long,int> edgeId;
        edgeId.reserve(2*(n-1));
        edgeId.max_load_factor(0.7f);

        for (int i = 1; i <= n-1; ++i) {
            int u, v;
            cin >> u >> v;
            adj[u].push_back({v,i});
            adj[v].push_back({u,i});
            int a = min(u,v), b = max(u,v);
            long long key = 1LL * a * (n + 1) + b;
            edgeId[key] = i;
        }

        int LOG = 1;
        while ((1<<LOG) <= n) ++LOG;
        vector<int> depth(n+1, 0), parent(n+1, 0);
        vector<vector<int>> up(LOG, vector<int>(n+1, 0));

        // BFS to set parent and depth
        queue<int> q;
        parent[1] = 0;
        depth[1] = 0;
        q.push(1);
        vector<int> vis(n+1,0);
        vis[1]=1;
        while(!q.empty()){
            int u = q.front(); q.pop();
            for(auto [v, id] : adj[u]){
                if(!vis[v]){
                    vis[v]=1;
                    parent[v]=u;
                    depth[v]=depth[u]+1;
                    q.push(v);
                }
            }
        }
        for (int v = 1; v <= n; ++v) up[0][v] = parent[v] ? parent[v] : 0;
        for (int k = 1; k < LOG; ++k) {
            for (int v = 1; v <= n; ++v) {
                int mid = up[k-1][v];
                up[k][v] = mid ? up[k-1][mid] : 0;
            }
        }

        auto lift = [&](int v, int k){
            for (int i = 0; i < LOG && v; ++i) {
                if (k & (1<<i)) v = up[i][v];
            }
            return v;
        };
        function<int(int,int)> lca = [&](int a, int b){
            if (depth[a] < depth[b]) swap(a,b);
            a = lift(a, depth[a]-depth[b]);
            if (a == b) return a;
            for (int k = LOG-1; k >= 0; --k) {
                if (up[k][a] != up[k][b]) {
                    a = up[k][a];
                    b = up[k][b];
                }
            }
            return parent[a];
        };

        vector<int> posOf(n+1);
        for (int v = 1; v <= n; ++v) posOf[p[v]] = v;

        vector<int> ops;
        ops.reserve(n*n);

        for (int val = 1; val <= n; ++val) {
            while (posOf[val] != val) {
                int u = posOf[val];
                int v = val;
                int w = lca(u, v);
                int nxt;
                if (u != w) {
                    nxt = parent[u];
                } else {
                    int diff = depth[v] - depth[w] - 1;
                    int child = lift(v, diff);
                    nxt = child;
                }
                int a = min(u, nxt), b = max(u, nxt);
                long long key = 1LL * a * (n + 1) + b;
                int eid = edgeId[key];
                // perform swap on edge (u, nxt)
                int val_u = p[u];
                int val_v = p[nxt];
                swap(p[u], p[nxt]);
                posOf[val_u] = nxt;
                posOf[val_v] = u;
                ops.push_back(eid);
            }
        }

        cout << (int)ops.size() << "\n";
        for (int id : ops) {
            cout << 1 << " " << id << "\n";
        }
    }
    return 0;
}