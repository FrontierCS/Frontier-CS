#include <bits/stdc++.h>
using namespace std;

struct Edge {
    int to;
    int id;
    long long w;
};

static inline int ceil_sqrt_ll(long long x) {
    long double s = sqrt((long double)x);
    long long r = (long long)floor(s);
    while (r * r < x) ++r;
    while ((r - 1) * (r - 1) >= x) --r;
    return (int)r;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N, M, K;
    if (!(cin >> N >> M >> K)) return 0;
    vector<long long> x(N), y(N);
    for (int i = 0; i < N; i++) cin >> x[i] >> y[i];
    vector<int> U(M), V(M);
    vector<long long> W(M);
    for (int j = 0; j < M; j++) {
        int u, v;
        long long w;
        cin >> u >> v >> w;
        --u; --v;
        U[j] = u; V[j] = v; W[j] = w;
    }
    vector<long long> a(K), b(K);
    for (int k = 0; k < K; k++) cin >> a[k] >> b[k];

    // Assign each resident to the nearest station
    vector<long long> maxds(N, -1);
    for (int k = 0; k < K; k++) {
        long long best = (1LL<<62);
        int besti = 0;
        for (int i = 0; i < N; i++) {
            long long dx = x[i] - a[k];
            long long dy = y[i] - b[k];
            long long ds = dx*dx + dy*dy;
            if (ds < best) {
                best = ds;
                besti = i;
            }
        }
        if (best > maxds[besti]) maxds[besti] = best;
    }

    // Set P_i for stations with assigned residents
    vector<int> P(N, 0);
    for (int i = 0; i < N; i++) {
        if (maxds[i] >= 0) {
            int r = ceil_sqrt_ll(maxds[i]);
            if (r > 5000) r = 5000;
            P[i] = r;
        } else {
            P[i] = 0;
        }
    }

    // Build graph
    vector<vector<Edge>> g(N);
    for (int j = 0; j < M; j++) {
        int u = U[j], v = V[j];
        long long w = W[j];
        g[u].push_back({v, j, w});
        g[v].push_back({u, j, w});
    }

    // Terminals: root (0) + stations with P[i]>0
    vector<int> terminals;
    terminals.push_back(0);
    for (int i = 1; i < N; i++) if (P[i] > 0) terminals.push_back(i);
    int T = (int)terminals.size();

    vector<vector<long long>> distT(T, vector<long long>(N, (long long)4e18));
    vector<vector<int>> prevV(T, vector<int>(N, -1));
    vector<vector<int>> prevE(T, vector<int>(N, -1));

    // Dijkstra from each terminal
    for (int ti = 0; ti < T; ti++) {
        int s = terminals[ti];
        auto &dist = distT[ti];
        auto &pv = prevV[ti];
        auto &pe = prevE[ti];
        dist[s] = 0;
        using PII = pair<long long,int>;
        priority_queue<PII, vector<PII>, greater<PII>> pq;
        pq.push({0, s});
        while (!pq.empty()) {
            auto [d,u] = pq.top(); pq.pop();
            if (d != dist[u]) continue;
            for (auto &e : g[u]) {
                int v = e.to;
                long long nd = d + e.w;
                if (nd < dist[v]) {
                    dist[v] = nd;
                    pv[v] = u;
                    pe[v] = e.id;
                    pq.push({nd, v});
                }
            }
        }
    }

    // Build complete graph of terminals with distances
    vector<vector<long long>> mat(T, vector<long long>(T, (long long)4e18));
    for (int i = 0; i < T; i++) {
        for (int j = 0; j < T; j++) {
            mat[i][j] = distT[i][terminals[j]];
        }
    }

    // MST on terminals using Prim
    vector<long long> key(T, (long long)4e18);
    vector<int> parentT(T, -1);
    vector<char> inMST(T, 0);
    key[0] = 0;
    for (int it = 0; it < T; it++) {
        int u = -1;
        long long best = (long long)4e18;
        for (int v = 0; v < T; v++) if (!inMST[v] && key[v] < best) {
            best = key[v];
            u = v;
        }
        if (u == -1) break;
        inMST[u] = 1;
        for (int v = 0; v < T; v++) if (!inMST[v]) {
            if (mat[u][v] < key[v]) {
                key[v] = mat[u][v];
                parentT[v] = u;
            }
        }
    }

    // Reconstruct paths and mark edges
    vector<int> B(M, 0);
    for (int v = 1; v < T; v++) {
        int u = parentT[v];
        if (u < 0) continue;
        int su = terminals[u];
        int sv = terminals[v];
        int cur = sv;
        // Use prev arrays from su
        int ti = u; // Dijkstra index from su
        while (cur != su) {
            int eid = prevE[ti][cur];
            if (eid < 0) break; // should not happen
            B[eid] = 1;
            cur = prevV[ti][cur];
        }
    }

    // Output
    for (int i = 0; i < N; i++) {
        if (i) cout << ' ';
        cout << P[i];
    }
    cout << '\n';
    for (int j = 0; j < M; j++) {
        if (j) cout << ' ';
        cout << (B[j] ? 1 : 0);
    }
    cout << '\n';
    return 0;
}