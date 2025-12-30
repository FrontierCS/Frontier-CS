#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        int n;
        if (!(cin >> n)) break;

        vector<vector<int>> adj(n + 1);
        string tok;
        if (!(cin >> tok)) {
            // No more input; assume no edges.
        } else {
            bool isBinaryRow = (int)tok.size() == n;
            if (isBinaryRow) {
                for (char c : tok) {
                    if (c != '0' && c != '1') {
                        isBinaryRow = false;
                        break;
                    }
                }
            }
            if (isBinaryRow) {
                // Adjacency matrix, tok is first row
                vector<string> mat(n);
                mat[0] = tok;
                for (int i = 1; i < n; ++i) {
                    cin >> mat[i];
                }
                for (int i = 0; i < n; ++i) {
                    for (int j = 0; j < n; ++j) {
                        if (mat[i][j] == '1') {
                            int u = i + 1, v = j + 1;
                            if (u != v) {
                                adj[u].push_back(v);
                                adj[v].push_back(u);
                            }
                        }
                    }
                }
            } else {
                // Treat tok as m (number of edges), then read edge list
                int m = stoi(tok);
                for (int i = 0; i < m; ++i) {
                    int u, v;
                    cin >> u >> v;
                    if (1 <= u && u <= n && 1 <= v && v <= n && u != v) {
                        adj[u].push_back(v);
                        adj[v].push_back(u);
                    }
                }
            }
        }

        // BFS/DFS to check connectivity
        vector<int> vis(n + 1, 0);
        int cnt = 0;
        if (n >= 1) {
            queue<int> q;
            q.push(1);
            vis[1] = 1;
            while (!q.empty()) {
                int u = q.front(); q.pop();
                ++cnt;
                for (int v : adj[u]) {
                    if (!vis[v]) {
                        vis[v] = 1;
                        q.push(v);
                    }
                }
            }
        }

        int connected = (cnt == n ? 1 : 0);
        cout << "! " << connected << "\n";
        cout.flush();
    }
    return 0;
}