#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N, M, K;
    if (!(cin >> N >> M >> K)) return 0;
    vector<long long> x(N+1), y(N+1);
    for (int i = 1; i <= N; ++i) cin >> x[i] >> y[i];
    struct Edge { int u, v; long long w; };
    vector<Edge> edges(M);
    vector<vector<tuple<int,long long,int>>> adj(N+1);
    for (int j = 0; j < M; ++j) {
        int u, v; long long w;
        cin >> u >> v >> w;
        edges[j] = {u, v, w};
        adj[u].push_back({v, w, j});
        adj[v].push_back({u, w, j});
    }
    vector<long long> a(K), b(K);
    for (int k = 0; k < K; ++k) cin >> a[k] >> b[k];

    // Assign residents to nearest station
    vector<int> P(N+1, 0);
    vector<long long> maxd2(N+1, 0);
    for (int k = 0; k < K; ++k) {
        int best = 1;
        long long bestd2 = (x[1]-a[k])*(x[1]-a[k]) + (y[1]-b[k])*(y[1]-b[k]);
        for (int i = 2; i <= N; ++i) {
            long long dx = x[i]-a[k], dy = y[i]-b[k];
            long long d2 = dx*dx + dy*dy;
            if (d2 < bestd2) {
                bestd2 = d2;
                best = i;
            }
        }
        if (bestd2 > maxd2[best]) maxd2[best] = bestd2;
    }
    for (int i = 1; i <= N; ++i) {
        long double r = sqrt((long double)maxd2[i]);
        long long ri = (long long)ceil(r);
        if (ri < 0) ri = 0;
        if (ri > 5000) ri = 5000;
        P[i] = (int)ri;
    }

    // Terminals: stations with P>0 plus node 1
    vector<char> is_terminal(N+1, 0);
    is_terminal[1] = 1;
    for (int i = 1; i <= N; ++i) if (P[i] > 0) is_terminal[i] = 1;

    // Dijkstra from node 1 to build shortest path tree
    const long long INF = (1LL<<62);
    vector<long long> dist(N+1, INF);
    vector<int> par(N+1, -1);      // parent node
    vector<int> paredge(N+1, -1);  // edge index used to reach node
    priority_queue<pair<long long,int>, vector<pair<long long,int>>, greater<pair<long long,int>>> pq;
    dist[1] = 0;
    pq.push({0,1});
    while (!pq.empty()) {
        auto [d,u] = pq.top(); pq.pop();
        if (d != dist[u]) continue;
        for (auto [v,w,ei] : adj[u]) {
            if (dist[v] > d + w) {
                dist[v] = d + w;
                par[v] = u;
                paredge[v] = ei;
                pq.push({dist[v], v});
            }
        }
    }

    // Mark edges used to connect all terminals via shortest path tree
    vector<int> B(M, 0);
    for (int i = 1; i <= N; ++i) {
        if (!is_terminal[i]) continue;
        int v = i;
        while (v != 1 && paredge[v] != -1) {
            int ei = paredge[v];
            B[ei] = 1;
            v = par[v];
        }
    }

    // Output
    for (int i = 1; i <= N; ++i) {
        if (i > 1) cout << ' ';
        cout << P[i];
    }
    cout << '\n';
    for (int j = 0; j < M; ++j) {
        if (j) cout << ' ';
        cout << B[j];
    }
    cout << '\n';
    return 0;
}