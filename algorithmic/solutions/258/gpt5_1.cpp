#include <bits/stdc++.h>
using namespace std;

pair<int, vector<int>> bfs(int n, const vector<vector<int>>& g, int s) {
    vector<int> dist(n + 1, -1), parent(n + 1, -1);
    queue<int> q;
    q.push(s);
    dist[s] = 0;
    while (!q.empty()) {
        int u = q.front(); q.pop();
        for (int v : g[u]) {
            if (dist[v] == -1) {
                dist[v] = dist[u] + 1;
                parent[v] = u;
                q.push(v);
            }
        }
    }
    int far = s;
    for (int i = 1; i <= n; ++i) {
        if (dist[i] > dist[far]) far = i;
    }
    return {far, dist};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int t;
    if (!(cin >> t)) return 0;
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
        int u = bfs(n, g, 1).first;
        int v = bfs(n, g, u).first;
        cout << u << " " << v << "\n";
    }
    return 0;
}