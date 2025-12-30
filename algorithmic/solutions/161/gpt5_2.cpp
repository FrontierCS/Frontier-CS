#include <bits/stdc++.h>
using namespace std;

static inline long long sqll(long long x) { return x * x; }

static inline long long isqrtll(long long n) {
    long double nd = (long double)n;
    long long x = (long long) sqrtl(nd);
    while ((x+1) * (x+1) <= n) ++x;
    while (x * x > n) --x;
    return x;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N, M, K;
    if (!(cin >> N >> M >> K)) return 0;
    
    vector<long long> x(N + 1), y(N + 1);
    for (int i = 1; i <= N; i++) cin >> x[i] >> y[i];
    
    vector<int> u(M), v(M);
    vector<long long> w(M);
    vector<vector<pair<int,int>>> g(N + 1); // (to, edge_index)
    for (int j = 0; j < M; j++) {
        cin >> u[j] >> v[j] >> w[j];
        g[u[j]].push_back({v[j], j});
        g[v[j]].push_back({u[j], j});
    }
    
    vector<long long> a(K), b(K);
    for (int k = 0; k < K; k++) cin >> a[k] >> b[k];
    
    vector<int> P(N + 1, 0);
    // Assign each resident to nearest station and compute required radius
    for (int k = 0; k < K; k++) {
        long long bestD2 = (1LL<<62);
        int bestIdx = 1;
        for (int i = 1; i <= N; i++) {
            long long dx = a[k] - x[i];
            long long dy = b[k] - y[i];
            long long d2 = dx*dx + dy*dy;
            if (d2 < bestD2) {
                bestD2 = d2;
                bestIdx = i;
            }
        }
        long long r = isqrtll(bestD2);
        int need = (r * r == bestD2) ? (int)r : (int)(r + 1);
        if (need > 5000) need = 5000;
        if (P[bestIdx] < need) P[bestIdx] = need;
    }
    
    // Dijkstra from node 1
    const long long INF = (1LL<<62);
    vector<long long> dist(N + 1, INF);
    vector<int> parent(N + 1, -1), parentEdge(N + 1, -1);
    priority_queue<pair<long long,int>, vector<pair<long long,int>>, greater<pair<long long,int>>> pq;
    dist[1] = 0;
    pq.push({0,1});
    while (!pq.empty()) {
        auto [d, u0] = pq.top(); pq.pop();
        if (d != dist[u0]) continue;
        for (auto [to, ei] : g[u0]) {
            long long nd = d + w[ei];
            if (nd < dist[to]) {
                dist[to] = nd;
                parent[to] = u0;
                parentEdge[to] = ei;
                pq.push({nd, to});
            }
        }
    }
    
    vector<int> B(M, 0);
    for (int i = 1; i <= N; i++) {
        if (P[i] > 0) {
            int cur = i;
            while (cur != 1 && parent[cur] != -1) {
                int pe = parentEdge[cur];
                if (pe >= 0) B[pe] = 1;
                cur = parent[cur];
            }
        }
    }
    
    // Output
    for (int i = 1; i <= N; i++) {
        if (i > 1) cout << ' ';
        cout << P[i];
    }
    cout << '\n';
    for (int j = 0; j < M; j++) {
        if (j > 0) cout << ' ';
        cout << B[j];
    }
    cout << '\n';
    return 0;
}