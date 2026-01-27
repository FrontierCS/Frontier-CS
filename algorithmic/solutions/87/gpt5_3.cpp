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
    vector<vector<int>> adj(n);
    for (int i = 0; i < m; ++i) {
        int u, v; cin >> u >> v;
        --u; --v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    const int INF = 1e9;

    auto bfs = [&](int color) {
        vector<int> dist(n, INF), parent(n, -1);
        queue<int> q;
        for (int i = 0; i < n; ++i) {
            if (init[i] == color) {
                dist[i] = 0;
                parent[i] = i;
                q.push(i);
            }
        }
        while (!q.empty()) {
            int u = q.front(); q.pop();
            for (int v : adj[u]) {
                if (dist[v] == INF) {
                    dist[v] = dist[u] + 1;
                    parent[v] = u;
                    q.push(v);
                }
            }
        }
        return pair<vector<int>, vector<int>>(dist, parent);
    };

    auto [dist0, parent0] = bfs(0);
    auto [dist1, parent1] = bfs(1);

    vector<int> distFinal(n);
    int K = 0;
    for (int i = 0; i < n; ++i) {
        if (target[i] == 0) distFinal[i] = dist0[i];
        else distFinal[i] = dist1[i];
        // Problem guarantees a solution exists, so distFinal[i] should not be INF
        if (distFinal[i] > K) K = distFinal[i];
    }

    auto ancestor = [&](int v, int steps, int color) {
        if (steps <= 0) return v;
        if (color == 0) {
            int u = v;
            for (int i = 0; i < steps; ++i) u = parent0[u];
            return u;
        } else {
            int u = v;
            for (int i = 0; i < steps; ++i) u = parent1[u];
            return u;
        }
    };

    cout << K << "\n";
    for (int t = 0; t <= K; ++t) {
        for (int i = 0; i < n; ++i) {
            int c = target[i];
            int d = distFinal[i];
            int steps = t < d ? t : d;
            int w = ancestor(i, steps, c);
            int val = init[w];
            cout << val << (i + 1 == n ? '\n' : ' ');
        }
    }

    return 0;
}