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
    for (int i = 1; i <= N; i++) {
        sort(adj[i].begin(), adj[i].end());
        auto it = unique(adj[i].begin(), adj[i].end());
        adj[i].erase(it, adj[i].end());
    }
    vector<int> active_deg(N + 1);
    vector<bool> is_active(N + 1, true);
    for (int i = 1; i <= N; i++) {
        active_deg[i] = adj[i].size();
    }
    vector<int> incover(N + 1, 0);
    while (true) {
        int max_d = 0;
        int best = -1;
        for (int i = 1; i <= N; i++) {
            if (is_active[i] && active_deg[i] > max_d) {
                max_d = active_deg[i];
                best = i;
            }
        }
        if (max_d == 0) break;
        incover[best] = 1;
        is_active[best] = false;
        for (int w : adj[best]) {
            if (is_active[w]) {
                active_deg[w]--;
            }
        }
    }
    for (int i = 1; i <= N; i++) {
        cout << incover[i] << '\n';
    }
    return 0;
}