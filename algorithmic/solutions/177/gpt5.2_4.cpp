#include <bits/stdc++.h>
using namespace std;

struct XorShift64 {
    uint64_t x;
    explicit XorShift64(uint64_t seed = 88172645463325252ull) : x(seed ? seed : 88172645463325252ull) {}
    inline uint64_t next_u64() {
        x ^= x << 7;
        x ^= x >> 9;
        return x;
    }
    inline int next_int(int mod) { return (int)(next_u64() % (uint64_t)mod); }
    inline int next_int(int l, int r) { return l + next_int(r - l + 1); }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    cin >> n >> m;

    if (m == 0) {
        for (int i = 1; i <= n; i++) {
            if (i > 1) cout << ' ';
            cout << 1;
        }
        cout << "\n";
        return 0;
    }

    vector<int> head(n + 1, -1);
    vector<int> to(2LL * m);
    vector<int> nxt(2LL * m);
    vector<int> deg(n + 1, 0);
    int ec = 0;

    auto add_edge = [&](int u, int v) {
        to[ec] = v;
        nxt[ec] = head[u];
        head[u] = ec++;
    };

    for (int i = 0; i < m; i++) {
        int u, v;
        cin >> u >> v;
        add_edge(u, v);
        add_edge(v, u);
        deg[u]++; deg[v]++;
    }

    uint64_t seed = (uint64_t)chrono::steady_clock::now().time_since_epoch().count();
    seed ^= (uint64_t)(uintptr_t)(&head);
    seed ^= (uint64_t)n * 1315423911u + (uint64_t)m * 2654435761u;
    XorShift64 rng(seed);

    vector<int> col(n + 1, 1), bestCol(n + 1, 1);
    vector<array<int, 4>> cnt(n + 1);
    vector<int> confList;
    vector<int> pos(n + 1, -1);
    confList.reserve(n);

    auto updateStatus = [&](int v) {
        bool now = (cnt[v][col[v]] > 0);
        int &p = pos[v];
        if (now) {
            if (p == -1) {
                p = (int)confList.size();
                confList.push_back(v);
            }
        } else {
            if (p != -1) {
                int idx = p;
                int w = confList.back();
                confList[idx] = w;
                pos[w] = idx;
                confList.pop_back();
                p = -1;
            }
        }
    };

    auto buildCounts = [&](int &totalConflicts) {
        for (int i = 1; i <= n; i++) cnt[i] = {0, 0, 0, 0};

        for (int v = 1; v <= n; v++) {
            for (int e = head[v]; e != -1; e = nxt[e]) {
                int u = to[e];
                cnt[v][col[u]]++;
            }
        }

        long long sum = 0;
        for (int v = 1; v <= n; v++) sum += cnt[v][col[v]];
        totalConflicts = (int)(sum / 2);

        confList.clear();
        fill(pos.begin(), pos.end(), -1);
        for (int v = 1; v <= n; v++) updateStatus(v);
    };

    auto changeColor = [&](int v, int newc, int &totalConflicts) {
        int old = col[v];
        if (old == newc) return;

        totalConflicts += -cnt[v][old] + cnt[v][newc];
        col[v] = newc;
        updateStatus(v);

        for (int e = head[v]; e != -1; e = nxt[e]) {
            int u = to[e];
            cnt[u][old]--;
            cnt[u][newc]++;
            updateStatus(u);
        }
    };

    auto greedyInit = [&]() {
        vector<pair<int,int>> ord;
        ord.reserve(n);
        for (int v = 1; v <= n; v++) {
            ord.push_back({-deg[v], (int)(rng.next_u64() & 0x7fffffff)});
        }
        vector<int> order(n);
        iota(order.begin(), order.end(), 1);
        sort(order.begin(), order.end(), [&](int a, int b) {
            if (deg[a] != deg[b]) return deg[a] > deg[b];
            return ord[a-1].second < ord[b-1].second;
        });

        fill(col.begin(), col.end(), 0);
        int localCnt[4];

        for (int v : order) {
            localCnt[1] = localCnt[2] = localCnt[3] = 0;
            for (int e = head[v]; e != -1; e = nxt[e]) {
                int u = to[e];
                int cu = col[u];
                if (cu) localCnt[cu]++;
            }
            int best = min({localCnt[1], localCnt[2], localCnt[3]});
            int choices[3], k = 0;
            for (int c = 1; c <= 3; c++) if (localCnt[c] == best) choices[k++] = c;
            col[v] = choices[rng.next_int(k)];
        }
    };

    auto randomInit = [&]() {
        for (int v = 1; v <= n; v++) col[v] = 1 + rng.next_int(3);
    };

    auto localSearch = [&](double timeLimitSec, int &totalConflicts, int &bestTotalConflicts) {
        auto start = chrono::steady_clock::now();
        auto elapsed = [&]() -> double {
            return chrono::duration<double>(chrono::steady_clock::now() - start).count();
        };

        int bestHere = totalConflicts;
        long long noImprove = 0;
        const long long NO_IMPROVE_LIMIT = 60000;
        const int MAX_STEPS = 3000000;

        for (int step = 0; step < MAX_STEPS; step++) {
            if (elapsed() >= timeLimitSec) break;
            if (confList.empty()) break;

            int v = confList[rng.next_int((int)confList.size())];
            int curc = col[v];
            int curConf = cnt[v][curc];

            int bestConf = curConf;
            int bestColors[3], k = 0;

            for (int c = 1; c <= 3; c++) {
                int conf = cnt[v][c];
                if (conf < bestConf) {
                    bestConf = conf;
                    k = 0;
                    bestColors[k++] = c;
                } else if (conf == bestConf) {
                    bestColors[k++] = c;
                }
            }

            int newc = curc;
            if (bestConf < curConf) {
                newc = bestColors[rng.next_int(k)];
            } else {
                int r = rng.next_int(1000);
                if (r < 170) { // 17% random walk
                    newc = 1 + rng.next_int(3);
                    if (newc == curc) newc = 1 + rng.next_int(3);
                } else {
                    if (k > 1) {
                        do { newc = bestColors[rng.next_int(k)]; } while (newc == curc);
                    } else {
                        if (r < 200) {
                            newc = 1 + rng.next_int(3);
                            if (newc == curc) newc = 1 + rng.next_int(3);
                        } else {
                            newc = curc;
                        }
                    }
                }
            }

            if (newc != curc) changeColor(v, newc, totalConflicts);

            if (totalConflicts < bestHere) {
                bestHere = totalConflicts;
                noImprove = 0;
                if (totalConflicts < bestTotalConflicts) {
                    bestTotalConflicts = totalConflicts;
                    bestCol = col;
                }
            } else {
                noImprove++;
                if (noImprove > NO_IMPROVE_LIMIT) break;
            }
            if (bestTotalConflicts == 0) break;
        }
    };

    auto globalStart = chrono::steady_clock::now();
    auto globalElapsed = [&]() -> double {
        return chrono::duration<double>(chrono::steady_clock::now() - globalStart).count();
    };

    double GLOBAL_LIMIT = 1.75; // conservative
    if (n <= 15000 && m <= 80000) GLOBAL_LIMIT = 1.90;

    int totalConflicts = 0;
    greedyInit();
    buildCounts(totalConflicts);

    int bestTotalConflicts = totalConflicts;
    bestCol = col;

    double t0 = globalElapsed();
    double remaining = max(0.0, GLOBAL_LIMIT - t0);
    localSearch(min(0.70, remaining), totalConflicts, bestTotalConflicts);

    while (globalElapsed() < GLOBAL_LIMIT - 0.10 && bestTotalConflicts > 0) {
        randomInit();
        buildCounts(totalConflicts);
        if (totalConflicts < bestTotalConflicts) {
            bestTotalConflicts = totalConflicts;
            bestCol = col;
        }

        double rem = GLOBAL_LIMIT - globalElapsed();
        double slice = min(0.35, max(0.0, rem - 0.05));
        if (slice <= 0.0) break;

        localSearch(slice, totalConflicts, bestTotalConflicts);
    }

    for (int i = 1; i <= n; i++) {
        if (i > 1) cout << ' ';
        cout << bestCol[i];
    }
    cout << "\n";
    return 0;
}