#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N, M;
    if (!(cin >> N >> M)) return 0;
    
    vector<pair<int,int>> edges;
    edges.reserve(M);
    vector<vector<int>> adj(N+1);
    vector<int> deg(N+1, 0);
    
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        edges.emplace_back(u, v);
        adj[u].push_back(v);
        adj[v].push_back(u);
        deg[u]++; deg[v]++;
    }
    
    // Sort edges to favor covering with high-degree involvement first
    vector<int> order(M);
    iota(order.begin(), order.end(), 0);
    sort(order.begin(), order.end(), [&](int a, int b){
        auto [u1, v1] = edges[a];
        auto [u2, v2] = edges[b];
        int ka = deg[u1] + deg[v1];
        int kb = deg[u2] + deg[v2];
        if (ka != kb) return ka > kb;
        // tie-breakers to keep deterministic
        if (u1 != u2) return u1 < u2;
        return v1 < v2;
    });
    
    vector<char> matched(N+1, 0);
    vector<char> inCover(N+1, 0);
    
    // Build a maximal matching and take both endpoints into the cover
    for (int idx : order) {
        int u = edges[idx].first;
        int v = edges[idx].second;
        if (!matched[u] && !matched[v]) {
            matched[u] = matched[v] = 1;
            inCover[u] = inCover[v] = 1;
        }
    }
    
    // Reduction: remove vertices whose all neighbors are in the cover
    // Process vertices with smaller degree first to maximize removals
    vector<int> candidates;
    candidates.reserve(N);
    for (int v = 1; v <= N; ++v) if (inCover[v]) candidates.push_back(v);
    sort(candidates.begin(), candidates.end(), [&](int a, int b){
        if (deg[a] != deg[b]) return deg[a] < deg[b];
        return a < b;
    });
    
    for (int v : candidates) {
        if (!inCover[v]) continue;
        bool allNeighborsIn = true;
        for (int u : adj[v]) {
            if (!inCover[u]) { allNeighborsIn = false; break; }
        }
        if (allNeighborsIn) inCover[v] = 0;
    }
    
    for (int i = 1; i <= N; ++i) {
        cout << (inCover[i] ? 1 : 0) << '\n';
    }
    return 0;
}