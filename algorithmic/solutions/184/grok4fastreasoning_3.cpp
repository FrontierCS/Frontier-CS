#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    int N, M;
    cin >> N >> M;
    vector<vector<int>> adj(N + 1);
    for (int i = 0; i < M; i++) {
        int u, v;
        cin >> u >> v;
        if (u != v) {
            adj[u].push_back(v);
            adj[v].push_back(u);
        }
    }
    vector<int> deg(N + 1, 0);
    for (int i = 1; i <= N; i++) {
        sort(adj[i].begin(), adj[i].end());
        auto it = unique(adj[i].begin(), adj[i].end());
        adj[i].resize(it - adj[i].begin());
        deg[i] = adj[i].size();
    }
    vector<pair<int, int>> verts;
    for (int i = 1; i <= N; i++) {
        verts.emplace_back(deg[i], i);
    }
    sort(verts.begin(), verts.end());
    vector<bool> blocked(N + 1, false);
    vector<int> selection(N + 1, 0);
    for (auto& p : verts) {
        int u = p.second;
        if (!blocked[u]) {
            selection[u] = 1;
            for (int v : adj[u]) {
                blocked[v] = true;
            }
        }
    }
    for (int i = 1; i <= N; i++) {
        cout << selection[i] << '\n';
    }
    return 0;
}