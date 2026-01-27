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
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    vector<pair<int, int>> verts;
    for (int i = 1; i <= N; i++) {
        verts.emplace_back(adj[i].size(), i);
    }
    sort(verts.begin(), verts.end());
    vector<bool> inIS(N + 1, false);
    for (auto& p : verts) {
        int v = p.second;
        bool can = true;
        for (int u : adj[v]) {
            if (inIS[u]) {
                can = false;
                break;
            }
        }
        if (can) {
            inIS[v] = true;
        }
    }
    for (int i = 1; i <= N; i++) {
        cout << (inIS[i] ? 1 : 0) << '\n';
    }
    return 0;
}