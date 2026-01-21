#include <bits/stdc++.h>
using namespace std;

struct RNG {
    uint64_t state;
    RNG(uint64_t seed = (uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count()) : state(seed) {}
    inline uint64_t next() {
        uint64_t z = (state += 0x9e3779b97f4a7c15ULL);
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
        return z ^ (z >> 31);
    }
    inline size_t randSize(size_t mod) { return (size_t)(next() % (mod)); }
    inline int randint(int lo, int hi) { // inclusive
        return lo + (int)(next() % (uint64_t)(hi - lo + 1));
    }
    inline double randDouble() { return (next() >> 11) * (1.0/9007199254740992.0); } // [0,1)
};

struct LocalSearch {
    int n;
    const vector<vector<int>>& g;
    const vector<pair<int,int>>& edges;
    RNG& rng;

    vector<uint8_t> color;
    vector<array<int,3>> cnt; // cnt[v][c] = # neighbors of v with color c
    vector<int> curConf; // curConf[v] = cnt[v][color[v]]
    vector<int> conflictNodes;
    vector<int> pos; // position in conflictNodes or -1
    long long b; // number of conflicting edges
    vector<uint8_t> bestColor;
    long long bestB;

    LocalSearch(int n_, const vector<vector<int>>& g_, const vector<pair<int,int>>& edges_, RNG& rng_)
        : n(n_), g(g_), edges(edges_), rng(rng_) {
        color.assign(n, 0);
        cnt.assign(n, {0,0,0});
        curConf.assign(n, 0);
        pos.assign(n, -1);
        b = 0;
        bestB = LLONG_MAX;
    }

    inline void clearStructures() {
        for (int i = 0; i < n; ++i) {
            cnt[i][0] = cnt[i][1] = cnt[i][2] = 0;
            curConf[i] = 0;
            pos[i] = -1;
        }
        conflictNodes.clear();
        b = 0;
    }

    void initColor(const vector<uint8_t>& start) {
        color = start;
        clearStructures();
        for (const auto &e : edges) {
            int u = e.first, v = e.second;
            ++cnt[u][color[v]];
            ++cnt[v][color[u]];
        }
        long long sum = 0;
        for (int v = 0; v < n; ++v) {
            curConf[v] = cnt[v][color[v]];
            if (curConf[v] > 0) addNode(v);
            sum += curConf[v];
        }
        b = sum / 2;
        bestB = b;
        bestColor = color;
    }

    inline void addNode(int v) {
        if (pos[v] != -1) return;
        pos[v] = (int)conflictNodes.size();
        conflictNodes.push_back(v);
    }

    inline void removeNode(int v) {
        int i = pos[v];
        if (i == -1) return;
        int last = conflictNodes.back();
        conflictNodes[i] = last;
        pos[last] = i;
        conflictNodes.pop_back();
        pos[v] = -1;
    }

    inline void switchColor(int v, int newC) {
        int oldC = color[v];
        if (oldC == newC) return;

        int oldConf = curConf[v];
        int newConf = cnt[v][newC];

        color[v] = (uint8_t)newC;
        b += (newConf - oldConf);

        // Update neighbors
        for (int u : g[v]) {
            cnt[u][oldC]--;
            cnt[u][newC]++;
            if (color[u] == oldC) {
                int before = curConf[u];
                curConf[u]--;
                if (before > 0 && curConf[u] == 0) removeNode(u);
            } else if (color[u] == newC) {
                int before = curConf[u];
                curConf[u]++;
                if (before == 0 && curConf[u] > 0) addNode(u);
            }
        }

        // Update v
        curConf[v] = newConf;
        if (oldConf > 0 && newConf == 0) removeNode(v);
        else if (oldConf == 0 && newConf > 0) addNode(v);
    }

    inline int pickNode() {
        if (conflictNodes.empty()) return -1;
        size_t size = conflictNodes.size();
        size_t sample = size < 32 ? size : 32;
        int bestV = -1;
        int bestGain = INT_MIN;
        for (size_t s = 0; s < sample; ++s) {
            int v = conflictNodes[rng.randSize(size)];
            int cur = curConf[v];
            int m = cnt[v][0];
            if (cnt[v][1] < m) m = cnt[v][1];
            if (cnt[v][2] < m) m = cnt[v][2];
            int gain = cur - m;
            if (gain > bestGain) {
                bestGain = gain;
                bestV = v;
            }
        }
        return bestV;
    }

    void run(long long stepLimit, long long endTimeMs) {
        long long steps = 0;
        long long stall = 0;

        auto nowMs = []() -> long long {
            return chrono::duration_cast<chrono::milliseconds>(
                chrono::steady_clock::now().time_since_epoch()).count();
        };

        while (steps < stepLimit) {
            if ((steps & 1023LL) == 0) {
                if (nowMs() >= endTimeMs) break;
            }
            if (b == 0) break;
            if (conflictNodes.empty()) break;

            int v = pickNode();
            if (v == -1) break;

            int oldC = color[v];
            int oldConf = curConf[v];

            int c1 = (oldC + 1) % 3;
            int c2 = (oldC + 2) % 3;
            int cnt1 = cnt[v][c1];
            int cnt2 = cnt[v][c2];
            int newC, newCnt;
            if (cnt1 < cnt2) { newC = c1; newCnt = cnt1; }
            else if (cnt2 < cnt1) { newC = c2; newCnt = cnt2; }
            else { // tie
                newC = (rng.next() & 1ULL) ? c1 : c2;
                newCnt = cnt[v][newC];
            }

            bool moved = false;
            if (newCnt < oldConf) {
                switchColor(v, newC);
                moved = true;
            } else if (newCnt == oldConf) {
                double pPlateau = min(0.25, 0.02 + (double)stall * 0.00002);
                if (rng.randDouble() < pPlateau) {
                    switchColor(v, newC);
                    moved = true;
                }
            } else {
                double pWorse = min(0.10, 0.001 + (double)stall * 0.00001);
                if (rng.randDouble() < pWorse) {
                    switchColor(v, newC);
                    moved = true;
                }
            }

            if (moved) {
                if (b < bestB) {
                    bestB = b;
                    bestColor = color;
                    stall = 0;
                } else {
                    stall++;
                }
            } else {
                stall++;
                // occasional random kick
                if ((steps & 8191LL) == 0) {
                    int u;
                    if (!conflictNodes.empty()) {
                        u = conflictNodes[rng.randSize(conflictNodes.size())];
                    } else {
                        u = rng.randint(0, n - 1);
                    }
                    int nc = rng.randint(0, 2);
                    if (nc == color[u]) nc = (nc + 1) % 3;
                    switchColor(u, nc);
                }
            }

            ++steps;
        }
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m;
    if (!(cin >> n >> m)) {
        return 0;
    }
    vector<vector<int>> g(n);
    g.assign(n, {});
    g.shrink_to_fit();
    vector<pair<int,int>> edges;
    edges.reserve(m);
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        g[u].push_back(v);
        g[v].push_back(u);
        if (u < v) edges.emplace_back(u, v);
        else edges.emplace_back(v, u);
    }
    if (m == 0) {
        for (int i = 0; i < n; ++i) {
            if (i) cout << ' ';
            cout << 1;
        }
        cout << '\n';
        return 0;
    }

    RNG rng;

    // Initial colorings
    vector<uint8_t> color_bip(n, 0);
    {
        vector<int> col(n, -1);
        deque<int> dq;
        for (int i = 0; i < n; ++i) {
            if (col[i] != -1) continue;
            col[i] = 0;
            dq.push_back(i);
            while (!dq.empty()) {
                int v = dq.front(); dq.pop_front();
                for (int u : g[v]) {
                    if (col[u] == -1) {
                        col[u] = col[v] ^ 1;
                        dq.push_back(u);
                    }
                }
            }
        }
        for (int i = 0; i < n; ++i) color_bip[i] = (uint8_t)col[i];
    }

    vector<uint8_t> color_greedy(n, 0);
    {
        vector<int> order(n);
        iota(order.begin(), order.end(), 0);
        sort(order.begin(), order.end(), [&](int a, int b){
            return g[a].size() > g[b].size();
        });
        vector<array<int,3>> cntAssigned(n);
        for (int i = 0; i < n; ++i) cntAssigned[i] = {0,0,0};
        for (int v : order) {
            int c0 = cntAssigned[v][0];
            int c1 = cntAssigned[v][1];
            int c2 = cntAssigned[v][2];
            int bestC = 0;
            int bestCnt = c0;
            if (c1 < bestCnt || (c1 == bestCnt && (rng.next() & 1ULL))) { bestCnt = c1; bestC = 1; }
            if (c2 < bestCnt || (c2 == bestCnt && (rng.next() & 1ULL))) { bestCnt = c2; bestC = 2; }
            color_greedy[v] = (uint8_t)bestC;
            for (int u : g[v]) {
                cntAssigned[u][bestC]++;
            }
        }
    }

    vector<uint8_t> color_rand(n, 0);
    for (int i = 0; i < n; ++i) color_rand[i] = (uint8_t)rng.randint(0, 2);

    auto nowMs = []() -> long long {
        return chrono::duration_cast<chrono::milliseconds>(
            chrono::steady_clock::now().time_since_epoch()).count();
    };
    long long startTime = nowMs();
    long long TOTAL_MS = 1900; // time budget
    long long endTime = startTime + TOTAL_MS;

    LocalSearch ls(n, g, edges, rng);

    vector<uint8_t> globalBest;
    long long globalBestB = LLONG_MAX;

    auto consider = [&](const vector<uint8_t>& initial) {
        if (nowMs() >= endTime - 5) return;
        long long timeLeft = endTime - nowMs();
        if (timeLeft <= 0) return;
        ls.initColor(initial);
        // Large step limit; time check inside controls actual runtime
        long long stepLimit = max(100000LL, 6LL * (long long)edges.size());
        ls.run(stepLimit, nowMs() + timeLeft - 2);
        if (ls.bestB < globalBestB) {
            globalBestB = ls.bestB;
            globalBest = ls.bestColor;
        }
    };

    consider(color_greedy);
    consider(color_bip);
    consider(color_rand);

    // Additional restarts if time remains
    while (nowMs() < endTime - 50) {
        // Mutated restart from best if available, otherwise random
        vector<uint8_t> start(n);
        if (!globalBest.empty()) {
            start = globalBest;
            // Mutate a small fraction of nodes
            int mutateCount = max(1, n / 50); // ~2%
            for (int i = 0; i < mutateCount; ++i) {
                int v = rng.randint(0, n - 1);
                int nc = rng.randint(0, 2);
                if (nc == start[v]) nc = (nc + 1) % 3;
                start[v] = (uint8_t)nc;
            }
        } else {
            for (int i = 0; i < n; ++i) start[i] = (uint8_t)rng.randint(0, 2);
        }
        consider(start);
        // Also a pure random restart if time allows
        if (nowMs() < endTime - 100) {
            for (int i = 0; i < n; ++i) start[i] = (uint8_t)rng.randint(0, 2);
            consider(start);
        }
    }

    if (globalBest.empty()) {
        // fallback
        globalBest = color_greedy;
    }

    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << (int)globalBest[i] + 1;
    }
    cout << '\n';
    return 0;
}