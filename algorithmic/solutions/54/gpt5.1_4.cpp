#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    vector<vector<int>> adj(n + 1);
    for (int i = 0; i < n - 1; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    vector<int> sz(n + 1);
    int centroid = 1;
    int bestVal = n + 1;

    function<void(int,int)> dfs = [&](int u, int p) {
        sz[u] = 1;
        int maxSub = 0;
        for (int v : adj[u]) {
            if (v == p) continue;
            dfs(v, u);
            sz[u] += sz[v];
            maxSub = max(maxSub, sz[v]);
        }
        maxSub = max(maxSub, n - sz[u]);
        if (maxSub < bestVal) {
            bestVal = maxSub;
            centroid = u;
        }
    };

    dfs(1, 0);
    cout << centroid << '\n';
    return 0;
}