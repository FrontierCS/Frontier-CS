#include <bits/stdc++.h>
using namespace std;

struct Edge {
    int u, v;
    long long w;
};

static inline int ceil_sqrt_ll(long long x) {
    if (x <= 0) return 0;
    long long r = (long long)floor(sqrt((long double)x));
    while (r * r < x) ++r;
    while ((r - 1) >= 0 && (r - 1) * (r - 1) >= x) --r;
    return (int)r;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M, K;
    cin >> N >> M >> K;

    vector<int> x(N + 1), y(N + 1);
    for (int i = 1; i <= N; i++) cin >> x[i] >> y[i];

    vector<Edge> edges(M);
    vector<vector<pair<int,int>>> g(N + 1); // (to, edge_id)
    for (int j = 0; j < M; j++) {
        int u, v;
        long long w;
        cin >> u >> v >> w;
        edges[j] = {u, v, w};
        g[u].push_back({v, j});
        g[v].push_back({u, j});
    }

    vector<int> a(K), b(K);
    for (int k = 0; k < K; k++) cin >> a[k] >> b[k];

    // Assign each resident to the nearest station and set required radius.
    vector<int> P(N + 1, 0);
    for (int k = 0; k < K; k++) {
        int best_i = 1;
        long long best_d2 = (long long)(x[1] - a[k]) * (x[1] - a[k]) + (long long)(y[1] - b[k]) * (y[1] - b[k]);
        for (int i = 2; i <= N; i++) {
            long long dx = (long long)x[i] - a[k];
            long long dy = (long long)y[i] - b[k];
            long long d2 = dx * dx + dy * dy;
            if (d2 < best_d2 || (d2 == best_d2 && i < best_i)) {
                best_d2 = d2;
                best_i = i;
            }
        }
        int r = ceil_sqrt_ll(best_d2);
        if (r > 5000) r = 5000; // safety
        P[best_i] = max(P[best_i], r);
    }

    // Dijkstra from node 1 to get a shortest path tree.
    const long long INF = (1LL << 62);
    vector<long long> dist(N + 1, INF);
    vector<int> parentV(N + 1, -1), parentE(N + 1, -1);
    priority_queue<pair<long long,int>, vector<pair<long long,int>>, greater<pair<long long,int>>> pq;

    dist[1] = 0;
    pq.push({0, 1});

    while (!pq.empty()) {
        auto [d, v] = pq.top();
        pq.pop();
        if (d != dist[v]) continue;
        for (auto [to, eid] : g[v]) {
            long long nd = d + edges[eid].w;
            if (nd < dist[to]) {
                dist[to] = nd;
                parentV[to] = v;
                parentE[to] = eid;
                pq.push({nd, to});
            }
        }
    }

    vector<int> B(M, 0);
    vector<char> used(N + 1, 0);
    used[1] = 1;
    for (int i = 1; i <= N; i++) if (P[i] > 0) used[i] = 1;

    // Mark edges along shortest paths from each used node to 1.
    for (int i = 1; i <= N; i++) {
        if (!used[i] || i == 1) continue;
        int cur = i;
        while (cur != 1) {
            int pe = parentE[cur];
            int pv = parentV[cur];
            if (pe < 0 || pv < 0) break; // should not happen in connected graph
            B[pe] = 1;
            cur = pv;
        }
    }

    // Output
    for (int i = 1; i <= N; i++) {
        if (i > 1) cout << ' ';
        cout << P[i];
    }
    cout << "\n";
    for (int j = 0; j < M; j++) {
        if (j) cout << ' ';
        cout << B[j];
    }
    cout << "\n";

    return 0;
}