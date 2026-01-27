#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int t;
    if(!(cin >> t)) return 0;
    while (t--) {
        int n;
        cin >> n;
        vector<vector<int>> g(n + 1);
        for (int i = 0; i < n - 1; ++i) {
            int u, v;
            cin >> u >> v;
            g[u].push_back(v);
            g[v].push_back(u);
        }
        auto bfs = [&](int src) {
            vector<int> dist(n + 1, -1), par(n + 1, -1);
            queue<int> q;
            q.push(src);
            dist[src] = 0;
            while (!q.empty()) {
                int u = q.front(); q.pop();
                for (int v : g[u]) {
                    if (dist[v] == -1) {
                        dist[v] = dist[u] + 1;
                        par[v] = u;
                        q.push(v);
                    }
                }
            }
            int far = src;
            for (int i = 1; i <= n; ++i) {
                if (dist[i] > dist[far]) far = i;
            }
            return tuple<int, vector<int>, vector<int>>(far, dist, par);
        };
        int u;
        vector<int> dist, par;
        tie(u, dist, par) = bfs(1);
        int v;
        tie(v, dist, par) = bfs(u);
        cout << u << " " << v << "\n";
    }
    return 0;
}