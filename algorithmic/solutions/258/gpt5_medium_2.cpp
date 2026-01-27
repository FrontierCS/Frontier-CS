#include <bits/stdc++.h>
using namespace std;

pair<int,int> query(const vector<int>& nodes) {
    cout << "? " << nodes.size();
    for (int v : nodes) cout << " " << v;
    cout << endl;
    cout.flush();
    int x, d;
    if (!(cin >> x >> d)) exit(0);
    if (x == -1 && d == -1) exit(0);
    return {x, d};
}

vector<int> bfs(int n, const vector<vector<int>>& adj, int src) {
    const int INF = 1e9;
    vector<int> dist(n+1, INF);
    queue<int> q;
    dist[src] = 0;
    q.push(src);
    while (!q.empty()) {
        int u = q.front(); q.pop();
        for (int v : adj[u]) {
            if (dist[v] == INF) {
                dist[v] = dist[u] + 1;
                q.push(v);
            }
        }
    }
    return dist;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int t;
    if (!(cin >> t)) return 0;
    while (t--) {
        int n;
        cin >> n;
        vector<vector<int>> adj(n+1);
        for (int i = 0; i < n-1; ++i) {
            int u, v;
            cin >> u >> v;
            adj[u].push_back(v);
            adj[v].push_back(u);
        }
        vector<int> all(n);
        iota(all.begin(), all.end(), 1);
        auto first = query(all);
        int r = first.first;
        int D = first.second;

        vector<int> distR = bfs(n, adj, r);
        int maxDepth = 0;
        for (int i = 1; i <= n; ++i) maxDepth = max(maxDepth, distR[i]);

        vector<vector<int>> layers(maxDepth+1);
        for (int i = 1; i <= n; ++i) {
            layers[distR[i]].push_back(i);
        }

        int L = 0, R = maxDepth;
        while (L < R) {
            int mid = (L + R + 1) / 2;
            auto res = query(layers[mid]);
            if (res.second == D) L = mid;
            else R = mid - 1;
        }

        auto got = query(layers[L]);
        int endpoint1 = got.first;

        vector<int> distU = bfs(n, adj, endpoint1);
        vector<int> candidates;
        for (int i = 1; i <= n; ++i) if (distU[i] == D) candidates.push_back(i);

        auto got2 = query(candidates);
        int endpoint2 = got2.first;

        cout << "! " << endpoint1 << " " << endpoint2 << endl;
        cout.flush();
        string verdict;
        if (!(cin >> verdict)) return 0;
        if (verdict != "Correct") return 0;
    }
    return 0;
}