#include <bits/stdc++.h>
using namespace std;

struct EdgeAdj {
    int to;
    long long w;
    int idx;
};

struct PQItem {
    long long w;
    int eidx;
    int to;
};

struct Comp {
    bool operator()(PQItem const& a, PQItem const& b) const {
        return a.w > b.w; // min-heap
    }
};

long long isqrt_floor(long long x) {
    long long r = (long long)std::sqrt((long double)x);
    if (r < 0) r = 0;
    while (r * r > x) --r;
    while ((r + 1) * (r + 1) <= x) ++r;
    return r;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M, K;
    if (!(cin >> N >> M >> K)) {
        return 0;
    }

    vector<long long> x(N + 1), y(N + 1);
    for (int i = 1; i <= N; ++i) {
        cin >> x[i] >> y[i];
    }

    vector<int> u(M + 1), v(M + 1);
    vector<long long> w(M + 1);
    vector<vector<EdgeAdj>> g(N + 1);
    for (int j = 1; j <= M; ++j) {
        cin >> u[j] >> v[j] >> w[j];
        g[u[j]].push_back({v[j], w[j], j});
        g[v[j]].push_back({u[j], w[j], j});
    }

    vector<long long> a(K + 1), b(K + 1);
    for (int k = 1; k <= K; ++k) {
        cin >> a[k] >> b[k];
    }

    // Build MST using Prim's algorithm starting from vertex 1
    vector<int> usedEdge(M + 1, 0);
    vector<char> vis(N + 1, 0);
    priority_queue<PQItem, vector<PQItem>, Comp> pq;

    vis[1] = 1;
    int visitedCnt = 1;
    for (const auto &e : g[1]) {
        pq.push({e.w, e.idx, e.to});
    }

    while (visitedCnt < N && !pq.empty()) {
        auto cur = pq.top();
        pq.pop();
        int vtx = cur.to;
        int eidx = cur.eidx;
        if (vis[vtx]) continue;
        vis[vtx] = 1;
        ++visitedCnt;
        usedEdge[eidx] = 1;
        for (const auto &e : g[vtx]) {
            if (!vis[e.to]) {
                pq.push({e.w, e.idx, e.to});
            }
        }
    }

    // Assign residents to nearest station and compute max squared distance per station
    vector<long long> maxd2(N + 1, 0);
    for (int k = 1; k <= K; ++k) {
        long long best_d2 = (long long)9e18;
        int best_i = 1;
        for (int i = 1; i <= N; ++i) {
            long long dx = a[k] - x[i];
            long long dy = b[k] - y[i];
            long long d2 = dx * dx + dy * dy;
            if (d2 < best_d2) {
                best_d2 = d2;
                best_i = i;
            }
        }
        if (best_d2 > maxd2[best_i]) {
            maxd2[best_i] = best_d2;
        }
    }

    // Compute P_i
    vector<int> P(N + 1, 0);
    for (int i = 1; i <= N; ++i) {
        if (maxd2[i] == 0) {
            P[i] = 0;
        } else {
            long long floor_r = isqrt_floor(maxd2[i]);
            long long rad = floor_r;
            if (rad * rad < maxd2[i]) ++rad; // ceil
            if (rad > 5000) rad = 5000;
            P[i] = (int)rad;
        }
    }

    // Output
    for (int i = 1; i <= N; ++i) {
        cout << P[i] << (i < N ? ' ' : '\n');
    }
    for (int j = 1; j <= M; ++j) {
        cout << usedEdge[j] << (j < M ? ' ' : '\n');
    }

    return 0;
}