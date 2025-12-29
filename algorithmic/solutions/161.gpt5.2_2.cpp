#include <bits/stdc++.h>
using namespace std;

struct Edge {
    int u, v;
    long long w;
};

static inline int isqrt_ceil_ll(long long s) {
    long long r = (long long)floor(sqrt((long double)s));
    while (r * r < s) ++r;
    while (r > 0 && (r - 1) * (r - 1) >= s) --r;
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
    vector<vector<pair<int,int>>> g(N); // (to, edgeIndex)
    for (int j = 0; j < M; j++) {
        int u, v;
        long long w;
        cin >> u >> v >> w;
        --u; --v;
        edges[j] = {u, v, w};
        g[u].push_back({v, j});
        g[v].push_back({u, j});
    }

    vector<int> a(K), b(K);
    for (int k = 0; k < K; k++) cin >> a[k] >> b[k];

    // Precompute resident->station ceil distances (capped at 5001).
    vector<uint16_t> distMat((size_t)K * (size_t)N);
    vector<int> minDist(K, 5001);
    for (int k = 0; k < K; k++) {
        int best = 5001;
        for (int i = 0; i < N; i++) {
            long long dx = (long long)a[k] - x[i];
            long long dy = (long long)b[k] - y[i];
            long long d2 = dx * dx + dy * dy;
            int d = isqrt_ceil_ll(d2);
            if (d > 5001) d = 5001;
            distMat[(size_t)k * (size_t)N + (size_t)i] = (uint16_t)d;
            best = min(best, d);
        }
        minDist[k] = best;
    }

    // All-pairs shortest paths by edge weights with parents for reconstruction.
    const long long INF = (1LL << 62);
    vector<vector<long long>> distW(N, vector<long long>(N, INF));
    vector<vector<int>> parentV(N, vector<int>(N, -1));
    vector<vector<int>> parentE(N, vector<int>(N, -1));

    for (int s = 0; s < N; s++) {
        vector<long long> dist(N, INF);
        vector<int> pv(N, -1), pe(N, -1);
        priority_queue<pair<long long,int>, vector<pair<long long,int>>, greater<pair<long long,int>>> pq;
        dist[s] = 0;
        pq.push({0, s});
        while (!pq.empty()) {
            auto [d, v] = pq.top(); pq.pop();
            if (d != dist[v]) continue;
            for (auto [to, ei] : g[v]) {
                long long nd = d + edges[ei].w;
                if (nd < dist[to]) {
                    dist[to] = nd;
                    pv[to] = v;
                    pe[to] = ei;
                    pq.push({nd, to});
                }
            }
        }
        distW[s] = std::move(dist);
        parentV[s] = std::move(pv);
        parentE[s] = std::move(pe);
    }

    auto build_used_edges_mst = [&](const vector<int>& terminals, vector<char>& used) -> long long {
        int T = (int)terminals.size();
        used.assign(M, 0);
        if (T <= 1) return 0;

        vector<long long> key(T, INF);
        vector<int> par(T, -1);
        vector<char> in(T, 0);
        key[0] = 0;

        for (int it = 0; it < T; it++) {
            int v = -1;
            long long best = INF;
            for (int i = 0; i < T; i++) {
                if (!in[i] && key[i] < best) {
                    best = key[i];
                    v = i;
                }
            }
            if (v < 0) break;
            in[v] = 1;
            int sv = terminals[v];
            for (int u = 0; u < T; u++) {
                if (in[u]) continue;
                int su = terminals[u];
                long long w = distW[sv][su];
                if (w < key[u]) {
                    key[u] = w;
                    par[u] = v;
                }
            }
        }

        auto mark_path = [&](int s, int t) {
            int cur = t;
            while (cur != s) {
                int e = parentE[s][cur];
                int p = parentV[s][cur];
                if (e < 0 || p < 0) break; // should not happen in connected graph
                used[e] = 1;
                cur = p;
            }
        };

        for (int i = 1; i < T; i++) {
            if (par[i] < 0) continue;
            int u = terminals[par[i]];
            int v = terminals[i];
            mark_path(u, v);
        }

        long long cost = 0;
        for (int e = 0; e < M; e++) if (used[e]) cost += edges[e].w;
        return cost;
    };

    mt19937 rng((uint32_t)chrono::steady_clock::now().time_since_epoch().count());

    auto solve_with_order = [&](vector<int> order, vector<int>& outP, vector<char>& outUsed, long long& outS) {
        vector<int> P(N, 0);
        for (int idx : order) {
            long long bestInc = INF;
            int bestI = -1;
            int bestD = 5002;
            const uint16_t* row = &distMat[(size_t)idx * (size_t)N];
            for (int i = 0; i < N; i++) {
                int d = (int)row[i];
                if (d > 5000) continue;
                int pi = P[i];
                long long inc;
                if (d <= pi) inc = 0;
                else inc = 1LL * d * d - 1LL * pi * pi;
                if (inc < bestInc || (inc == bestInc && d < bestD)) {
                    bestInc = inc;
                    bestI = i;
                    bestD = d;
                    if (bestInc == 0 && bestD == 0) break;
                }
            }
            if (bestI < 0) {
                // Should not happen; fall back to nearest (even if > 5000)
                int ni = 0, nd = (int)row[0];
                for (int i = 1; i < N; i++) {
                    int d = (int)row[i];
                    if (d < nd) { nd = d; ni = i; }
                }
                bestI = ni;
                bestD = min(nd, 5000);
            }
            P[bestI] = max(P[bestI], bestD);
        }

        long long sumP2 = 0;
        vector<int> terminals;
        terminals.reserve(N);
        terminals.push_back(0); // station 1 (0-index)
        for (int i = 1; i < N; i++) if (P[i] > 0) terminals.push_back(i);
        if (P[0] > 0) {
            // already included
        }

        vector<char> used;
        long long cable = build_used_edges_mst(terminals, used);
        for (int i = 0; i < N; i++) sumP2 += 1LL * P[i] * P[i];
        long long S = sumP2 + cable;

        outP = std::move(P);
        outUsed = std::move(used);
        outS = S;
    };

    vector<int> bestP(N, 0);
    vector<char> bestUsed(M, 0);
    long long bestS = INF;

    // Attempt 1: sort by decreasing minDist (hardest first)
    {
        vector<int> order(K);
        iota(order.begin(), order.end(), 0);
        stable_sort(order.begin(), order.end(), [&](int i, int j) {
            return minDist[i] > minDist[j];
        });
        vector<int> P;
        vector<char> used;
        long long S;
        solve_with_order(order, P, used, S);
        if (S < bestS) { bestS = S; bestP = std::move(P); bestUsed = std::move(used); }
    }

    // Attempt 2: sort by increasing minDist (easiest first)
    {
        vector<int> order(K);
        iota(order.begin(), order.end(), 0);
        stable_sort(order.begin(), order.end(), [&](int i, int j) {
            return minDist[i] < minDist[j];
        });
        vector<int> P;
        vector<char> used;
        long long S;
        solve_with_order(order, P, used, S);
        if (S < bestS) { bestS = S; bestP = std::move(P); bestUsed = std::move(used); }
    }

    // Random restarts
    int RESTARTS = 35;
    vector<int> baseOrder(K);
    iota(baseOrder.begin(), baseOrder.end(), 0);
    for (int t = 0; t < RESTARTS; t++) {
        auto order = baseOrder;
        shuffle(order.begin(), order.end(), rng);
        vector<int> P;
        vector<char> used;
        long long S;
        solve_with_order(order, P, used, S);
        if (S < bestS) { bestS = S; bestP = std::move(P); bestUsed = std::move(used); }
    }

    // Output
    for (int i = 0; i < N; i++) {
        if (i) cout << ' ';
        cout << bestP[i];
    }
    cout << "\n";
    for (int j = 0; j < M; j++) {
        if (j) cout << ' ';
        cout << (bestUsed[j] ? 1 : 0);
    }
    cout << "\n";

    return 0;
}