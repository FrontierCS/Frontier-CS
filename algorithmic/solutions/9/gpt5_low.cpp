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
        vector<int> p(n + 1), inv(n + 1);
        for (int i = 1; i <= n; ++i) {
            cin >> p[i];
            inv[p[i]] = i;
        }
        vector<pair<int,int>> edges(n); // 1..n-1
        vector<vector<pair<int,int>>> adj(n + 1);
        for (int idx = 1; idx <= n - 1; ++idx) {
            int u, v;
            cin >> u >> v;
            edges[idx] = {u, v};
            adj[u].push_back({v, idx});
            adj[v].push_back({u, idx});
        }
        
        vector<int> ops; ops.reserve(2*n*n/n); // rough
        
        // For each vertex i, bring value i to vertex i
        for (int i = 1; i <= n; ++i) {
            while (p[i] != i) {
                int pos = inv[i]; // current vertex holding value i
                // BFS from pos to i to find path
                vector<int> par(n + 1, -1), pedge(n + 1, -1);
                queue<int> q;
                q.push(pos);
                par[pos] = 0;
                while (!q.empty() && par[i] == -1) {
                    int u = q.front(); q.pop();
                    for (auto [v, ei] : adj[u]) {
                        if (par[v] == -1) {
                            par[v] = u;
                            pedge[v] = ei;
                            q.push(v);
                            if (v == i) break;
                        }
                    }
                }
                // Reconstruct path edges from pos -> i
                vector<int> pathEdges;
                vector<int> pathVerts;
                int cur = i;
                while (cur != pos) {
                    pathEdges.push_back(pedge[cur]);
                    pathVerts.push_back(cur);
                    cur = par[cur];
                }
                pathVerts.push_back(pos);
                reverse(pathEdges.begin(), pathEdges.end());
                reverse(pathVerts.begin(), pathVerts.end());
                // Move value i along path: swap along edges in order
                for (size_t t = 0; t < pathEdges.size(); ++t) {
                    int u = pathVerts[t];
                    int v = pathVerts[t+1];
                    // swap p[u], p[v]
                    int pu = p[u], pv = p[v];
                    swap(p[u], p[v]);
                    inv[pu] = v;
                    inv[pv] = u;
                    ops.push_back(pathEdges[t]);
                }
                // now p[i]==i due to full path processed
            }
        }
        
        cout << ops.size() << "\n";
        for (int e : ops) {
            cout << 1 << " " << e << "\n";
        }
    }
    return 0;
}