#include <bits/stdc++.h>
using namespace std;

struct RNG {
    uint64_t x;
    explicit RNG(uint64_t seed = 0) : x(seed) {}
    static uint64_t splitmix64(uint64_t &s) {
        uint64_t z = (s += 0x9e3779b97f4a7c15ULL);
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
        return z ^ (z >> 31);
    }
    uint64_t nextU64() { return splitmix64(x); }
    uint32_t nextU32() { return (uint32_t)nextU64(); }
    int nextInt(int l, int r) { return l + (int)(nextU64() % (uint64_t)(r - l + 1)); }
};

static inline int pickAmong(const int *a, int k, RNG &rng) {
    return a[(int)(rng.nextU64() % (uint64_t)k)];
}

struct Result {
    int conflicts;
    vector<uint8_t> col;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    cin >> n >> m;
    if (!cin) return 0;

    if (m == 0) {
        for (int i = 0; i < n; i++) {
            if (i) cout << ' ';
            cout << 1;
        }
        cout << '\n';
        return 0;
    }

    vector<int> U(m), V(m);
    vector<int> deg(n, 0);
    for (int i = 0; i < m; i++) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        U[i] = u; V[i] = v;
        deg[u]++; deg[v]++;
    }

    vector<vector<int>> adj(n);
    for (int i = 0; i < n; i++) adj[i].reserve(deg[i]);
    for (int i = 0; i < m; i++) {
        int u = U[i], v = V[i];
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    uint64_t seed = (uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count();
    seed ^= (uint64_t)(uintptr_t)(&adj);
    RNG rng(seed);

    auto runRestart = [&](RNG &rngLocal) -> Result {
        vector<uint32_t> tie(n);
        for (int i = 0; i < n; i++) tie[i] = rngLocal.nextU32();

        vector<int> order(n);
        iota(order.begin(), order.end(), 0);
        sort(order.begin(), order.end(), [&](int a, int b) {
            if (deg[a] != deg[b]) return deg[a] > deg[b];
            return tie[a] < tie[b];
        });

        vector<uint8_t> col(n, 0);
        for (int v : order) {
            int cnt[4] = {0, 0, 0, 0};
            for (int u : adj[v]) {
                uint8_t cu = col[u];
                if (cu) cnt[cu]++;
            }
            int bestCols[3], k = 0;
            int best = min({cnt[1], cnt[2], cnt[3]});
            for (int c = 1; c <= 3; c++) if (cnt[c] == best) bestCols[k++] = c;
            col[v] = (uint8_t)pickAmong(bestCols, k, rngLocal);
        }

        vector<array<int, 4>> ncnt(n);
        for (int i = 0; i < n; i++) ncnt[i] = {0, 0, 0, 0};

        int b = 0;
        for (int i = 0; i < m; i++) {
            int u = U[i], v = V[i];
            uint8_t cu = col[u], cv = col[v];
            ncnt[u][cv]++;
            ncnt[v][cu]++;
            if (cu == cv) b++;
        }

        vector<int> sc(n, 0);
        for (int i = 0; i < n; i++) sc[i] = ncnt[i][col[i]];

        vector<int> bad;
        bad.reserve(n);
        vector<int> pos(n, -1);

        auto setBad = [&](int v) {
            bool isBad = (sc[v] > 0);
            if (isBad) {
                if (pos[v] == -1) {
                    pos[v] = (int)bad.size();
                    bad.push_back(v);
                }
            } else {
                if (pos[v] != -1) {
                    int idx = pos[v];
                    int w = bad.back();
                    bad[idx] = w;
                    pos[w] = idx;
                    bad.pop_back();
                    pos[v] = -1;
                }
            }
        };

        for (int i = 0; i < n; i++) if (sc[i] > 0) { pos[i] = (int)bad.size(); bad.push_back(i); }

        int bestB = b;
        int stepsNoImprove = 0;

        long long budget = 50LL * m + 20000; // total neighbor-updates budget
        long long steps = 0;
        long long maxSteps = 4000000LL + 10LL * m;

        auto recolor = [&](int v, int newc) {
            int oldc = col[v];
            if (oldc == newc) return;

            b += -ncnt[v][oldc] + ncnt[v][newc];

            col[v] = (uint8_t)newc;
            sc[v] = ncnt[v][newc];

            for (int u : adj[v]) {
                ncnt[u][oldc]--;
                ncnt[u][newc]++;
                if (col[u] == oldc) {
                    sc[u]--;
                    setBad(u);
                } else if (col[u] == newc) {
                    sc[u]++;
                    setBad(u);
                }
            }
            setBad(v);
        };

        while (!bad.empty() && budget > 0 && steps < maxSteps && b > 0) {
            steps++;
            int v = bad[(int)(rngLocal.nextU64() % (uint64_t)bad.size())];
            int cur = col[v];

            int c1 = ncnt[v][1], c2 = ncnt[v][2], c3 = ncnt[v][3];
            int best = min({c1, c2, c3});
            int bestCols[3], k = 0;
            if (c1 == best) bestCols[k++] = 1;
            if (c2 == best) bestCols[k++] = 2;
            if (c3 == best) bestCols[k++] = 3;

            int chosen = cur;

            if (k >= 2) {
                int options[3], kk = 0;
                for (int i = 0; i < k; i++) if (bestCols[i] != cur) options[kk++] = bestCols[i];
                if (kk > 0) chosen = options[(int)(rngLocal.nextU64() % (uint64_t)kk)];
                else chosen = bestCols[(int)(rngLocal.nextU64() % (uint64_t)k)];
            } else {
                int sec = INT_MAX;
                int secCols[2], kk = 0;
                for (int c = 1; c <= 3; c++) if (c != cur) {
                    int val = ncnt[v][c];
                    if (val < sec) {
                        sec = val;
                        kk = 0;
                        secCols[kk++] = c;
                    } else if (val == sec) {
                        secCols[kk++] = c;
                    }
                }
                uint64_t r = rngLocal.nextU64();
                if ((int)(r % 100) < 15) chosen = secCols[(int)((r >> 32) % (uint64_t)kk)];
                else if ((int)(r % 2000) == 0) chosen = 1 + (int)((r >> 10) % 3);
                else chosen = cur;
            }

            if (chosen != cur) {
                budget -= (long long)adj[v].size();
                recolor(v, chosen);
            }

            if (b < bestB) {
                bestB = b;
                stepsNoImprove = 0;
            } else {
                stepsNoImprove++;
                if (stepsNoImprove > 300000 && budget > 0) {
                    int rv = (int)(rngLocal.nextU64() % (uint64_t)n);
                    int nc = 1 + (int)(rngLocal.nextU64() % 3ULL);
                    if (nc == (int)col[rv]) nc = 1 + (nc % 3);
                    budget -= (long long)adj[rv].size();
                    recolor(rv, nc);
                    stepsNoImprove = 0;
                }
            }
        }

        return {b, std::move(col)};
    };

    int restarts = 3;
    if (m < 50000) restarts = 4;
    if (m > 150000) restarts = 3;

    int bestConf = INT_MAX;
    vector<uint8_t> bestCol;

    for (int r = 0; r < restarts; r++) {
        RNG rngLocal(rng.nextU64() ^ (uint64_t)r * 0x9e3779b97f4a7c15ULL);
        Result res = runRestart(rngLocal);
        if (res.conflicts < bestConf || bestCol.empty()) {
            bestConf = res.conflicts;
            bestCol = std::move(res.col);
            if (bestConf == 0) break;
        }
    }

    if (bestCol.empty()) bestCol.assign(n, 1);

    for (int i = 0; i < n; i++) {
        if (i) cout << ' ';
        cout << (int)bestCol[i];
    }
    cout << '\n';
    return 0;
}