#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N, M, H;
    if (!(cin >> N >> M >> H)) return 0;
    vector<int> A(N);
    for (int i = 0; i < N; i++) cin >> A[i];
    
    vector<vector<int>> g(N);
    for (int i = 0; i < M; i++) {
        int u, v;
        cin >> u >> v;
        g[u].push_back(v);
        g[v].push_back(u);
    }
    // Read coordinates (unused)
    for (int i = 0; i < N; i++) {
        int x, y;
        cin >> x >> y;
    }
    
    int P = H + 1;
    vector<int> dist(N), parent(N);
    long long bestScore = -1;
    int bestRoot = 0;
    
    vector<int> q;
    q.reserve(N);
    
    // Try all vertices as root and pick the best based on sum A[v] * (dist % (H+1))
    for (int root = 0; root < N; root++) {
        fill(dist.begin(), dist.end(), -1);
        q.clear();
        dist[root] = 0;
        q.push_back(root);
        for (size_t head = 0; head < q.size(); head++) {
            int u = q[head];
            for (int v : g[u]) {
                if (dist[v] == -1) {
                    dist[v] = dist[u] + 1;
                    q.push_back(v);
                }
            }
        }
        long long score = 0;
        for (int v = 0; v < N; v++) {
            score += 1LL * A[v] * (dist[v] % P);
        }
        if (score > bestScore) {
            bestScore = score;
            bestRoot = root;
        }
    }
    
    // BFS from best root to get parents and distances
    fill(dist.begin(), dist.end(), -1);
    fill(parent.begin(), parent.end(), -2);
    q.clear();
    dist[bestRoot] = 0;
    parent[bestRoot] = -1;
    q.push_back(bestRoot);
    for (size_t head = 0; head < q.size(); head++) {
        int u = q[head];
        for (int v : g[u]) {
            if (dist[v] == -1) {
                dist[v] = dist[u] + 1;
                parent[v] = u;
                q.push_back(v);
            }
        }
    }
    
    // Build final parent array with cuts every (H+1) levels
    vector<int> par(N, -1);
    for (int v = 0; v < N; v++) {
        if (dist[v] % P == 0) {
            par[v] = -1;
        } else {
            if (parent[v] >= 0) par[v] = parent[v];
            else par[v] = -1; // Fallback, though graph is connected
        }
    }
    
    for (int i = 0; i < N; i++) {
        if (i) cout << ' ';
        cout << par[i];
    }
    cout << '\n';
    
    return 0;
}