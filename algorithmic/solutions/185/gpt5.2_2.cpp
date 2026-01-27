#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static constexpr size_t BUFSIZE = 1 << 20;
    int idx = 0, size = 0;
    char buf[BUFSIZE];

    inline char read() {
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

struct XorShift64 {
    uint64_t x;
    explicit XorShift64(uint64_t seed = 88172645463325252ull) : x(seed) {}
    inline uint64_t next() {
        x ^= x << 7;
        x ^= x >> 9;
        return x;
    }
    inline uint32_t nextU32() { return (uint32_t)next(); }
    inline int nextInt(int mod) { return (int)(next() % (uint64_t)mod); }
};

static inline int popcount64(uint64_t x) { return __builtin_popcountll(x); }
static inline int ctz64(uint64_t x) { return __builtin_ctzll(x); }

struct GraphBit {
    int n = 0;
    int L = 0;
    uint64_t lastMask = 0;
    vector<uint64_t> adj; // flat: n * L

    GraphBit(int n_ = 0) { init(n_); }

    void init(int n_) {
        n = n_;
        L = (n + 63) >> 6;
        lastMask = (n % 64 == 0) ? ~0ull : ((1ull << (n % 64)) - 1ull);
        adj.assign((size_t)n * L, 0ull);
    }

    inline uint64_t* row(int v) { return &adj[(size_t)v * L]; }
    inline const uint64_t* row(int v) const { return &adj[(size_t)v * L]; }

    inline void addEdge(int u, int v) {
        uint64_t *ru = row(u), *rv = row(v);
        ru[v >> 6] |= 1ull << (v & 63);
        rv[u >> 6] |= 1ull << (u & 63);
    }

    inline bool hasEdge(int u, int v) const {
        const uint64_t *ru = row(u);
        return (ru[v >> 6] >> (v & 63)) & 1ull;
    }

    inline int popcount_and_row_bits(int v, const vector<uint64_t>& bits) const {
        const uint64_t *rv = row(v);
        int s = 0;
        for (int i = 0; i < L; i++) s += popcount64(rv[i] & bits[i]);
        return s;
    }

    inline int popcount_bits(const vector<uint64_t>& bits) const {
        int s = 0;
        for (int i = 0; i < L; i++) s += popcount64(bits[i]);
        return s;
    }

    inline bool testbit(const vector<uint64_t>& bits, int v) const {
        return (bits[v >> 6] >> (v & 63)) & 1ull;
    }

    inline void setbit(vector<uint64_t>& bits, int v) const {
        bits[v >> 6] |= 1ull << (v & 63);
    }

    inline void clrbit(vector<uint64_t>& bits, int v) const {
        bits[v >> 6] &= ~(1ull << (v & 63));
    }

    inline vector<uint64_t> allOnes() const {
        vector<uint64_t> b(L, ~0ull);
        if (L) b[L - 1] &= lastMask;
        return b;
    }
};

static inline double nowSec() {
    using namespace std::chrono;
    return duration<double>(steady_clock::now().time_since_epoch()).count();
}

struct Solver {
    GraphBit g;
    int n = 0;
    vector<int> deg;
    XorShift64 rng;
    double tStart = 0, tLimit = 0;

    Solver(int n_, uint64_t seed, double tLimit_) : g(n_), n(n_), deg(n_, 0), rng(seed), tLimit(tLimit_) {
        tStart = nowSec();
    }

    inline bool timeUp() const { return (nowSec() - tStart) >= tLimit; }

    vector<int> greedyBuild(int topK, int startVertex, int bestKnown) {
        vector<uint64_t> candBits;
        vector<int> candList;
        vector<int> clique;
        clique.reserve(n);

        if (startVertex >= 0) {
            clique.push_back(startVertex);
            candBits.assign(g.row(startVertex), g.row(startVertex) + g.L);
            candBits[g.L - 1] &= g.lastMask;
            candList.reserve(n);
            for (int v = 0; v < n; v++) if (g.testbit(candBits, v)) candList.push_back(v);
        } else {
            candBits = g.allOnes();
            candList.resize(n);
            iota(candList.begin(), candList.end(), 0);
        }

        vector<pair<int,int>> top;
        top.reserve(topK);

        while (!candList.empty()) {
            if ((int)clique.size() + (int)candList.size() <= bestKnown) break;

            top.clear();
            for (int v : candList) {
                int d = g.popcount_and_row_bits(v, candBits);
                if ((int)top.size() < topK) {
                    top.push_back({d, v});
                    int i = (int)top.size() - 1;
                    while (i > 0 && top[i].first > top[i - 1].first) {
                        swap(top[i], top[i - 1]);
                        --i;
                    }
                } else if (d > top.back().first) {
                    top.back() = {d, v};
                    int i = topK - 1;
                    while (i > 0 && top[i].first > top[i - 1].first) {
                        swap(top[i], top[i - 1]);
                        --i;
                    }
                }
            }

            int pickIdx = (int)top.size() == 1 ? 0 : rng.nextInt((int)top.size());
            int chosen = top[pickIdx].second;

            clique.push_back(chosen);

            const uint64_t* rch = g.row(chosen);
            for (int i = 0; i < g.L; i++) candBits[i] &= rch[i];
            candBits[g.L - 1] &= g.lastMask;

            vector<int> nextList;
            nextList.reserve(candList.size());
            for (int v : candList) if (g.testbit(candBits, v)) nextList.push_back(v);
            candList.swap(nextList);
        }
        return clique;
    }

    vector<int> expandMaximalFromBase(const vector<int>& base, int bestKnown) {
        vector<uint64_t> cand = g.allOnes();
        for (int x : base) {
            const uint64_t* rx = g.row(x);
            for (int i = 0; i < g.L; i++) cand[i] &= rx[i];
        }
        cand[g.L - 1] &= g.lastMask;
        for (int x : base) g.clrbit(cand, x);

        vector<int> candList;
        candList.reserve(n);
        for (int v = 0; v < n; v++) if (g.testbit(cand, v)) candList.push_back(v);

        vector<int> clique = base;
        clique.reserve(n);

        while (!candList.empty()) {
            if ((int)clique.size() + (int)candList.size() <= bestKnown) break;

            int bestV = -1, bestD = -1;
            for (int v : candList) {
                int d = g.popcount_and_row_bits(v, cand);
                if (d > bestD) {
                    bestD = d;
                    bestV = v;
                }
            }
            if (bestV < 0) break;

            clique.push_back(bestV);
            const uint64_t* rb = g.row(bestV);
            for (int i = 0; i < g.L; i++) cand[i] &= rb[i];
            cand[g.L - 1] &= g.lastMask;

            vector<int> nextList;
            nextList.reserve(candList.size());
            for (int v : candList) if (g.testbit(cand, v)) nextList.push_back(v);
            candList.swap(nextList);
        }
        return clique;
    }

    vector<int> localImprove1Swap(const vector<int>& initial, int bestKnown) {
        vector<int> clique = initial;
        if ((int)clique.size() <= 1) return clique;

        vector<uint64_t> C(g.L, 0ull);
        for (int v : clique) g.setbit(C, v);

        vector<int> outside;
        outside.reserve(n - (int)clique.size());
        for (int v = 0; v < n; v++) if (!g.testbit(C, v)) outside.push_back(v);

        // sample up to S vertices
        int S = min(240, (int)outside.size());
        for (int i = 0; i < S; i++) {
            int j = i + rng.nextInt((int)outside.size() - i);
            swap(outside[i], outside[j]);
        }
        outside.resize(S);

        bool improved = true;
        int iter = 0;
        while (improved && !timeUp() && iter++ < 25) {
            improved = false;

            for (int u : outside) {
                if (timeUp()) break;
                const uint64_t* au = g.row(u);

                int missCount = 0;
                int missV = -1;
                for (int i = 0; i < g.L; i++) {
                    uint64_t x = C[i] & ~au[i];
                    if (i == g.L - 1) x &= g.lastMask;
                    int pc = popcount64(x);
                    if (pc) {
                        missCount += pc;
                        if (missCount > 1) break;
                        int bit = ctz64(x);
                        missV = (i << 6) + bit;
                    }
                }

                if (missCount == 0) {
                    vector<int> base = clique;
                    base.push_back(u);
                    auto candClique = expandMaximalFromBase(base, bestKnown);
                    if ((int)candClique.size() > (int)clique.size()) {
                        clique.swap(candClique);
                        fill(C.begin(), C.end(), 0ull);
                        for (int v : clique) g.setbit(C, v);
                        improved = true;
                        break;
                    }
                } else if (missCount == 1) {
                    vector<int> base;
                    base.reserve(clique.size());
                    for (int v : clique) if (v != missV) base.push_back(v);
                    base.push_back(u);

                    auto candClique = expandMaximalFromBase(base, bestKnown);
                    if ((int)candClique.size() > (int)clique.size()) {
                        clique.swap(candClique);
                        fill(C.begin(), C.end(), 0ull);
                        for (int v : clique) g.setbit(C, v);
                        improved = true;
                        break;
                    }
                }
            }
        }
        return clique;
    }

    vector<int> solve() {
        // degrees
        for (int v = 0; v < n; v++) {
            int s = 0;
            const uint64_t* rv = g.row(v);
            for (int i = 0; i < g.L; i++) s += popcount64(rv[i]);
            deg[v] = s;
        }

        vector<int> bestClique;

        // deterministic seed run: start from highest-degree vertex
        int startMax = max_element(deg.begin(), deg.end()) - deg.begin();
        {
            auto c = greedyBuild(1, startMax, (int)bestClique.size());
            c = localImprove1Swap(c, (int)bestClique.size());
            if (c.size() > bestClique.size()) bestClique.swap(c);
        }

        // deterministic no fixed start
        {
            auto c = greedyBuild(1, -1, (int)bestClique.size());
            c = localImprove1Swap(c, (int)bestClique.size());
            if (c.size() > bestClique.size()) bestClique.swap(c);
        }

        while (!timeUp()) {
            int mode = rng.nextInt(3);
            int topK = 5 + (int)(rng.next() % 11); // 5..15
            int startV = -1;

            if (mode == 0) {
                startV = rng.nextInt(n);
            } else if (mode == 1) {
                // start from a high-degree vertex among top 30
                vector<int> idx(n);
                iota(idx.begin(), idx.end(), 0);
                int K = min(30, n);
                nth_element(idx.begin(), idx.begin() + K, idx.end(),
                            [&](int a, int b) { return deg[a] > deg[b]; });
                startV = idx[rng.nextInt(K)];
            } else {
                startV = -1;
            }

            auto c = greedyBuild(topK, startV, (int)bestClique.size());

            if ((int)c.size() >= (int)bestClique.size() - 1 && !timeUp()) {
                c = localImprove1Swap(c, (int)bestClique.size());
            }

            if (c.size() > bestClique.size()) bestClique.swap(c);
        }

        return bestClique;
    }
};

int main() {
    FastScanner fs;
    int N, M;
    if (!fs.readInt(N)) return 0;
    fs.readInt(M);

    uint64_t seed = 0x9e3779b97f4a7c15ull;
    seed ^= (uint64_t)N * 0xbf58476d1ce4e5b9ull;
    seed ^= (uint64_t)M * 0x94d049bb133111ebull;
    seed ^= (uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count();

    Solver solver(N, seed, 1.85);
    solver.g.init(N);

    for (int i = 0; i < M; i++) {
        int u, v;
        fs.readInt(u);
        fs.readInt(v);
        --u; --v;
        if (u == v) continue;
        solver.g.addEdge(u, v);
    }

    auto bestClique = solver.solve();

    vector<char> ans(N, '0');
    for (int v : bestClique) ans[v] = '1';

    string out;
    out.reserve((size_t)N * 2);
    for (int i = 0; i < N; i++) {
        out.push_back(ans[i]);
        out.push_back('\n');
    }
    fwrite(out.data(), 1, out.size(), stdout);
    return 0;
}