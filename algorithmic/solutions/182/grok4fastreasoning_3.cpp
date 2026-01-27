#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    int N, M;
    cin >> N >> M;
    set<pair<int, int>> edge_set;
    for (int i = 0; i < M; i++) {
        int u, v;
        cin >> u >> v;
        if (u > v) swap(u, v);
        edge_set.insert({u, v});
    }
    vector<vector<int>> adj(N + 1);
    for (auto [u, v] : edge_set) {
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    vector<int> current_deg(N + 1);
    for (int i = 1; i <= N; i++) {
        current_deg[i] = adj[i].size();
    }
    set<pair<int, int>> pq;
    for (int i = 1; i <= N; i++) {
        if (current_deg[i] > 0) {
            pq.insert({-current_deg[i], i});
        }
    }
    vector<int> cover(N + 1, 0);
    vector<bool> selected(N + 1, false);
    while (!pq.empty()) {
        auto it = *pq.begin();
        pq.erase(pq.begin());
        int negd = it.first;
        int u = it.second;
        int d = -negd;
        if (selected[u] || current_deg[u] != d || d <= 0) continue;
        selected[u] = true;
        cover[u] = 1;
        for (int v : adj[u]) {
            if (!selected[v]) {
                current_deg[v]--;
                pq.insert({-current_deg[v], v});
            }
        }
        current_deg[u] = 0;
    }
    for (int i = 1; i <= N; i++) {
        cout << cover[i] << '\n';
    }
    return 0;
}