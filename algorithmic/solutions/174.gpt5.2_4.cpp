#include <bits/stdc++.h>
using namespace std;

static inline uint64_t nowNs() {
    return chrono::duration_cast<chrono::nanoseconds>(
               chrono::steady_clock::now().time_since_epoch())
        .count();
}

struct Solver {
    int n;
    long long m;
    vector<vector<int>> g;
    vector<int> deg;
    mt19937 rng;

    Solver(int n_, long long m_) : n(n_), m(m_), g(n + 1), deg(n + 1, 0) {
        uint64_t seed = chrono::high_resolution_clock::now().time_since_epoch().count();
        seed ^= (uint64_t)uintptr_t(this) + 0x9e3779b97f4a7c15ULL;
        rng.seed((uint32_t)(seed ^ (seed >> 32)));
    }

    inline uint32_t rnd() { return rng(); }
    inline int rndInt(int mod) { return (int)(rnd() % (uint32_t)mod); }
    inline int rndColor() { return (int)(rnd() % 3u) + 1; }
    inline double rnd01() { return (double)rnd() * (1.0 / 4294967295.0); }

    vector<int> initGreedy() {
        vector<int> col(n + 1, 0);
        vector<int> ord(n);
        iota(ord.begin(), ord.end(), 1);
        shuffle(ord.begin(), ord.end(), rng);
        stable_sort(ord.begin(), ord.end(), [&](int a, int b) { return deg[a] > deg[b]; });

        for (int v : ord) {
            int cnt[4] = {0, 0, 0, 0};
            for (int u : g[v]) {
                int cu = col[u];
                if (cu) cnt[cu]++;
            }
            int best = min({cnt[1], cnt[2], cnt[3]});
            int cand[3], k = 0;
            for (int c = 1; c <= 3; c++) if (cnt[c] == best) cand[k++] = c;
            col[v] = cand[rndInt(k)];
        }
        return col;
    }

    vector<int> initRandomThenSweep(int sweeps = 2) {
        vector<int> col(n + 1);
        for (int i = 1; i <= n; i++) col[i] = rndColor();

        vector<int> ord(n);
        iota(ord.begin(), ord.end(), 1);
        for (int s = 0; s < sweeps; s++) {
            shuffle(ord.begin(), ord.end(), rng);
            for (int v : ord) {
                int cnt[4] = {0, 0, 0, 0};
                for (int u : g[v]) cnt[col[u]]++;
                int best = min({cnt[1], cnt[2], cnt[3]});
                int cand[3], k = 0;
                for (int c = 1; c <= 3; c++) if (cnt[c] == best) cand[k++] = c;
                col[v] = cand[rndInt(k)];
            }
        }
        return col;
    }

    int localSearch(vector<int>& col, uint64_t deadlineNs, long long maxMoves) {
        vector<array<int, 4>> cnt(n + 1);
        vector<int> conf(n + 1, 0);
        vector<int> pos(n + 1, -1);
        vector<int> confList;
        confList.reserve(n);

        for (int v = 1; v <= n; v++) cnt[v] = {0, 0, 0, 0};
        for (int v = 1; v <= n; v++) {
            const int cv = col[v];
            for (int u : g[v]) {
                cnt[v][col[u]]++;
            }
            (void)cv;
        }

        long long b2 = 0;
        for (int v = 1; v <= n; v++) {
            conf[v] = cnt[v][col[v]];
            b2 += conf[v];
            if (conf[v] > 0) {
                pos[v] = (int)confList.size();
                confList.push_back(v);
            }
        }
        int b = (int)(b2 / 2);

        auto addConf = [&](int v) {
            if (pos[v] != -1) return;
            pos[v] = (int)confList.size();
            confList.push_back(v);
        };
        auto remConf = [&](int v) {
            int p = pos[v];
            if (p == -1) return;
            int last = confList.back();
            confList[p] = last;
            pos[last] = p;
            confList.pop_back();
            pos[v] = -1;
        };

        int bestB = b;
        vector<int> bestCol = col;

        long long iter = 0;
        int stagnation = 0;

        while (iter < maxMoves && nowNs() < deadlineNs) {
            if (confList.empty()) break;

            int v = confList[rndInt((int)confList.size())];
            int old = col[v];

            int c1 = cnt[v][1], c2 = cnt[v][2], c3 = cnt[v][3];
            int bestCnt = min({c1, c2, c3});

            int cand[3], k = 0;
            for (int c = 1; c <= 3; c++) {
                if (cnt[v][c] == bestCnt && c != old) cand[k++] = c;
            }

            int newc = old;
            if (k > 0) {
                newc = cand[rndInt(k)];
            } else {
                // No non-worsening move (old is the unique best or only tied with itself).
                // Sometimes escape by taking a random different color.
                double pEscape = 0.01 + min(0.15, stagnation * 0.00005);
                if (rnd01() < pEscape) {
                    int r = rndColor();
                    if (r == old) r = (r % 3) + 1;
                    newc = r;
                } else {
                    stagnation++;
                    iter++;
                    continue;
                }
            }

            if (newc == old) {
                stagnation++;
                iter++;
                continue;
            }

            int delta = cnt[v][newc] - cnt[v][old];
            col[v] = newc;
            b += delta;

            for (int u : g[v]) {
                cnt[u][old]--;
                cnt[u][newc]++;

                int oldConf = conf[u];
                conf[u] = cnt[u][col[u]];
                if (oldConf == 0 && conf[u] > 0) addConf(u);
                else if (oldConf > 0 && conf[u] == 0) remConf(u);
            }

            {
                int oldConf = conf[v];
                conf[v] = cnt[v][col[v]];
                if (oldConf == 0 && conf[v] > 0) addConf(v);
                else if (oldConf > 0 && conf[v] == 0) remConf(v);
            }

            if (b < bestB) {
                bestB = b;
                bestCol = col;
                stagnation = 0;
                if (bestB == 0) break;
            } else {
                stagnation++;
            }

            iter++;
        }

        col.swap(bestCol);
        return bestB;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    long long m;
    if (!(cin >> n >> m)) return 0;

    if (m == 0) {
        for (int i = 1; i <= n; i++) {
            if (i > 1) cout << ' ';
            cout << 1;
        }
        cout << '\n';
        return 0;
    }

    vector<int> U(m), V(m);
    vector<int> deg(n + 1, 0);
    for (long long i = 0; i < m; i++) {
        int u, v;
        cin >> u >> v;
        U[i] = u; V[i] = v;
        deg[u]++; deg[v]++;
    }

    Solver solver(n, m);
    solver.deg = deg;
    for (int i = 1; i <= n; i++) solver.g[i].reserve(deg[i]);
    for (long long i = 0; i < m; i++) {
        int u = U[i], v = V[i];
        solver.g[u].push_back(v);
        solver.g[v].push_back(u);
    }

    const double TIME_LIMIT_SEC = 0.88; // conservative
    uint64_t start = nowNs();
    uint64_t deadline = start + (uint64_t)(TIME_LIMIT_SEC * 1e9);

    long long totalMovesTarget = 120000000LL; // edge-touch budget
    long long totalMoves;
    {
        long long denom = max(1LL, 2LL * m);
        long long mv = (totalMovesTarget * n) / denom;
        totalMoves = max(80000LL, min(2500000LL, mv));
    }

    vector<int> bestCol(n + 1, 1);
    int bestB = INT_MAX;

    int runId = 0;
    while (nowNs() < deadline) {
        uint64_t now = nowNs();
        uint64_t remain = (deadline > now) ? (deadline - now) : 0;
        if (remain < 10'000'000ULL) break; // <10ms left

        double perRunSec = (m > 200000 ? 0.28 : 0.16);
        uint64_t runDeadline = min(deadline, now + (uint64_t)(perRunSec * 1e9));

        vector<int> col;
        if ((runId & 1) == 0) col = solver.initGreedy();
        else col = solver.initRandomThenSweep(2);

        long long perRunMoves = max(20000LL, totalMoves / 6);
        int b = solver.localSearch(col, runDeadline, perRunMoves);

        if (b < bestB) {
            bestB = b;
            bestCol = col;
            if (bestB == 0) break;
        }

        runId++;
    }

    for (int i = 1; i <= n; i++) {
        if (i > 1) cout << ' ';
        cout << bestCol[i];
    }
    cout << '\n';
    return 0;
}