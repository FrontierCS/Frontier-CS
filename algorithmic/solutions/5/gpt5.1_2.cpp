#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    vector<int> a(10);
    for (int i = 0; i < 10; ++i) cin >> a[i];

    vector<vector<int>> adj(n + 1);
    vector<int> indeg(n + 1, 0), outdeg(n + 1, 0);

    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        if (u < 1 || u > n || v < 1 || v > n) continue; // safety
        adj[u].push_back(v);
        ++outdeg[u];
        ++indeg[v];
    }

    // Choose start vertex as one with minimal in-degree
    int start = 1;
    for (int i = 2; i <= n; ++i) {
        if (indeg[i] < indeg[start]) start = i;
    }

    vector<char> visited(n + 1, 0);
    vector<int> path;
    path.reserve(n);

    int cur = start;
    visited[cur] = 1;
    path.push_back(cur);

    while (true) {
        int bestScore = -1;
        int nxt = -1;
        for (int to : adj[cur]) {
            if (!visited[to]) {
                int score = outdeg[to];
                if (score > bestScore) {
                    bestScore = score;
                    nxt = to;
                }
            }
        }
        if (nxt == -1) break;
        cur = nxt;
        visited[cur] = 1;
        path.push_back(cur);
    }

    cout << path.size() << '\n';
    for (size_t i = 0; i < path.size(); ++i) {
        if (i) cout << ' ';
        cout << path[i];
    }
    cout << '\n';

    return 0;
}