#include <bits/stdc++.h>
using namespace std;

static inline double now_sec() {
    using namespace std::chrono;
    return duration<double>(steady_clock::now().time_since_epoch()).count();
}

struct Solver {
    int n;
    int m;
    vector<int> deg;
    vector<int> eu, ev;
    vector<vector<int>> adj;

    mt19937 rng;

    Solver(int n_, int m_) : n(n_), m(m_), deg(n + 1, 0), adj(n + 1) {
        uint64_t seed = (uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count();
        seed ^= (uint64_t)(uintptr_t)this + 0x9e3779b97f4a7c15ULL;
        rng.seed((uint32_t)(seed ^ (seed >> 32)));
    }

    vector<int> init_dsatur() {
        vector<int> col(n + 1, 0);
        vector<int> mask(n + 1, 0);

        for (int it = 1; it <= n; it++) {
            int best = -1;
            int bestSat = -1;
            int bestDeg = -1;

            for (int v = 1; v <= n; v++) if (col[v] == 0) {
                int s = __builtin_popcount((unsigned)mask[v]);
                if (s > bestSat || (s == bestSat && deg[v] > bestDeg)) {
                    best = v;
                    bestSat = s;
                    bestDeg = deg[v];
                } else if (s == bestSat && deg[v] == bestDeg && best != -1) {
                    if ((rng() & 1) == 0) best = v;
                }
            }

            int cnt[4] = {0, 0, 0, 0};
            for (int u : adj[best]) if (col[u] != 0) cnt[col[u]]++;

            int minConf = INT_MAX;
            int cand[3], csz = 0;
            for (int c = 1; c <= 3; c++) {
                if (cnt[c] < minConf) {
                    minConf = cnt[c];
                    cand[0] = c;
                    csz = 1;
                } else if (cnt[c] == minConf) {
                    cand[csz++] = c;
                }
            }
            int chosen = cand[uniform_int_distribution<int>(0, csz - 1)(rng)];
            col[best] = chosen;

            for (int u : adj[best]) if (col[u] == 0) mask[u] |= (1 << chosen);
        }

        for (int v = 1; v <= n; v++) if (col[v] == 0) col[v] = (int)(rng() % 3) + 1;
        return col;
    }

    vector<int> init_random() {
        vector<int> col(n + 1);
        for (int v = 1; v <= n; v++) col[v] = (int)(rng() % 3) + 1;
        return col;
    }

    struct State {
        int n;
        vector<int> col;
        vector<array<int,4>> cnt;      // cnt[v][c] = number of neighbors of v with color c (c=1..3)
        long long b = 0;              // number of conflicting edges
        vector<int> pos;              // position in conflicted list, -1 if not present
        vector<int> conflicted;       // vertices with cnt[v][col[v]] > 0

        State(int n_=0): n(n_), col(n_+1), cnt(n_+1), pos(n_+1, -1) {}
    };

    static inline void add_conf(State &st, int v) {
        if (st.pos[v] != -1) return;
        st.pos[v] = (int)st.conflicted.size();
        st.conflicted.push_back(v);
    }
    static inline void rem_conf(State &st, int v) {
        int i = st.pos[v];
        if (i == -1) return;
        int last = st.conflicted.back();
        st.conflicted[i] = last;
        st.pos[last] = i;
        st.conflicted.pop_back();
        st.pos[v] = -1;
    }
    static inline void update_conf(State &st, int v) {
        int c = st.col[v];
        bool is = (st.cnt[v][c] > 0);
        if (is) add_conf(st, v);
        else rem_conf(st, v);
    }

    State build_state(const vector<int>& colInit) {
        State st(n);
        st.col = colInit;
        for (int v = 1; v <= n; v++) st.cnt[v] = {0,0,0,0};
        st.b = 0;

        for (int i = 0; i < m; i++) {
            int u = eu[i], v = ev[i];
            int cu = st.col[u], cv = st.col[v];
            st.cnt[u][cv]++;
            st.cnt[v][cu]++;
            if (cu == cv) st.b++;
        }

        st.conflicted.clear();
        fill(st.pos.begin(), st.pos.end(), -1);
        for (int v = 1; v <= n; v++) update_conf(st, v);

        return st;
    }

    void recolor_vertex(State &st, int v, int newC) {
        int oldC = st.col[v];
        if (oldC == newC) return;

        st.b += (long long)st.cnt[v][newC] - (long long)st.cnt[v][oldC];
        st.col[v] = newC;

        for (int u : adj[v]) {
            st.cnt[u][oldC]--;
            st.cnt[u][newC]++;
        }

        update_conf(st, v);
        for (int u : adj[v]) update_conf(st, u);
    }

    void local_search(State &st, vector<int> &bestCol, long long &bestB, double endTime) {
        if (st.b < bestB) {
            bestB = st.b;
            bestCol = st.col;
            if (bestB == 0) return;
        }

        double avgDeg = (n ? (2.0 * (double)m / (double)n) : 0.0);
        double T = 1.5 + avgDeg / 40.0;
        double cool = 0.9993;

        int maxSteps = 20000;
        if (m > 300000) maxSteps = 12000;
        else if (m > 150000) maxSteps = 16000;

        int sinceImprove = 0;

        uniform_real_distribution<double> urd(0.0, 1.0);
        uniform_int_distribution<int> vdist(1, n);

        for (int step = 0; step < maxSteps; step++) {
            if (now_sec() >= endTime) break;
            if (st.b == 0) break;
            if (st.conflicted.empty()) break;

            int v = st.conflicted[uniform_int_distribution<int>(0, (int)st.conflicted.size() - 1)(rng)];
            int cur = st.col[v];

            bool explore = (urd(rng) < 0.10);

            int newC;
            if (explore) {
                newC = (int)(rng() % 2) + 1;
                if (newC >= cur) newC++;
            } else {
                int bestConf = INT_MAX;
                int cand[3], csz = 0;
                for (int c = 1; c <= 3; c++) {
                    int cc = st.cnt[v][c];
                    if (cc < bestConf) {
                        bestConf = cc;
                        cand[0] = c;
                        csz = 1;
                    } else if (cc == bestConf) {
                        cand[csz++] = c;
                    }
                }
                newC = cand[uniform_int_distribution<int>(0, csz - 1)(rng)];
                if (newC == cur && csz > 1) {
                    int idx = uniform_int_distribution<int>(0, csz - 2)(rng);
                    for (int i = 0, k = 0; i < csz; i++) {
                        if (cand[i] == cur) continue;
                        if (k == idx) { newC = cand[i]; break; }
                        k++;
                    }
                }
            }

            int delta = st.cnt[v][newC] - st.cnt[v][cur];

            bool accept = false;
            if (delta < 0) accept = true;
            else if (delta == 0) accept = (urd(rng) < 0.30);
            else {
                double p = exp(-(double)delta / max(0.01, T));
                accept = (urd(rng) < p);
            }

            if (accept) {
                recolor_vertex(st, v, newC);
                if (st.b < bestB) {
                    bestB = st.b;
                    bestCol = st.col;
                    sinceImprove = 0;
                    if (bestB == 0) break;
                } else {
                    sinceImprove++;
                }
            } else {
                sinceImprove++;
            }

            T *= cool;
            if (T < 0.05) T = 0.05;

            if (sinceImprove >= 3000) {
                // small perturbation
                int flips = 3;
                for (int i = 0; i < flips; i++) {
                    int x = vdist(rng);
                    int c = st.col[x];
                    int nc = (int)(rng() % 2) + 1;
                    if (nc >= c) nc++;
                    recolor_vertex(st, x, nc);
                }
                sinceImprove = 0;
                T = 1.5 + avgDeg / 40.0;
            }
        }
    }

    vector<int> solve(double timeLimitSec = 1.85) {
        if (m == 0) return vector<int>(n + 1, 1);

        double start = now_sec();
        double endTime = start + timeLimitSec;

        vector<int> bestCol(n + 1, 1);
        long long bestB = (long long)m + 1;

        // First run: DSATUR + local search
        {
            auto init = init_dsatur();
            State st = build_state(init);
            local_search(st, bestCol, bestB, endTime);
        }

        int restarts = 0;
        while (now_sec() < endTime && bestB > 0) {
            restarts++;
            vector<int> init;
            double r = uniform_real_distribution<double>(0.0, 1.0)(rng);
            if (r < 0.30) init = init_dsatur();
            else init = init_random();

            State st = build_state(init);
            local_search(st, bestCol, bestB, endTime);
        }

        // Ensure colors in 1..3
        for (int v = 1; v <= n; v++) {
            if (bestCol[v] < 1 || bestCol[v] > 3) bestCol[v] = 1;
        }
        return bestCol;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    cin >> n >> m;

    Solver solver(n, m);
    solver.eu.resize(m);
    solver.ev.resize(m);

    for (int i = 0; i < m; i++) {
        int u, v;
        cin >> u >> v;
        solver.eu[i] = u;
        solver.ev[i] = v;
        solver.deg[u]++;
        solver.deg[v]++;
    }

    for (int v = 1; v <= n; v++) solver.adj[v].reserve(solver.deg[v]);
    for (int i = 0; i < m; i++) {
        int u = solver.eu[i], v = solver.ev[i];
        solver.adj[u].push_back(v);
        solver.adj[v].push_back(u);
    }

    vector<int> col = solver.solve();

    for (int v = 1; v <= n; v++) {
        if (v > 1) cout << ' ';
        cout << col[v];
    }
    cout << '\n';
    return 0;
}