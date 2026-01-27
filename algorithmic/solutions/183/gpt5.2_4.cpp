#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static constexpr size_t BUFSIZE = 1 << 20;
    int idx = 0, size = 0;
    char buf[BUFSIZE];

    inline char readChar() {
        if (idx >= size) {
            size = (int)fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }

    template <class T>
    bool readInt(T &out) {
        char c;
        do {
            c = readChar();
            if (!c) return false;
        } while (c <= ' ');

        bool neg = false;
        if (c == '-') { neg = true; c = readChar(); }

        T val = 0;
        while (c > ' ') {
            val = val * 10 + (c - '0');
            c = readChar();
        }
        out = neg ? -val : val;
        return true;
    }
};

struct SplitMix64 {
    uint64_t x;
    SplitMix64(uint64_t seed = 0) : x(seed) {}
    inline uint64_t nextU64() {
        uint64_t z = (x += 0x9e3779b97f4a7c15ULL);
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
        return z ^ (z >> 31);
    }
    inline uint32_t nextU32() { return (uint32_t)nextU64(); }
    inline int nextInt(int mod) { return (int)(nextU64() % (uint64_t)mod); }
};

static inline double elapsedSeconds(const chrono::steady_clock::time_point &st) {
    return chrono::duration<double>(chrono::steady_clock::now() - st).count();
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    FastScanner fs;

    int N, M;
    if (!fs.readInt(N)) return 0;
    fs.readInt(M);

    vector<int> deg(N, 0);
    vector<int> U(M), V(M);
    for (int i = 0; i < M; i++) {
        int u, v;
        fs.readInt(u); fs.readInt(v);
        --u; --v;
        U[i] = u; V[i] = v;
        deg[u]++; deg[v]++;
    }

    vector<int> start(N + 1, 0);
    for (int i = 0; i < N; i++) start[i + 1] = start[i] + deg[i];
    vector<int> cur = start;
    vector<int> edges(2LL * M);
    for (int i = 0; i < M; i++) {
        int u = U[i], v = V[i];
        edges[cur[u]++] = v;
        edges[cur[v]++] = u;
    }
    U.clear(); V.clear(); U.shrink_to_fit(); V.shrink_to_fit();

    int maxDeg = 0;
    for (int d : deg) maxDeg = max(maxDeg, d);

    SplitMix64 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count());

    auto greedyByKey = [&](const vector<uint64_t> &key) -> pair<vector<uint8_t>, int> {
        vector<int> order(N);
        iota(order.begin(), order.end(), 0);
        sort(order.begin(), order.end(), [&](int a, int b) { return key[a] < key[b]; });

        vector<int> tight(N, 0);
        vector<uint8_t> sel(N, 0);
        int cnt = 0;

        for (int v : order) {
            if (tight[v] == 0) {
                sel[v] = 1;
                cnt++;
                for (int ei = start[v]; ei < start[v + 1]; ei++) {
                    int nb = edges[ei];
                    tight[nb]++;
                }
            }
        }
        return {move(sel), cnt};
    };

    // Multi-start greedy initialization
    vector<uint8_t> bestSel;
    int bestSize = -1;

    int R = 6;
    for (int r = 0; r < R; r++) {
        int noiseScale;
        if (r == 0) noiseScale = 0;
        else if (r <= 2) noiseScale = max(1, maxDeg / 8 + 1);
        else if (r <= 4) noiseScale = max(1, maxDeg / 3 + 1);
        else noiseScale = max(1, maxDeg + 1);

        vector<uint64_t> key(N);
        for (int v = 0; v < N; v++) {
            uint32_t noise = (noiseScale == 0 ? 0u : (uint32_t)rng.nextInt(noiseScale));
            uint32_t primary = (uint32_t)(deg[v] + (int)noise);
            uint32_t tie = rng.nextU32();
            key[v] = (uint64_t(primary) << 32) | uint64_t(tie);
        }

        auto [sel, sz] = greedyByKey(key);
        if (sz > bestSize) {
            bestSize = sz;
            bestSel = move(sel);
        }
    }

    // Local search with remove-k and re-maximize
    vector<uint8_t> inSol(N, 0);
    vector<int> tight(N, 0);
    vector<int> pos(N, -1);
    vector<int> sol;
    sol.reserve(N);

    auto solAdd = [&](int v) {
        pos[v] = (int)sol.size();
        sol.push_back(v);
    };
    auto solRemove = [&](int v) {
        int i = pos[v];
        int last = sol.back();
        sol[i] = last;
        pos[last] = i;
        sol.pop_back();
        pos[v] = -1;
    };

    auto loadSelection = [&](const vector<uint8_t> &sel) {
        inSol = sel;
        fill(tight.begin(), tight.end(), 0);
        fill(pos.begin(), pos.end(), -1);
        sol.clear();
        for (int v = 0; v < N; v++) if (inSol[v]) solAdd(v);

        for (int v : sol) {
            for (int ei = start[v]; ei < start[v + 1]; ei++) {
                int nb = edges[ei];
                tight[nb]++;
            }
        }
        for (int v : sol) tight[v] = 0;
    };

    loadSelection(bestSel);
    int curSize = (int)sol.size();

    vector<uint8_t> globalBestSel = bestSel;
    int globalBestSize = bestSize;

    vector<pair<int,int>> changes;
    vector<int> added, removed;
    vector<pair<int,int>> heap;
    changes.reserve(1 << 16);
    added.reserve(1 << 12);
    removed.reserve(1 << 12);
    heap.reserve(1 << 12);

    auto heapPush = [&](pair<int,int> p) {
        heap.push_back(p);
        push_heap(heap.begin(), heap.end(), greater<pair<int,int>>());
    };
    auto heapPop = [&]() -> pair<int,int> {
        pop_heap(heap.begin(), heap.end(), greater<pair<int,int>>());
        auto p = heap.back();
        heap.pop_back();
        return p;
    };

    auto removeVertex = [&](int u) {
        inSol[u] = 0;
        removed.push_back(u);
        solRemove(u);
        for (int ei = start[u]; ei < start[u + 1]; ei++) {
            int v = edges[ei];
            tight[v]--;
            changes.push_back({v, -1});
            if (tight[v] == 0 && !inSol[v]) heapPush({deg[v], v});
        }
    };

    auto addVertex = [&](int u) {
        inSol[u] = 1;
        added.push_back(u);
        solAdd(u);
        for (int ei = start[u]; ei < start[u + 1]; ei++) {
            int v = edges[ei];
            tight[v]++;
            changes.push_back({v, +1});
        }
    };

    auto tournamentPick = [&]() -> int {
        int s = (int)sol.size();
        if (s == 1) return sol[0];
        int best = sol[rng.nextInt(s)];
        int bestD = deg[best];
        int trials = min(5, s);
        for (int i = 1; i < trials; i++) {
            int cand = sol[rng.nextInt(s)];
            int d = deg[cand];
            if (d > bestD) { best = cand; bestD = d; }
        }
        return best;
    };

    auto doMove = [&](int k, bool forceAccept) {
        if (sol.empty()) return;

        int oldSize = (int)sol.size();
        changes.clear();
        added.clear();
        removed.clear();
        heap.clear();

        vector<int> toRemove;
        k = min(k, (int)sol.size());
        toRemove.reserve(k);

        if (k == (int)sol.size()) {
            toRemove = sol;
        } else {
            for (int i = 0; i < k; i++) {
                int u;
                while (true) {
                    u = tournamentPick();
                    bool dup = false;
                    for (int x : toRemove) if (x == u) { dup = true; break; }
                    if (!dup) break;
                }
                toRemove.push_back(u);
            }
        }

        for (int u : toRemove) if (inSol[u]) removeVertex(u);

        while (!heap.empty()) {
            auto [d, v] = heapPop();
            if (!inSol[v] && tight[v] == 0) addVertex(v);
        }

        int newSize = (int)sol.size();
        int delta = newSize - oldSize;

        bool accept = forceAccept;
        if (!accept) {
            if (delta > 0) accept = true;
            else if (delta == 0) accept = (rng.nextInt(100) < 20);
            else accept = (rng.nextInt(1000) < 10);
        }

        if (accept) {
            curSize = newSize;
            if (curSize > globalBestSize) {
                globalBestSize = curSize;
                globalBestSel.assign(inSol.begin(), inSol.end());
            }
        } else {
            // rollback
            for (int v : added) {
                if (inSol[v]) {
                    inSol[v] = 0;
                    solRemove(v);
                }
            }
            for (int v : removed) {
                if (!inSol[v]) {
                    inSol[v] = 1;
                    solAdd(v);
                }
            }
            for (int i = (int)changes.size() - 1; i >= 0; i--) {
                auto [v, d] = changes[i];
                tight[v] -= d;
            }
            curSize = (int)sol.size();
        }
    };

    const auto t0 = chrono::steady_clock::now();
    const double TIME_LIMIT = 1.90;

    int sinceBest = 0;
    int it = 0;

    while (true) {
        if ((it++ & 1023) == 0) {
            if (elapsedSeconds(t0) > TIME_LIMIT) break;
        }

        if (curSize + 50 < globalBestSize) {
            loadSelection(globalBestSel);
            curSize = (int)sol.size();
        }

        int r = rng.nextInt(100);
        int k = (r < 70 ? 1 : (r < 95 ? 2 : 3));
        if (curSize < 30 && rng.nextInt(100) < 10) k = min(curSize, 5);

        int oldBest = globalBestSize;
        doMove(k, false);
        if (globalBestSize > oldBest) sinceBest = 0;
        else sinceBest++;

        if (sinceBest > 20000) {
            loadSelection(globalBestSel);
            curSize = (int)sol.size();
            int kk = min(6, (int)sol.size());
            if (kk > 0) doMove(kk, true);
            sinceBest = 0;
        }
    }

    // Final repair / ensure validity by rebuilding via greedy with best as priority
    vector<uint64_t> finalKey(N);
    for (int v = 0; v < N; v++) {
        uint64_t pri = globalBestSel[v] ? 0ULL : 1ULL;
        uint64_t d = (uint64_t)(uint32_t)deg[v];
        uint64_t tie = (uint64_t)rng.nextU32();
        finalKey[v] = (pri << 48) | (d << 32) | tie;
    }
    auto [finalSel, finalSize] = greedyByKey(finalKey);

    string out;
    out.reserve((size_t)N * 2);
    for (int i = 0; i < N; i++) {
        out.push_back(finalSel[i] ? '1' : '0');
        out.push_back('\n');
    }
    cout << out;
    return 0;
}