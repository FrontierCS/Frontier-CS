#include <bits/stdc++.h>
using namespace std;

static inline uint64_t splitmix64(uint64_t x) {
    x += 0x9e3779b97f4a7c15ULL;
    x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
    x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
    return x ^ (x >> 31);
}

struct Solver {
    int n;
    int m;
    vector<vector<int>> adj;
    mt19937 rng;

    Solver(int n_, int m_) : n(n_), m(m_), adj(n_ + 1) {
        uint64_t seed = chrono::steady_clock::now().time_since_epoch().count();
        seed = splitmix64(seed ^ (uint64_t)(uintptr_t)this);
        rng.seed((uint32_t)seed);
    }

    vector<int> greedyInit() {
        vector<int> order(n);
        iota(order.begin(), order.end(), 1);
        stable_sort(order.begin(), order.end(), [&](int a, int b) {
            return adj[a].size() > adj[b].size();
        });

        vector<int> col(n + 1, 0);
        array<int, 4> cntc{};
        for (int v : order) {
            cntc = {0, 0, 0, 0};
            for (int u : adj[v]) {
                int cu = col[u];
                if (cu) cntc[cu]++;
            }
            int best = 1;
            if (cntc[2] < cntc[best]) best = 2;
            if (cntc[3] < cntc[best]) best = 3;
            col[v] = best;
        }
        for (int v = 1; v <= n; v++) if (col[v] == 0) col[v] = 1;
        return col;
    }

    void buildCountsAndB(const vector<int>& col, vector<array<int,4>>& cnt, long long& b) {
        cnt.assign(n + 1, array<int,4>{0,0,0,0});
        for (int v = 1; v <= n; v++) {
            auto &cv = cnt[v];
            for (int u : adj[v]) cv[col[u]]++;
        }
        long long sum = 0;
        for (int v = 1; v <= n; v++) sum += cnt[v][col[v]];
        b = sum / 2;
    }

    inline void applyMove(int v, int nw, vector<int>& col, vector<array<int,4>>& cnt, long long& b) {
        int old = col[v];
        if (old == nw) return;
        b += (long long)cnt[v][nw] - (long long)cnt[v][old];
        col[v] = nw;
        for (int u : adj[v]) {
            cnt[u][old]--;
            cnt[u][nw]++;
        }
    }

    void localImprove(vector<int>& col, vector<array<int,4>>& cnt, long long& b, int passLimit) {
        vector<int> order(n);
        iota(order.begin(), order.end(), 1);
        for (int pass = 0; pass < passLimit; pass++) {
            shuffle(order.begin(), order.end(), rng);
            bool any = false;
            for (int v : order) {
                int old = col[v];
                int best = old;
                int bestDelta = 0;
                int d2 = cnt[v][2] - cnt[v][old];
                int d3 = cnt[v][3] - cnt[v][old];
                int d1 = cnt[v][1] - cnt[v][old];
                if (old != 1 && d1 < bestDelta) { bestDelta = d1; best = 1; }
                if (old != 2 && d2 < bestDelta) { bestDelta = d2; best = 2; }
                if (old != 3 && d3 < bestDelta) { bestDelta = d3; best = 3; }

                if (best != old) {
                    applyMove(v, best, col, cnt, b);
                    any = true;
                }
            }
            if (!any) break;
        }
    }

    void randomKick(vector<int>& col, vector<array<int,4>>& cnt, long long& b, int K) {
        uniform_int_distribution<int> distV(1, n);
        uniform_int_distribution<int> distC(1, 3);
        for (int i = 0; i < K; i++) {
            int v = distV(rng);
            int old = col[v];
            int nw = distC(rng);
            if (nw == old) nw = (nw % 3) + 1;
            applyMove(v, nw, col, cnt, b);
        }
    }

    vector<int> solve() {
        if (m == 0) {
            vector<int> col(n + 1, 1);
            return col;
        }

        int restarts, passLimit;
        if (m <= 100000) { restarts = 12; passLimit = 30; }
        else if (m <= 300000) { restarts = 9; passLimit = 25; }
        else { restarts = 7; passLimit = 20; }

        vector<int> bestCol(n + 1, 1);
        long long bestB = (1LL<<62);

        auto trySolution = [&](vector<int> col) {
            vector<array<int,4>> cnt;
            long long b = 0;
            buildCountsAndB(col, cnt, b);
            localImprove(col, cnt, b, passLimit);

            if (b < bestB) { bestB = b; bestCol = col; }

            int K = max(1, n / 25);
            for (int t = 0; t < 3; t++) {
                randomKick(col, cnt, b, K);
                localImprove(col, cnt, b, passLimit / 2 + 5);
                if (b < bestB) { bestB = b; bestCol = col; }
            }
        };

        trySolution(greedyInit());

        uniform_int_distribution<int> distC(1, 3);
        for (int r = 0; r < restarts; r++) {
            vector<int> col(n + 1);
            for (int v = 1; v <= n; v++) col[v] = distC(rng);
            trySolution(col);
        }

        return bestCol;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    Solver solver(n, m);
    solver.adj.assign(n + 1, {});
    solver.adj.shrink_to_fit();
    solver.adj.assign(n + 1, {});

    solver.adj.reserve(n + 1);

    for (int i = 0; i < m; i++) {
        int u, v;
        cin >> u >> v;
        solver.adj[u].push_back(v);
        solver.adj[v].push_back(u);
    }

    vector<int> col = solver.solve();
    for (int i = 1; i <= n; i++) {
        if (i > 1) cout << ' ';
        int c = col[i];
        if (c < 1 || c > 3) c = 1;
        cout << c;
    }
    cout << "\n";
    return 0;
}