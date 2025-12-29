#include <bits/stdc++.h>
using namespace std;

struct FastRNG {
    uint64_t x;
    FastRNG(uint64_t seed = 88172645463325252ull) : x(seed) {}
    static uint64_t splitmix64(uint64_t &s) {
        uint64_t z = (s += 0x9e3779b97f4a7c15ull);
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ull;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebull;
        return z ^ (z >> 31);
    }
    uint64_t nextU64() { return splitmix64(x); }
    uint32_t nextU32() { return (uint32_t)nextU64(); }
    int nextInt(int mod) { return (int)(nextU64() % (uint64_t)mod); }
    int nextInt(int l, int r) { return l + nextInt(r - l + 1); } // inclusive
    double nextDouble() { // [0,1)
        return (nextU64() >> 11) * (1.0 / 9007199254740992.0);
    }
};

static inline void recolor_vertex(
    int v, int newc,
    vector<int> &col,
    vector<array<int,4>> &cnt,
    const vector<vector<int>> &adj,
    long long &confEdges
) {
    int old = col[v];
    if (old == newc) return;
    int oldConf = cnt[v][old];
    int newConf = cnt[v][newc];
    confEdges += (long long)newConf - (long long)oldConf;

    for (int u : adj[v]) {
        cnt[u][old]--;
        cnt[u][newc]++;
    }
    col[v] = newc;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    int m;
    cin >> n >> m;

    if (n <= 0) return 0;

    vector<pair<int,int>> edges;
    edges.reserve(m);
    vector<int> deg(n, 0);

    for (int i = 0; i < m; i++) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        edges.emplace_back(u, v);
        deg[u]++; deg[v]++;
    }

    vector<vector<int>> adj(n);
    for (int i = 0; i < n; i++) adj[i].reserve(deg[i]);
    for (auto &e : edges) {
        int u = e.first, v = e.second;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    vector<int> bestCol(n, 1);
    long long bestConf = (m == 0 ? 0LL : (long long)m);

    if (m == 0) {
        for (int i = 0; i < n; i++) {
            if (i) cout << ' ';
            cout << 1;
        }
        cout << '\n';
        return 0;
    }

    uint64_t seed = chrono::high_resolution_clock::now().time_since_epoch().count();
    seed ^= (uint64_t)(uintptr_t)(&seed);
    FastRNG rng(seed);

    auto start = chrono::steady_clock::now();
    auto endTime = start + chrono::milliseconds(1850);

    double avgdeg = 2.0 * (double)m / (double)n;
    int maxStepsBase = (avgdeg > 0.0 ? (int)(3e7 / avgdeg) : 300000);
    maxStepsBase = max(20000, min(300000, maxStepsBase));

    vector<int> col(n, 1);
    vector<array<int,4>> cnt(n);
    vector<int> confs;
    confs.reserve(n);

    auto build_counts = [&](long long &confEdges) {
        for (int i = 0; i < n; i++) cnt[i] = {0,0,0,0};
        confEdges = 0;
        for (auto &e : edges) {
            int u = e.first, v = e.second;
            int cu = col[u], cv = col[v];
            cnt[u][cv]++;
            cnt[v][cu]++;
            if (cu == cv) confEdges++;
        }
    };

    auto greedy_init = [&]() {
        vector<int> order(n);
        iota(order.begin(), order.end(), 0);
        sort(order.begin(), order.end(), [&](int a, int b) {
            if (deg[a] != deg[b]) return deg[a] > deg[b];
            return rng.nextU32() < rng.nextU32();
        });

        fill(col.begin(), col.end(), 0);

        array<int,4> local{};
        for (int v : order) {
            local = {0,0,0,0};
            for (int u : adj[v]) {
                int cu = col[u];
                if (cu) local[cu]++;
            }
            int minVal = min({local[1], local[2], local[3]});
            int candidates[3];
            int k = 0;
            for (int c = 1; c <= 3; c++) if (local[c] == minVal) candidates[k++] = c;
            col[v] = candidates[rng.nextInt(k)];
        }
    };

    auto rebuild_confs = [&]() {
        confs.clear();
        for (int v = 0; v < n; v++) {
            if (cnt[v][col[v]] > 0) confs.push_back(v);
        }
    };

    vector<int> runBestCol;
    runBestCol.reserve(n);

    while (chrono::steady_clock::now() < endTime - chrono::milliseconds(30)) {
        greedy_init();

        long long confEdges = 0;
        build_counts(confEdges);

        if (confEdges < bestConf) {
            bestConf = confEdges;
            bestCol = col;
            if (bestConf == 0) break;
        }

        long long runBestConf = confEdges;
        runBestCol = col;

        rebuild_confs();
        int stalePicks = 0;
        int stagn = 0;

        int maxSteps = maxStepsBase;
        for (int step = 0; step < maxSteps && confEdges > 0; step++) {
            if ((step & 1023) == 0) {
                if (chrono::steady_clock::now() > endTime - chrono::milliseconds(20)) break;
                rebuild_confs();
                stalePicks = 0;
                if (confs.empty()) break;
            }

            if (confs.empty()) break;

            int v = confs[rng.nextInt((int)confs.size())];
            int cur = col[v];
            int curVal = cnt[v][cur];
            if (curVal == 0) {
                if (++stalePicks > 2000) {
                    rebuild_confs();
                    stalePicks = 0;
                }
                continue;
            }

            int minVal = min({cnt[v][1], cnt[v][2], cnt[v][3]});
            int mins[3];
            int k = 0;
            for (int c = 1; c <= 3; c++) if (cnt[v][c] == minVal) mins[k++] = c;
            int chosen = mins[rng.nextInt(k)];

            // noise depends on current conflict ratio
            double noise = 0.02 + 0.18 * ((double)confEdges / (double)m); // [0.02, 0.20]
            if (noise > 0.20) noise = 0.20;

            bool moved = false;

            if (chosen == cur) {
                if (k > 1 && rng.nextInt(100) < 30) {
                    // move to another equally-good color
                    int alt;
                    do { alt = mins[rng.nextInt(k)]; } while (alt == cur);
                    recolor_vertex(v, alt, col, cnt, adj, confEdges);
                    moved = true;
                } else if (rng.nextDouble() < noise) {
                    int alt = 1 + rng.nextInt(3);
                    if (alt == cur) alt = cur % 3 + 1;
                    recolor_vertex(v, alt, col, cnt, adj, confEdges);
                    moved = true;
                }
            } else {
                // usually accept best move; occasionally accept a random move too (handled via noise above)
                recolor_vertex(v, chosen, col, cnt, adj, confEdges);
                moved = true;
            }

            if (!moved) continue;

            if (confEdges < runBestConf) {
                runBestConf = confEdges;
                runBestCol = col;
                stagn = 0;
            } else {
                stagn++;
            }

            if (confEdges < bestConf) {
                bestConf = confEdges;
                bestCol = col;
                if (bestConf == 0) break;
            }

            if (stagn > 6000) {
                // shake: random recolors to escape local minima
                int shakes = 1 + rng.nextInt(7);
                for (int i = 0; i < shakes; i++) {
                    int x = rng.nextInt(n);
                    int nc = 1 + rng.nextInt(3);
                    if (nc == col[x]) nc = col[x] % 3 + 1;
                    recolor_vertex(x, nc, col, cnt, adj, confEdges);
                }
                stagn = 0;
                rebuild_confs();
            }
        }

        if (runBestConf < bestConf) {
            bestConf = runBestConf;
            bestCol = runBestCol;
            if (bestConf == 0) break;
        }
    }

    for (int i = 0; i < n; i++) {
        if (i) cout << ' ';
        int c = bestCol[i];
        if (c < 1 || c > 3) c = 1;
        cout << c;
    }
    cout << '\n';
    return 0;
}