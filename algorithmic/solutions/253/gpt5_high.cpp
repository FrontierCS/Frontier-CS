#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int t;
    if (!(cin >> t)) return 0;
    for (int tc = 0; tc < t; ++tc) {
        int n, m;
        if (tc == 0) {
            if (!(cin >> n >> m)) return 0;
        } else {
            // Skip any stray 0/1 tokens (possible interactive responses)
            do {
                if (!(cin >> n)) return 0;
            } while (n < 2);
            if (!(cin >> m)) return 0;
        }

        vector<pair<int,int>> edges(m);
        vector<vector<pair<int,int>>> adj(n + 1);
        for (int i = 0; i < m; ++i) {
            int a, b;
            cin >> a >> b;
            edges[i] = {a, b};
            adj[a].push_back({b, i});
            adj[b].push_back({a, i});
        }

        vector<int> ans(m, 0);
        vector<int> vis(n + 1, 0);
        queue<int> q;
        for (int s = 1; s <= n; ++s) {
            if (!vis[s]) {
                vis[s] = 1;
                q.push(s);
                while (!q.empty()) {
                    int u = q.front(); q.pop();
                    for (auto &e : adj[u]) {
                        int v = e.first, idx = e.second;
                        if (!vis[v]) {
                            vis[v] = 1;
                            ans[idx] = 1;
                            q.push(v);
                        }
                    }
                }
            }
        }

        cout << "!";
        for (int i = 0; i < m; ++i) {
            cout << " " << ans[i];
        }
        cout << "\n";
    }
    return 0;
}