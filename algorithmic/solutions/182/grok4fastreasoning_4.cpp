#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N, M;
    cin >> N >> M;
    vector<vector<int>> adj(N + 1);
    for (int i = 0; i < M; i++) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    vector<int> deg(N + 1);
    for (int i = 1; i <= N; i++) {
        sort(adj[i].begin(), adj[i].end());
        auto it = unique(adj[i].begin(), adj[i].end());
        adj[i].erase(it, adj[i].end());
        deg[i] = adj[i].size();
    }
    vector<int> order(N);
    for (int i = 0; i < N; i++) {
        order[i] = i + 1;
    }
    sort(order.begin(), order.end(), [&](int a, int b) {
        if (deg[a] != deg[b]) return deg[a] > deg[b];
        return a < b;
    });
    vector<int> mate(N + 1, 0);
    for (int iu = 0; iu < N; iu++) {
        int u = order[iu];
        for (int v : adj[u]) {
            if (u < v) {
                if (mate[u] == 0 && mate[v] == 0) {
                    mate[u] = v;
                    mate[v] = u;
                }
            }
        }
    }
    for (int i = 1; i <= N; i++) {
        cout << (mate[i] != 0 ? 1 : 0) << '\n';
    }
    return 0;
}