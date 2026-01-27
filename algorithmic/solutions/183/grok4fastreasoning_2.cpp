#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    int N, M;
    cin >> N >> M;
    vector<vector<int>> adj(N + 1);
    vector<int> deg(N + 1, 0);
    for (int i = 0; i < M; i++) {
        int u, v;
        cin >> u >> v;
        if (u == v) continue;
        adj[u].push_back(v);
        adj[v].push_back(u);
        deg[u]++;
        deg[v]++;
    }
    vector<pair<int, int>> nodes;
    for (int i = 1; i <= N; i++) {
        nodes.emplace_back(deg[i], i);
    }
    sort(nodes.begin(), nodes.end());
    vector<bool> in_set(N + 1, false);
    for (auto& p : nodes) {
        int u = p.second;
        bool can = true;
        for (int v : adj[u]) {
            if (in_set[v]) {
                can = false;
                break;
            }
        }
        if (can) in_set[u] = true;
    }
    for (int i = 1; i <= N; i++) {
        cout << (in_set[i] ? 1 : 0) << '\n';
    }
    return 0;
}