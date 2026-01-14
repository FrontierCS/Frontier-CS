#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) return 0;
    vector<int> init(n), target(n);
    for (int i = 0; i < n; ++i) cin >> init[i];
    for (int i = 0; i < n; ++i) cin >> target[i];
    vector<vector<int>> g(n);
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        g[u].push_back(v);
        g[v].push_back(u);
    }
    
    auto bfs = [&](int col) {
        const int INF = 1e9;
        vector<int> dist(n, INF), par(n, -1);
        queue<int> q;
        for (int i = 0; i < n; ++i) {
            if (init[i] == col) {
                dist[i] = 0;
                par[i] = i;
                q.push(i);
            }
        }
        while (!q.empty()) {
            int u = q.front(); q.pop();
            for (int v : g[u]) {
                if (dist[v] == INF) {
                    dist[v] = dist[u] + 1;
                    par[v] = u;
                    q.push(v);
                }
            }
        }
        return pair<vector<int>, vector<int>>(dist, par);
    };
    
    auto [dist0, par0] = bfs(0);
    auto [dist1, par1] = bfs(1);
    
    vector<int> succ(n);
    int D = 0;
    const int INF = 1e9;
    for (int i = 0; i < n; ++i) {
        if (target[i] == 0) {
            if (dist0[i] == 0) succ[i] = i;
            else succ[i] = par0[i];
            D = max(D, dist0[i] >= INF ? 0 : dist0[i]);
        } else {
            if (dist1[i] == 0) succ[i] = i;
            else succ[i] = par1[i];
            D = max(D, dist1[i] >= INF ? 0 : dist1[i]);
        }
    }
    
    cout << D << "\n";
    vector<int> curr = init, next(n);
    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << curr[i];
    }
    cout << "\n";
    for (int t = 0; t < D; ++t) {
        for (int i = 0; i < n; ++i) next[i] = curr[succ[i]];
        for (int i = 0; i < n; ++i) {
            if (i) cout << ' ';
            cout << next[i];
        }
        cout << "\n";
        curr.swap(next);
    }
    return 0;
}