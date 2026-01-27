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
    vector<int> degree(N + 1, 0);
    for (int i = 1; i <= N; i++) {
        sort(adj[i].begin(), adj[i].end());
        auto it = unique(adj[i].begin(), adj[i].end());
        adj[i].erase(it, adj[i].end());
        degree[i] = adj[i].size();
    }
    vector<int> cur_deg = degree;
    vector<bool> active(N + 1, true);
    set<pair<int, int>> candidates;
    for (int i = 1; i <= N; i++) {
        if (cur_deg[i] > 0) {
            candidates.insert({-cur_deg[i], i});
        }
    }
    vector<int> selected(N + 1, 0);
    while (!candidates.empty()) {
        auto p = *candidates.begin();
        candidates.erase(candidates.begin());
        int negd = p.first;
        int u = p.second;
        if (!active[u] || cur_deg[u] != -negd) continue;
        selected[u] = 1;
        active[u] = false;
        for (int v : adj[u]) {
            if (active[v]) {
                candidates.erase({-cur_deg[v], v});
                cur_deg[v]--;
                if (cur_deg[v] > 0) {
                    candidates.insert({-cur_deg[v], v});
                }
            }
        }
    }
    for (int i = 1; i <= N; i++) {
        cout << selected[i] << '\n';
    }
    return 0;
}