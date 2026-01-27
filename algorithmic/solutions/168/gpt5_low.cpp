#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N, M, H;
    if(!(cin >> N >> M >> H)) return 0;
    vector<int> A(N);
    for (int i = 0; i < N; ++i) cin >> A[i];
    vector<vector<int>> adj(N);
    vector<pair<int,int>> edges(M);
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        edges[i] = {u, v};
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    // Read coordinates (unused)
    for (int i = 0; i < N; ++i) {
        int x, y;
        cin >> x >> y;
    }

    vector<int> order(N);
    iota(order.begin(), order.end(), 0);
    sort(order.begin(), order.end(), [&](int i, int j){
        return A[i] > A[j];
    });

    vector<int> parent(N, -2);
    vector<int> depth(N, -1);
    queue<int> q;

    for (int s : order) {
        if (parent[s] != -2) continue;
        parent[s] = -1;
        depth[s] = 0;
        q.push(s);
        while (!q.empty()) {
            int v = q.front(); q.pop();
            if (depth[v] == H) continue;
            for (int u : adj[v]) {
                if (parent[u] == -2) {
                    parent[u] = v;
                    depth[u] = depth[v] + 1;
                    q.push(u);
                }
            }
        }
    }

    for (int i = 0; i < N; ++i) {
        if (i) cout << ' ';
        // Fallback: If any unassigned (shouldn't happen), make root
        if (parent[i] == -2) cout << -1;
        else cout << parent[i];
    }
    cout << '\n';
    return 0;
}