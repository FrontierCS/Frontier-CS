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

    inline bool readInt(int &out) {
        char c;
        do {
            c = read();
            if (!c) return false;
        } while (c <= ' ');

        int sign = 1;
        if (c == '-') { sign = -1; c = read(); }

        int x = 0;
        while (c > ' ') {
            x = x * 10 + (c - '0');
            c = read();
        }
        out = x * sign;
        return true;
    }
};

struct RNG {
    uint64_t x;
    explicit RNG(uint64_t seed = 0) : x(seed) {}
    static uint64_t splitmix64(uint64_t &s) {
        uint64_t z = (s += 0x9e3779b97f4a7c15ULL);
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
        return z ^ (z >> 31);
    }
    inline uint64_t nextU64() { return splitmix64(x); }
    inline uint32_t nextU32() { return (uint32_t)nextU64(); }
    inline int nextInt(int bound) { return (int)(nextU64() % (uint64_t)bound); }
};

struct Solver {
    int N, M, L;
    vector<uint64_t> adj;   // N * L
    vector<int> deg;
    vector<uint64_t> allOnes;
    vector<int> mark;
    int stamp = 1;
    RNG rng;

    inline const uint64_t* row(int v) const { return &adj[(size_t)v * (size_t)L]; }
    inline uint64_t* rowMut(int v) { return &adj[(size_t)v * (size_t)L]; }

    static inline bool testBit(const uint64_t* b, int idx) {
        return (b[idx >> 6] >> (idx & 63)) & 1ULL;
    }
    static inline bool testBitVec(const vector<uint64_t>& b, int idx) {
        return (b[idx >> 6] >> (idx & 63)) & 1ULL;
    }
    static inline void setBit(uint64_t* b, int idx) {
        b[idx >> 6] |= (1ULL << (idx & 63));
    }
    static inline void clearBitVec(vector<uint64_t>& b, int idx) {
        b[idx >> 6] &= ~(1ULL << (idx & 63));
    }
    static inline void setBitVec(vector<uint64_t>& b, int idx) {
        b[idx >> 6] |= (1ULL << (idx & 63));
    }

    inline int popcount_and(const uint64_t* a, const uint64_t* b) const {
        int s = 0;
        for (int i = 0; i < L; i++) s += __builtin_popcountll(a[i] & b[i]);
        return s;
    }

    inline int popcount_vec(const vector<uint64_t>& b) const {
        int s = 0;
        for (int i = 0; i < L; i++) s += __builtin_popcountll(b[i]);
        return s;
    }

    vector<int> bitsToList(const vector<uint64_t>& b) const {
        vector<int> res;
        for (int i = 0; i < L; i++) {
            uint64_t x = b[i];
            while (x) {
                int t = __builtin_ctzll(x);
                int v = (i << 6) + t;
                if (v < N) res.push_back(v);
                x &= x - 1;
            }
        }
        return res;
    }

    vector<int> sampleFromList(const vector<int>& lst, int t) {
        if ((int)lst.size() <= t) return lst;
        vector<int> sample;
        sample.reserve(t);
        stamp++;
        if (stamp == INT_MAX) {
            fill(mark.begin(), mark.end(), 0);
            stamp = 1;
        }
        while ((int)sample.size() < t) {
            int u = lst[rng.nextInt((int)lst.size())];
            if (mark[u] != stamp) {
                mark[u] = stamp;
                sample.push_back(u);
            }
        }
        return sample;
    }

    int pickBestVertex(const vector<int>& candList, const vector<uint64_t>& candBits, bool fullEval, int sampleT) {
        vector<int> eval = fullEval ? candList : sampleFromList(candList, min(sampleT, (int)candList.size()));
        int bestScore = -1;
        static vector<int> bestVerts;
        bestVerts.clear();
        const uint64_t* candPtr = candBits.data();
        for (int u : eval) {
            int sc = popcount_and(row(u), candPtr);
            if (sc > bestScore) {
                bestScore = sc;
                bestVerts.clear();
                bestVerts.push_back(u);
            } else if (sc == bestScore) {
                bestVerts.push_back(u);
            }
        }
        return bestVerts[rng.nextInt((int)bestVerts.size())];
    }

    void expandGreedy(vector<int>& clique, vector<uint64_t>& cliqueMask,
                      vector<uint64_t>& candBits, vector<int>& candList,
                      bool fullEval, int sampleT) {
        vector<int> nextList;
        nextList.reserve(candList.size());
        while (!candList.empty()) {
            int v = pickBestVertex(candList, candBits, fullEval || (int)candList.size() <= 80, sampleT);
            clique.push_back(v);
            setBitVec(cliqueMask, v);

            const uint64_t* Av = row(v);
            for (int i = 0; i < L; i++) candBits[i] &= Av[i];
            clearBitVec(candBits, v);

            nextList.clear();
            nextList.reserve(candList.size());
            for (int u : candList) {
                if (u != v && testBit(Av, u)) nextList.push_back(u);
            }
            candList.swap(nextList);
        }
    }

    void buildClique(vector<int>& clique, vector<uint64_t>& cliqueMask, bool fullEval, int sampleT) {
        clique.clear();
        fill(cliqueMask.begin(), cliqueMask.end(), 0ULL);

        vector<uint64_t> candBits = allOnes;
        vector<int> candList(N);
        iota(candList.begin(), candList.end(), 0);

        // Occasionally force a random first pick for diversification
        if (!fullEval && N > 0 && (rng.nextU32() % 7) == 0) {
            int v0 = rng.nextInt(N);
            clique.push_back(v0);
            setBitVec(cliqueMask, v0);
            const uint64_t* A0 = row(v0);
            for (int i = 0; i < L; i++) candBits[i] &= A0[i];
            clearBitVec(candBits, v0);
            vector<int> nextList;
            nextList.reserve(N);
            for (int u = 0; u < N; u++) {
                if (u != v0 && testBit(A0, u)) nextList.push_back(u);
            }
            candList.swap(nextList);
            expandGreedy(clique, cliqueMask, candBits, candList, fullEval, sampleT);
            return;
        }

        expandGreedy(clique, cliqueMask, candBits, candList, fullEval, sampleT);
    }

    void improveClique(vector<int>& clique, vector<uint64_t>& cliqueMask, int maxRounds) {
        if (clique.empty()) return;
        vector<int> pos(N, -1);

        for (int round = 0; round < maxRounds; round++) {
            int k = (int)clique.size();
            if (k <= 1) break;

            for (int i = 0; i < N; i++) pos[i] = -1;
            for (int i = 0; i < k; i++) pos[clique[i]] = i;

            // prefix/suffix intersections for "all except i"
            vector<uint64_t> prefix((size_t)(k + 1) * (size_t)L);
            vector<uint64_t> suffix((size_t)(k + 1) * (size_t)L);

            for (int j = 0; j < L; j++) prefix[j] = allOnes[j];
            for (int i = 0; i < k; i++) {
                const uint64_t* Ai = row(clique[i]);
                uint64_t* dst = &prefix[(size_t)(i + 1) * (size_t)L];
                const uint64_t* src = &prefix[(size_t)i * (size_t)L];
                for (int j = 0; j < L; j++) dst[j] = src[j] & Ai[j];
            }

            uint64_t* sufK = &suffix[(size_t)k * (size_t)L];
            for (int j = 0; j < L; j++) sufK[j] = allOnes[j];
            for (int i = k - 1; i >= 0; i--) {
                const uint64_t* Ai = row(clique[i]);
                uint64_t* dst = &suffix[(size_t)i * (size_t)L];
                const uint64_t* src = &suffix[(size_t)(i + 1) * (size_t)L];
                for (int j = 0; j < L; j++) dst[j] = src[j] & Ai[j];
            }

            int bestU = -1, bestRemIdx = -1, bestPot = 0;
            vector<uint64_t> bestCand(L, 0);

            const uint64_t* cliquePtr = cliqueMask.data();

            for (int u = 0; u < N; u++) {
                if (testBit(cliquePtr, u)) continue;
                const uint64_t* Au = row(u);
                int neigh = popcount_and(Au, cliquePtr);
                if (neigh != k - 1) continue;

                int w = -1;
                for (int j = 0; j < L; j++) {
                    uint64_t x = cliquePtr[j] & ~Au[j];
                    if (x) {
                        w = (j << 6) + __builtin_ctzll(x);
                        break;
                    }
                }
                if (w < 0 || w >= N) continue;
                int ridx = pos[w];
                if (ridx < 0) continue;

                int wWord = w >> 6, wBit = w & 63;
                int uWord = u >> 6, uBit = u & 63;

                const uint64_t* pre = &prefix[(size_t)ridx * (size_t)L];
                const uint64_t* suf = &suffix[(size_t)(ridx + 1) * (size_t)L];

                int pot = 0;
                uint64_t tmp;
                for (int j = 0; j < L; j++) {
                    uint64_t base = pre[j] & suf[j];
                    uint64_t val = base & Au[j];

                    uint64_t exc = cliquePtr[j];
                    if (j == wWord) exc &= ~(1ULL << wBit);
                    if (j == uWord) exc |= (1ULL << uBit);

                    val &= ~exc;
                    tmp = val;
                    pot += __builtin_popcountll(tmp);
                    if (pot + (L - j - 1) * 64 < bestPot) {
                        // weak pruning (safe upper bound), optional but cheap
                    }
                }

                if (pot > bestPot) {
                    bestPot = pot;
                    bestU = u;
                    bestRemIdx = ridx;

                    for (int j = 0; j < L; j++) {
                        uint64_t base = pre[j] & suf[j];
                        uint64_t val = base & Au[j];

                        uint64_t exc = cliquePtr[j];
                        if (j == wWord) exc &= ~(1ULL << wBit);
                        if (j == uWord) exc |= (1ULL << uBit);

                        bestCand[j] = val & ~exc;
                    }
                }
            }

            if (bestU == -1 || bestPot <= 0) break;

            int removedV = clique[bestRemIdx];

            // apply swap
            clique[bestRemIdx] = bestU;
            cliqueMask[removedV >> 6] &= ~(1ULL << (removedV & 63));
            cliqueMask[bestU >> 6] |= (1ULL << (bestU & 63));

            // expand from bestCand
            vector<uint64_t> candBits = bestCand;
            vector<int> candList = bitsToList(candBits);

            // Small chance to fully evaluate during expansion
            bool fullEval = ((rng.nextU32() % 11) == 0);
            int sampleT = 60;
            expandGreedy(clique, cliqueMask, candBits, candList, fullEval, sampleT);
        }
    }

    void solve() {
        FastScanner fs;
        fs.readInt(N);
        fs.readInt(M);
        L = (N + 63) >> 6;
        adj.assign((size_t)N * (size_t)L, 0ULL);
        deg.assign(N, 0);

        allOnes.assign(L, ~0ULL);
        if (L > 0) {
            int r = N & 63;
            if (r != 0) allOnes[L - 1] = (1ULL << r) - 1;
        }

        mark.assign(N, 0);

        for (int i = 0; i < M; i++) {
            int u, v;
            fs.readInt(u);
            fs.readInt(v);
            --u; --v;
            if (u < 0 || v < 0 || u >= N || v >= N || u == v) continue;
            uint64_t* Au = rowMut(u);
            uint64_t* Av = rowMut(v);
            int vw = v >> 6, vb = v & 63;
            int uw = u >> 6, ub = u & 63;

            uint64_t bv = 1ULL << vb;
            if ((Au[vw] & bv) == 0) { Au[vw] |= bv; deg[u]++; }
            uint64_t bu = 1ULL << ub;
            if ((Av[uw] & bu) == 0) { Av[uw] |= bu; deg[v]++; }
        }

        uint64_t seed = (uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count();
        rng = RNG(seed);

        vector<int> bestClique, clique;
        vector<uint64_t> bestMask(L, 0), cliqueMask(L, 0);

        // Baseline: one full-eval run
        buildClique(clique, cliqueMask, true, 80);
        improveClique(clique, cliqueMask, 12);
        bestClique = clique;
        bestMask = cliqueMask;

        auto start = chrono::steady_clock::now();
        auto deadline = start + chrono::milliseconds(1850);

        int it = 0;
        while (chrono::steady_clock::now() < deadline) {
            bool fullEval = false;
            int sampleT = (it % 3 == 0) ? 60 : 45;

            buildClique(clique, cliqueMask, fullEval, sampleT);
            improveClique(clique, cliqueMask, 8);

            if (clique.size() > bestClique.size()) {
                bestClique = clique;
                bestMask = cliqueMask;
            }
            it++;
        }

        string out;
        out.reserve((size_t)N * 2);
        for (int i = 0; i < N; i++) {
            out.push_back(testBitVec(bestMask, i) ? '1' : '0');
            out.push_back('\n');
        }
        fwrite(out.c_str(), 1, out.size(), stdout);
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    Solver s;
    s.solve();
    return 0;
}