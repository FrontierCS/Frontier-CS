#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int t;
    if (!(cin >> t)) return 0;
    while (t--) {
        int n, m;
        cin >> n >> m;
        vector<pair<int,int>> edges(m+1);
        vector<vector<pair<int,int>>> adj(n+1);
        for (int i = 1; i <= m; ++i) {
            int a, b;
            cin >> a >> b;
            edges[i] = {a, b};
            adj[a].push_back({b, i});
            adj[b].push_back({a, i});
        }
        vector<int> chosen(m+1, 0);
        vector<int> vis(n+1, 0);
        queue<int> q;
        vis[1] = 1;
        q.push(1);
        while (!q.empty()) {
            int u = q.front(); q.pop();
            for (auto [v, id] : adj[u]) {
                if (!vis[v]) {
                    vis[v] = 1;
                    chosen[id] = 1;
                    q.push(v);
                }
            }
        }
        cout << "!";
        for (int i = 1; i <= m; ++i) {
            cout << " " << chosen[i];
        }
        cout << "\n";
        cout.flush();
    }
    return 0;
}