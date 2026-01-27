#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static constexpr size_t BUFSIZE = 1 << 20;
    char buf[BUFSIZE];
    size_t idx = 0, size = 0;

    inline char read() {
        if (idx >= size) {
            size = fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }

    template <class T>
    bool readInt(T &out) {
        char c;
        do {
            c = read();
            if (!c) return false;
        } while (c <= ' ');

        bool neg = false;
        if (c == '-') {
            neg = true;
            c = read();
        }

        T val = 0;
        while (c > ' ') {
            val = val * 10 + (c - '0');
            c = read();
        }
        out = neg ? -val : val;
        return true;
    }
};

static inline int popc64(uint64_t x) { return __builtin_popcountll(x); }

struct Solver {
    int N, M;
    int B;
    vector<uint64_t> adj; // N * B
    vector<int> deg;
    vector<uint64_t> full;
    mt19937_64 rng;

    Solver(int n, int m) : N(n), M(m) {
        B = (N + 63) >> 6;
        adj.assign((size_t)N * B, 0);
        deg.assign(N, 0);
        full.assign(B, ~0ull);
        int rem = N & 63;
        if (rem) full[B - 1] = (1ull << rem) - 1;
        rng.seed((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count());
    }

    inline uint64_t* AdjPtr(int u) { return &adj[(size_t)u * B]; }
    inline const uint64_t* AdjPtr(int u) const { return &adj[(size_t)u * B]; }

    inline void addEdge(int u, int v) {
        adj[(size_t)u * B + (v >> 6)] |= 1ull << (v & 63);
        adj[(size_t)v * B + (u >> 6)] |= 1ull << (u & 63);
    }

    void computeDegrees() {
        for (int u = 0; u < N; u++) {
            const uint64_t* ap = AdjPtr(u);
            int d = 0;
            for (int i = 0; i < B; i++) d += popc64(ap[i]);
            deg[u] = d;
        }
    }

    inline bool inCand(const vector<uint64_t>& cand, int u) const {
        return (cand[u >> 6] >> (u & 63)) & 1ull;
    }

    inline int candPopcount(const vector<uint64_t>& cand) const {
        int s = 0;
        for (int i = 0; i < B; i++) s += popc64(cand[i]);
        return s;
    }

    inline int intersectCount(int u, const vector<uint64_t>& cand) const {
        const uint64_t* ap = AdjPtr(u);
        int c = 0;
        for (int i = 0; i < B; i++) c += popc64(ap[i] & cand[i]);
        return c;
    }

    int selectVertex(const vector<uint64_t>& cand, bool randomized) {
        int csz = candPopcount(cand);
        if (csz == 0) return -1;

        if (csz > 250) {
            int bestDeg = -1;
            int chosen = -1;
            int tieCnt = 0;
            for (int u = 0; u < N; u++) {
                if (!inCand(cand, u)) continue;
                int d = deg[u];
                if (d > bestDeg) {
                    bestDeg = d;
                    chosen = u;
                    tieCnt = 1;
                } else if (d == bestDeg) {
                    if (!randomized) {
                        if (u < chosen) chosen = u;
                    } else {
                        tieCnt++;
                        if ((uint64_t)(rng() % tieCnt) == 0) chosen = u;
                    }
                }
            }
            return chosen;
        } else {
            const int T = 8;
            int topV[T];
            int topS[T];
            int sz = 0;
            int minS = INT_MAX, minPos = -1;

            for (int u = 0; u < N; u++) {
                if (!inCand(cand, u)) continue;
                int s = intersectCount(u, cand);
                if (sz < T) {
                    topV[sz] = u;
                    topS[sz] = s;
                    if (s < minS) { minS = s; minPos = sz; }
                    sz++;
                } else if (s > minS) {
                    topV[minPos] = u;
                    topS[minPos] = s;
                    minS = topS[0];
                    minPos = 0;
                    for (int i = 1; i < T; i++) {
                        if (topS[i] < minS) { minS = topS[i]; minPos = i; }
                    }
                } else if (s == minS && !randomized) {
                    // deterministically prefer smaller id in the min slot replacement is not needed; ignore
                }
            }

            int maxS = -1;
            for (int i = 0; i < sz; i++) maxS = max(maxS, topS[i]);

            int chosen = -1;
            int tieCnt = 0;
            for (int i = 0; i < sz; i++) {
                if (topS[i] != maxS) continue;
                int u = topV[i];
                if (chosen == -1) {
                    chosen = u;
                    tieCnt = 1;
                } else {
                    if (!randomized) {
                        if (u < chosen) chosen = u;
                    } else {
                        tieCnt++;
                        if ((uint64_t)(rng() % tieCnt) == 0) chosen = u;
                    }
                }
            }
            return chosen;
        }
    }

    vector<int> buildFromCand(vector<uint64_t> cand, bool randomized) {
        vector<int> clique;
        while (true) {
            int v = selectVertex(cand, randomized);
            if (v < 0) break;
            clique.push_back(v);
            const uint64_t* ap = AdjPtr(v);
            for (int i = 0; i < B; i++) cand[i] &= ap[i];
        }
        return clique;
    }

    vector<int> buildFromStart(int s, bool randomized) {
        vector<int> clique;
        clique.push_back(s);
        vector<uint64_t> cand(B);
        const uint64_t* ap = AdjPtr(s);
        for (int i = 0; i < B; i++) cand[i] = ap[i];

        while (true) {
            int v = selectVertex(cand, randomized);
            if (v < 0) break;
            clique.push_back(v);
            const uint64_t* ap2 = AdjPtr(v);
            for (int i = 0; i < B; i++) cand[i] &= ap2[i];
        }
        return clique;
    }

    vector<int> shakeAndRebuild(const vector<int>& base, int removeCount, bool randomized) {
        if (base.empty()) return buildFromCand(full, randomized);
        removeCount = min(removeCount, (int)base.size());

        vector<char> removed(N, 0);
        for (int r = 0; r < removeCount; r++) {
            int idx = (int)(rng() % base.size());
            int v = base[idx];
            removed[v] = 1;
        }

        vector<int> keep;
        keep.reserve(base.size() - removeCount);
        for (int v : base) if (!removed[v]) keep.push_back(v);

        vector<uint64_t> cand = full;
        for (int v : keep) {
            const uint64_t* ap = AdjPtr(v);
            for (int i = 0; i < B; i++) cand[i] &= ap[i];
        }

        vector<int> clique = keep;
        while (true) {
            int v = selectVertex(cand, randomized);
            if (v < 0) break;
            clique.push_back(v);
            const uint64_t* ap = AdjPtr(v);
            for (int i = 0; i < B; i++) cand[i] &= ap[i];
        }
        return clique;
    }

    inline bool hasEdge(int u, int v) const {
        return (adj[(size_t)u * B + (v >> 6)] >> (v & 63)) & 1ull;
    }

    bool isClique(const vector<int>& c) const {
        for (int i = 0; i < (int)c.size(); i++) {
            for (int j = i + 1; j < (int)c.size(); j++) {
                if (!hasEdge(c[i], c[j])) return false;
            }
        }
        return true;
    }
};

int main() {
    FastScanner fs;
    int N, M;
    if (!fs.readInt(N)) return 0;
    fs.readInt(M);

    Solver solver(N, M);
    for (int i = 0; i < M; i++) {
        int u, v;
        fs.readInt(u); fs.readInt(v);
        --u; --v;
        if (u == v) continue;
        solver.addEdge(u, v);
    }
    solver.computeDegrees();

    vector<int> order(N);
    iota(order.begin(), order.end(), 0);
    sort(order.begin(), order.end(), [&](int a, int b) {
        if (solver.deg[a] != solver.deg[b]) return solver.deg[a] > solver.deg[b];
        return a < b;
    });

    vector<int> best = solver.buildFromCand(solver.full, false);

    int initialTries = min(N, 60);
    for (int i = 0; i < initialTries; i++) {
        int s = order[i];
        auto c = solver.buildFromStart(s, false);
        if (c.size() > best.size()) best.swap(c);
    }

    using Clock = chrono::steady_clock;
    auto t0 = Clock::now();
    auto limit = chrono::milliseconds(1850);

    int topL = min(N, 120);
    uint64_t iter = 0;
    while (Clock::now() - t0 < limit) {
        int mode = (int)(solver.rng() % 10);
        vector<int> c;

        if (mode <= 5) {
            int s = order[(int)(solver.rng() % topL)];
            c = solver.buildFromStart(s, true);
        } else if (mode <= 7) {
            c = solver.buildFromCand(solver.full, true);
        } else {
            int rem = 1 + (int)(solver.rng() % 3);
            c = solver.shakeAndRebuild(best, rem, true);
        }

        if (c.size() > best.size()) best.swap(c);

        if ((++iter & 7ull) == 0ull && !best.empty()) {
            int rem = 1 + (int)(solver.rng() % 2);
            auto cc = solver.shakeAndRebuild(best, rem, true);
            if (cc.size() > best.size()) best.swap(cc);
        }

        if (best.size() == (size_t)N) break;
    }

    if (!solver.isClique(best)) {
        best.clear();
        best.push_back(order[0]);
    }

    vector<int> ans(N, 0);
    for (int v : best) ans[v] = 1;

    string out;
    out.reserve((size_t)N * 2);
    for (int i = 0; i < N; i++) {
        out.push_back(char('0' + ans[i]));
        out.push_back('\n');
    }
    fwrite(out.c_str(), 1, out.size(), stdout);
    return 0;
}