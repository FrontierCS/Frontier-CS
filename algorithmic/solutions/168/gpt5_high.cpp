#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N, M, H;
    if (!(cin >> N >> M >> H)) return 0;
    vector<int> A(N);
    for (int i = 0; i < N; i++) cin >> A[i];
    vector<vector<int>> adj(N);
    for (int i = 0; i < M; i++) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    // Read coordinates (unused)
    for (int i = 0; i < N; i++) {
        int x, y;
        cin >> x >> y;
    }

    vector<int> par(N, -1);
    vector<char> vis(N, 0);

    vector<int> order(N);
    iota(order.begin(), order.end(), 0);
    sort(order.begin(), order.end(), [&](int a, int b){
        if (A[a] != A[b]) return A[a] < A[b];
        if (adj[a].size() != adj[b].size()) return adj[a].size() > adj[b].size();
        return a < b;
    });

    for (int s : order) {
        if (vis[s]) continue;
        vis[s] = 1;
        par[s] = -1;
        int u = s;
        int depth = 0;
        while (depth < H) {
            int best = -1;
            int bestDeg2 = -1;
            int bestA = INT_MAX;
            for (int v : adj[u]) {
                if (vis[v]) continue;
                int deg2 = 0;
                for (int w : adj[v]) {
                    if (w == u) continue;
                    if (!vis[w]) deg2++;
                }
                if (deg2 > bestDeg2 || (deg2 == bestDeg2 && (A[v] < bestA || (A[v] == bestA && v < best)))) {
                    bestDeg2 = deg2;
                    bestA = A[v];
                    best = v;
                }
            }
            if (best == -1) break;
            par[best] = u;
            vis[best] = 1;
            u = best;
            depth++;
        }
    }

    for (int i = 0; i < N; i++) {
        if (i) cout << ' ';
        cout << par[i];
    }
    cout << '\n';
    return 0;
}