#include <bits/stdc++.h>
using namespace std;

struct SplitMix64 {
    uint64_t x;
    explicit SplitMix64(uint64_t seed = 0) : x(seed) {}
    static uint64_t splitmix64(uint64_t &s) {
        uint64_t z = (s += 0x9e3779b97f4a7c15ULL);
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
        return z ^ (z >> 31);
    }
    uint64_t nextU64() { return splitmix64(x); }
    uint32_t nextU32() { return (uint32_t)nextU64(); }
    int nextInt(int lo, int hi) { // inclusive
        uint64_t r = nextU64();
        return lo + (int)(r % (uint64_t)(hi - lo + 1));
    }
};

struct Solver {
    int N;
    vector<vector<int>> adj;
    vector<int> deg;

    vector<int> cnt;
    vector<unsigned char> inSet;
    int curSize = 0;

    vector<unsigned char> bestSet;
    int bestSize = -1;

    vector<int> mark;
    int stamp = 1;

    SplitMix64 rng;

    explicit Solver(int n) : N(n) {}

    inline void resetState() {
        inSet.assign(N, 0);
        cnt.assign(N, 0);
        curSize = 0;
    }

    inline void addV(int v) {
        inSet[v] = 1;
        curSize++;
        for (int u : adj[v]) cnt[u]++;
    }
    inline void remV(int v) {
        inSet[v] = 0;
        curSize--;
        for (int u : adj[v]) cnt[u]--;
    }

    inline bool try1Swap(int v) {
        if (inSet[v] || cnt[v] != 1) return false;

        int u = -1;
        for (int x : adj[v]) if (inSet[x]) { u = x; break; }
        if (u < 0) return false;

        int before = curSize;
        vector<int> added;
        remV(u);
        if (cnt[v] != 0) { // should not happen with correct cnt, but be safe
            addV(u);
            return false;
        }
        addV(v);
        added.push_back(v);

        vector<int> cand;
        cand.reserve(adj[u].size());
        for (int w : adj[u]) if (!inSet[w] && cnt[w] == 0) cand.push_back(w);
        sort(cand.begin(), cand.end(), [&](int a, int b){
            if (deg[a] != deg[b]) return deg[a] < deg[b];
            return a < b;
        });
        for (int w : cand) {
            if (!inSet[w] && cnt[w] == 0) {
                addV(w);
                added.push_back(w);
            }
        }

        if (curSize > before) return true;

        for (int i = (int)added.size() - 1; i >= 0; --i) remV(added[i]);
        addV(u);
        return false;
    }

    inline bool try2Swap(int v) {
        if (inSet[v] || cnt[v] != 2) return false;

        int u1 = -1, u2 = -1;
        for (int x : adj[v]) if (inSet[x]) {
            if (u1 < 0) u1 = x;
            else { u2 = x; break; }
        }
        if (u1 < 0 || u2 < 0) return false;

        int before = curSize;

        remV(u1);
        remV(u2);

        if (cnt[v] != 0) { // safety
            addV(u1);
            addV(u2);
            return false;
        }

        vector<int> added;
        addV(v);
        added.push_back(v);

        stamp++;
        if (stamp == INT_MAX) { stamp = 1; mark.assign(N, 0); }

        vector<int> cand;
        cand.reserve(adj[u1].size() + adj[u2].size());

        auto pushCand = [&](int w) {
            if (mark[w] == stamp) return;
            mark[w] = stamp;
            if (!inSet[w] && cnt[w] == 0) cand.push_back(w);
        };

        for (int w : adj[u1]) pushCand(w);
        for (int w : adj[u2]) pushCand(w);

        sort(cand.begin(), cand.end(), [&](int a, int b){
            if (deg[a] != deg[b]) return deg[a] < deg[b];
            return a < b;
        });

        for (int w : cand) {
            if (!inSet[w] && cnt[w] == 0) {
                addV(w);
                added.push_back(w);
            }
        }

        if (curSize > before) return true;

        for (int i = (int)added.size() - 1; i >= 0; --i) remV(added[i]);
        addV(u1);
        addV(u2);
        return false;
    }

    inline void localImprove() {
        while (true) {
            bool changed = false;

            for (int v = 0; v < N; ++v) {
                if (!inSet[v] && cnt[v] == 0) {
                    addV(v);
                    changed = true;
                }
            }
            if (changed) continue;

            for (int v = 0; v < N; ++v) {
                if (!inSet[v] && cnt[v] == 1) {
                    if (try1Swap(v)) { changed = true; break; }
                }
            }
            if (changed) continue;

            for (int v = 0; v < N; ++v) {
                if (!inSet[v] && cnt[v] == 2) {
                    if (try2Swap(v)) { changed = true; break; }
                }
            }
            if (!changed) break;
        }
    }

    inline void greedyStatic() {
        resetState();
        vector<int> order(N);
        iota(order.begin(), order.end(), 0);

        vector<uint32_t> noise(N);
        for (int i = 0; i < N; ++i) noise[i] = rng.nextU32();

        sort(order.begin(), order.end(), [&](int a, int b) {
            if (deg[a] != deg[b]) return deg[a] < deg[b];
            return noise[a] < noise[b];
        });

        for (int v : order) if (!inSet[v] && cnt[v] == 0) addV(v);
    }

    inline void greedyDynamic() {
        resetState();

        vector<unsigned char> alive(N, 1);
        vector<int> degCur = deg;
        int aliveCount = N;

        while (aliveCount > 0) {
            int minD = INT_MAX;
            for (int v = 0; v < N; ++v) if (alive[v]) minD = min(minD, degCur[v]);

            vector<int> cand;
            for (int v = 0; v < N; ++v) if (alive[v] && degCur[v] == minD) cand.push_back(v);
            int pick = cand[rng.nextInt(0, (int)cand.size() - 1)];

            addV(pick);

            vector<int> removed;
            removed.reserve(adj[pick].size() + 1);
            if (alive[pick]) { alive[pick] = 0; aliveCount--; removed.push_back(pick); }
            for (int u : adj[pick]) {
                if (alive[u]) { alive[u] = 0; aliveCount--; removed.push_back(u); }
            }

            for (int x : removed) {
                for (int y : adj[x]) if (alive[y]) degCur[y]--;
            }
        }
    }

    inline void loadFromBest() {
        resetState();
        for (int v = 0; v < N; ++v) if (bestSet[v]) addV(v);
    }

    inline void perturbFromBest() {
        loadFromBest();
        vector<int> setVerts;
        setVerts.reserve(curSize);
        for (int v = 0; v < N; ++v) if (inSet[v]) setVerts.push_back(v);

        int p = 1;
        if (!setVerts.empty()) p = min((int)setVerts.size(), rng.nextInt(1, 3));
        for (int i = 0; i < p; ++i) {
            int j = rng.nextInt(i, (int)setVerts.size() - 1);
            swap(setVerts[i], setVerts[j]);
        }
        for (int i = 0; i < p; ++i) remV(setVerts[i]);

        vector<int> order(N);
        iota(order.begin(), order.end(), 0);
        for (int i = N - 1; i > 0; --i) {
            int j = rng.nextInt(0, i);
            swap(order[i], order[j]);
        }
        for (int v : order) if (!inSet[v] && cnt[v] == 0) addV(v);
    }

    inline void updateBest() {
        if (curSize > bestSize) {
            bestSize = curSize;
            bestSet = inSet;
        }
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    cin >> N >> M;

    int B = (N + 63) >> 6;
    vector<vector<uint64_t>> adjBits(N, vector<uint64_t>(B, 0));

    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        adjBits[u][v >> 6] |= 1ULL << (v & 63);
        adjBits[v][u >> 6] |= 1ULL << (u & 63);
    }

    Solver solver(N);
    solver.adj.assign(N, {});
    solver.deg.assign(N, 0);

    for (int i = 0; i < N; ++i) {
        solver.adj[i].reserve(N / 2);
        for (int b = 0; b < B; ++b) {
            uint64_t x = adjBits[i][b];
            while (x) {
                int t = __builtin_ctzll(x);
                int j = (b << 6) + t;
                if (j < N) solver.adj[i].push_back(j);
                x &= x - 1;
            }
        }
        solver.deg[i] = (int)solver.adj[i].size();
    }

    vector<vector<uint64_t>>().swap(adjBits);

    solver.mark.assign(N, 0);
    uint64_t seed = (uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count();
    seed ^= (uint64_t)(uintptr_t)(&solver);
    solver.rng = SplitMix64(seed);

    auto tStart = chrono::steady_clock::now();
    auto timeLeft = [&]() -> double {
        return 1.92 - chrono::duration<double>(chrono::steady_clock::now() - tStart).count();
    };

    solver.greedyStatic();
    solver.localImprove();
    solver.bestSet = solver.inSet;
    solver.bestSize = solver.curSize;

    int it = 0;
    while (timeLeft() > 0) {
        if (solver.bestSize >= N) break;

        if (it < 2 || solver.rng.nextInt(0, 99) < 55 || solver.bestSet.empty()) {
            if (solver.rng.nextInt(0, 1) == 0) solver.greedyStatic();
            else solver.greedyDynamic();
        } else {
            solver.perturbFromBest();
        }

        solver.localImprove();
        solver.updateBest();
        it++;
    }

    for (int i = 0; i < N; ++i) {
        cout << (solver.bestSet[i] ? 1 : 0) << "\n";
    }
    return 0;
}