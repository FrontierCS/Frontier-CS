#include <bits/stdc++.h>
using namespace std;

pair<int,int> bfs_farthest(int start, const vector<vector<int>>& g) {
    int n = g.size() - 1;
    vector<int> dist(n + 1, -1);
    queue<int> q;
    dist[start] = 0;
    q.push(start);
    int far_node = start, far_dist = 0;
    while (!q.empty()) {
        int u = q.front(); q.pop();
        if (dist[u] > far_dist) {
            far_dist = dist[u];
            far_node = u;
        }
        for (int v : g[u]) {
            if (dist[v] == -1) {
                dist[v] = dist[u] + 1;
                q.push(v);
            }
        }
    }
    return {far_node, far_dist};
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
        int a = bfs_farthest(1, g).first;
        int b = bfs_farthest(a, g).first;
        cout << a << " " << b << "\n";
    }
    return 0;
}