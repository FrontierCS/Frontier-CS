#include <bits/stdc++.h>
using namespace std;

const int MAXN = 4097;

int n;
vector<vector<int>> adj;
vector<bitset<MAXN>> edge;
vector<tuple<int, int, int>> ops;

bool check() {
    // Check if for all v<u, there is a path of length <=3
    for (int v = 0; v <= n; ++v) {
        // BFS from v limited to depth 3
        vector<bool> vis(n+1, false);
        queue<pair<int, int>> q;
        q.push({v, 0});
        vis[v] = true;
        while (!q.empty()) {
            auto [u, d] = q.front(); q.pop();
            if (d == 3) continue;
            for (int w : adj[u]) {
                if (!vis[w]) {
                    vis[w] = true;
                    q.push({w, d+1});
                }
            }
        }
        for (int u = v+1; u <= n; ++u) {
            if (!vis[u]) return false;
        }
    }
    return true;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    cin >> n;
    adj.resize(n+1);
    edge.resize(n+1);
    // initial edges: i -> i+1
    for (int i = 0; i < n; ++i) {
        adj[i].push_back(i+1);
        edge[i][i+1] = 1;
    }

    while (!check()) {
        int best_a = -1, best_b = -1, best_c = -1;
        int best_len = -1;
        // find candidate edge a->b with maximum b-a
        for (int a = 0; a <= n; ++a) {
            for (int c : adj[a]) {
                for (int b : adj[c]) {
                    if (b > a && !edge[a][b]) {
                        int len = b - a;
                        if (len > best_len) {
                            best_len = len;
                            best_a = a;
                            best_b = b;
                            best_c = c;
                        }
                    }
                }
            }
        }
        if (best_len == -1) break; // no candidate (should not happen)
        // add edge best_a -> best_b via best_c
        ops.push_back({best_a, best_c, best_b});
        adj[best_a].push_back(best_b);
        edge[best_a][best_b] = 1;
    }

    cout << ops.size() << '\n';
    for (auto [u, c, v] : ops) {
        cout << u << ' ' << c << ' ' << v << '\n';
    }
    return 0;
}