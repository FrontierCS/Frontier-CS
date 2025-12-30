#include <bits/stdc++.h>
using namespace std;

struct Edge {
    int u, v;
    long long w;
};

static inline long long sqr(long long x) { return x * x; }

static int ceil_sqrt_ll(long long x) {
    if (x <= 0) return 0;
    long long r = (long long)floor(sqrt((long double)x));
    while (r * r < x) ++r;
    while ((r - 1) >= 0 && (r - 1) * (r - 1) >= x) --r;
    if (r > 5000) r = 5000;
    return (int)r;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M, K;
    cin >> N >> M >> K;

    vector<int> x(N), y(N);
    for (int i = 0; i < N; i++) cin >> x[i] >> y[i];

    vector<Edge> edges(M);
    vector<vector<tuple<int,long long,int>>> g(N);
    for (int j = 0; j < M; j++) {
        int u, v;
        long long w;
        cin >> u >> v >> w;
        --u; --v;
        edges[j] = {u, v, w};
        g[u].push_back({v, w, j});
        g[v].push_back({u, w, j});
    }

    vector<int> a(K), b(K);
    for (int k = 0; k < K; k++) cin >> a[k] >> b[k];

    // Assign each resident to the nearest station
    vector<long long> maxDist2(N, 0);
    for (int k = 0; k < K; k++) {
        int best = 0;
        long long bestd2 = (1LL<<62);
        for (int i = 0; i < N; i++) {
            long long dx = (long long)x[i] - a[k];
            long long dy = (long long)y[i] - b[k];
            long long d2 = dx*dx + dy*dy;
            if (d2 < bestd2) {
                bestd2 = d2;
                best = i;
            }
        }
        if (bestd2 > maxDist2[best]) maxDist2[best] = bestd2;
    }

    vector<int> P(N, 0);
    for (int i = 0; i < N; i++) {
        if (maxDist2[i] > 0) P[i] = ceil_sqrt_ll(maxDist2[i]);
    }

    // Dijkstra from station 1 (index 0) to build a shortest path tree
    const long long INF = (1LL<<62);
    vector<long long> dist(N, INF);
    vector<int> parentV(N, -1), parentE(N, -1);

    priority_queue<pair<long long,int>, vector<pair<long long,int>>, greater<pair<long long,int>>> pq;
    dist[0] = 0;
    pq.push({0, 0});
    while (!pq.empty()) {
        auto [d, v] = pq.top();
        pq.pop();
        if (d != dist[v]) continue;
        for (auto &[to, w, idx] : g[v]) {
            long long nd = d + w;
            if (nd < dist[to]) {
                dist[to] = nd;
                parentV[to] = v;
                parentE[to] = idx;
                pq.push({nd, to});
            }
        }
    }

    // Turn ON edges needed to connect all stations with P_i > 0 to station 1
    vector<int> B(M, 0);
    vector<char> needV(N, 0);
    needV[0] = 1;
    for (int i = 0; i < N; i++) if (P[i] > 0) needV[i] = 1;

    for (int i = 0; i < N; i++) {
        if (!needV[i]) continue;
        int v = i;
        while (v != 0 && parentV[v] != -1) {
            int eidx = parentE[v];
            if (eidx >= 0) B[eidx] = 1;
            v = parentV[v];
        }
    }

    for (int i = 0; i < N; i++) {
        if (i) cout << ' ';
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