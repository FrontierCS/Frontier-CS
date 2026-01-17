#include <bits/stdc++.h>
using namespace std;

static uint64_t rng_state = 1469598103934665603ULL ^ (uint64_t)chrono::steady_clock::now().time_since_epoch().count();
inline uint64_t rng64() {
    rng_state ^= rng_state << 7;
    rng_state ^= rng_state >> 9;
    return rng_state;
}
inline int rnd3() { return (int)(rng64() % 3ULL); }
inline int rndInt(int a, int b) { return a + (int)(rng64() % (uint64_t)(b - a + 1)); }

struct Solver {
    int n;
    int m;
    vector<vector<int>> g;

    Solver(int n_, int m_, vector<vector<int>>&& g_) : n(n_), m(m_), g(move(g_)) {}

    pair<long long, vector<int>> local_descent(vector<int> col) {
        vector<array<int,3>> cnt(n);
        for (int u = 0; u < n; ++u) {
            cnt[u][0] = cnt[u][1] = cnt[u][2] = 0;
        }
        for (int u = 0; u < n; ++u) {
            int cu = col[u];
            for (int v: g[u]) {
                cnt[u][col[v]]++;
            }
        }
        long long b2 = 0;
        for (int u = 0; u < n; ++u) b2 += cnt[u][col[u]];
        long long b = b2 / 2;

        vector<int> q;
        q.reserve(n);
        vector<char> inQ(n, 0);
        for (int u = 0; u < n; ++u) {
            int cu = col[u];
            int a = cnt[u][0], bb = cnt[u][1], c = cnt[u][2];
            int bestVal = a, bestK = 0;
            if (bb < bestVal || (bb == bestVal && (rng64() & 1))) { bestVal = bb; bestK = 1; }
            if (c < bestVal || (c == bestVal && (rng64() & 1))) { bestVal = c; bestK = 2; }
            if (bestVal < cnt[u][cu]) {
                q.push_back(u);
                inQ[u] = 1;
            }
        }

        while (!q.empty()) {
            int u = q.back();
            q.pop_back();
            inQ[u] = 0;

            int cu = col[u];
            int bestK = 0, bestVal = cnt[u][0];
            int v1 = cnt[u][1], v2 = cnt[u][2];
            if (v1 < bestVal || (v1 == bestVal && (rng64() & 1))) { bestVal = v1; bestK = 1; }
            if (v2 < bestVal || (v2 == bestVal && (rng64() & 1))) { bestVal = v2; bestK = 2; }

            if (bestVal < cnt[u][cu]) {
                b += (long long)bestVal - (long long)cnt[u][cu];
                for (int v: g[u]) {
                    cnt[v][cu]--;
                    cnt[v][bestK]++;
                    int cv = col[v];
                    int mn = cnt[v][0];
                    if (cnt[v][1] < mn) mn = cnt[v][1];
                    if (cnt[v][2] < mn) mn = cnt[v][2];
                    if (mn < cnt[v][cv] && !inQ[v]) {
                        inQ[v] = 1;
                        q.push_back(v);
                    }
                }
                col[u] = bestK;
            }
        }
        return {b, move(col)};
    }

    vector<int> greedy_init() {
        vector<int> deg(n);
        for (int i = 0; i < n; ++i) deg[i] = (int)g[i].size();
        vector<int> order(n);
        iota(order.begin(), order.end(), 0);
        sort(order.begin(), order.end(), [&](int a, int b){ return deg[a] > deg[b]; });

        vector<int> col(n, -1);
        array<int,3> cnt;
        for (int u : order) {
            cnt = {0,0,0};
            for (int v : g[u]) {
                if (col[v] != -1) cnt[ col[v] ]++;
            }
            int bestK = 0, bestVal = cnt[0];
            if (cnt[1] < bestVal || (cnt[1] == bestVal && (rng64() & 1))) { bestVal = cnt[1]; bestK = 1; }
            if (cnt[2] < bestVal || (cnt[2] == bestVal && (rng64() & 1))) { bestVal = cnt[2]; bestK = 2; }
            col[u] = bestK;
        }
        return col;
    }

    vector<int> random_init() {
        vector<int> col(n);
        for (int i = 0; i < n; ++i) col[i] = rnd3();
        return col;
    }

    vector<int> solve() {
        vector<int> best_col(n, 0);
        long long best_b = (long long)m; // worst case all edges conflict impossible but safe upper bound
        // Initialization 1: Greedy degree-based
        {
            auto col0 = greedy_init();
            auto [b, col1] = local_descent(move(col0));
            if (b < best_b) {
                best_b = b;
                best_col = move(col1);
            }
        }
        // Initialization 2: Random
        {
            auto col0 = random_init();
            auto [b, col1] = local_descent(move(col0));
            if (b < best_b) {
                best_b = b;
                best_col = move(col1);
            }
        }
        // Optionally additional random starts (limited to 1 more for speed)
        if (m > 0 && n > 2000) {
            auto col0 = random_init();
            auto [b, col1] = local_descent(move(col0));
            if (b < best_b) {
                best_b = b;
                best_col = move(col1);
            }
        }
        return best_col;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m;
    if (!(cin >> n >> m)) return 0;
    vector<vector<int>> g(n);
    g.reserve(n);
    for (int i = 0; i < m; ++i) {
        int u,v; cin >> u >> v; --u; --v;
        g[u].push_back(v);
        g[v].push_back(u);
    }
    Solver solver(n, m, move(g));
    vector<int> ans = solver.solve();
    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << (ans[i] + 1);
    }
    cout << '\n';
    return 0;
}