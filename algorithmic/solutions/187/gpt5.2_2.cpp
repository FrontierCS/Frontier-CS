#include <bits/stdc++.h>
using namespace std;

static inline uint64_t splitmix64(uint64_t &x) {
    x += 0x9e3779b97f4a7c15ULL;
    uint64_t z = x;
    z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
    z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
    return z ^ (z >> 31);
}

struct RNG {
    uint64_t state;
    explicit RNG(uint64_t seed = 0) : state(seed) {}
    inline uint64_t nextU64() { return splitmix64(state); }
    inline uint32_t nextU32() { return (uint32_t)nextU64(); }
    inline int nextInt(int lo, int hi) { // inclusive
        return lo + (int)(nextU64() % (uint64_t)(hi - lo + 1));
    }
    template <class T>
    void shuffleVec(vector<T> &a) {
        for (int i = (int)a.size() - 1; i > 0; --i) {
            int j = (int)(nextU64() % (uint64_t)(i + 1));
            swap(a[i], a[j]);
        }
    }
};

static constexpr int MAXW = 8;

static inline int popcount_u64(uint64_t x) {
    return __builtin_popcountll(x);
}

static inline int ctz_u64(uint64_t x) {
    return __builtin_ctzll(x);
}

struct Solver {
    int N, M;
    int wordsV; // for vertex bitsets: N bits
    int wordsC; // for color masks: (N+1) bits (colors 0..N)
    uint64_t maskLastV;
    uint64_t maskLastC;
    vector<array<uint64_t, MAXW>> adj;     // original adjacency
    vector<array<uint64_t, MAXW>> compAdj; // complement adjacency
    vector<int> degComp;

    Solver(int n, int m) : N(n), M(m) {
        wordsV = (N + 63) / 64;
        wordsC = (N + 1 + 63) / 64;

        maskLastV = (N % 64 == 0) ? ~0ULL : ((1ULL << (N % 64)) - 1ULL);
        int bitsC = (N + 1) - (wordsC - 1) * 64;
        maskLastC = (bitsC == 64) ? ~0ULL : ((1ULL << bitsC) - 1ULL);

        adj.assign(N, {});
        compAdj.assign(N, {});
        degComp.assign(N, 0);
        for (int i = 0; i < N; i++) {
            for (int w = 0; w < MAXW; w++) adj[i][w] = 0;
        }
    }

    inline void addEdge(int u, int v) { // 0-indexed
        adj[u][v >> 6] |= (1ULL << (v & 63));
        adj[v][u >> 6] |= (1ULL << (u & 63));
    }

    void buildComplement() {
        for (int i = 0; i < N; i++) {
            for (int w = 0; w < wordsV; w++) {
                uint64_t m = (w == wordsV - 1) ? maskLastV : ~0ULL;
                compAdj[i][w] = (~adj[i][w]) & m;
            }
            // clear self-loop in complement
            compAdj[i][i >> 6] &= ~(1ULL << (i & 63));
            // compute degree in complement
            int d = 0;
            for (int w = 0; w < wordsV; w++) d += popcount_u64(compAdj[i][w]);
            degComp[i] = d;
            // clear unused words (safety)
            for (int w = wordsV; w < MAXW; w++) compAdj[i][w] = 0;
        }
    }

    inline int findSmallestAvailableColor(const array<uint64_t, MAXW> &mask) const {
        for (int w = 0; w < wordsC; w++) {
            uint64_t inv = ~mask[w];
            if (w == 0) inv &= ~1ULL; // disallow color 0
            if (w == wordsC - 1) inv &= maskLastC;
            if (inv) return w * 64 + ctz_u64(inv);
        }
        return N; // fallback (shouldn't happen)
    }

    pair<vector<int>, int> dsaturColoring(RNG &rng) const {
        vector<int> color(N, 0);
        vector<int> satDeg(N, 0);

        vector<array<uint64_t, MAXW>> neighColorMask(N);
        for (int i = 0; i < N; i++) {
            for (int w = 0; w < MAXW; w++) neighColorMask[i][w] = 0;
        }

        int uncolored = N;
        int maxColor = 0;

        while (uncolored) {
            int best = -1;
            for (int i = 0; i < N; i++) {
                if (color[i] != 0) continue;
                if (best == -1) {
                    best = i;
                    continue;
                }
                if (satDeg[i] > satDeg[best]) best = i;
                else if (satDeg[i] == satDeg[best]) {
                    if (degComp[i] > degComp[best]) best = i;
                    else if (degComp[i] == degComp[best]) {
                        if (rng.nextU64() & 1ULL) best = i;
                    }
                }
            }

            int v = best;
            int c = findSmallestAvailableColor(neighColorMask[v]);
            color[v] = c;
            if (c > maxColor) maxColor = c;
            uncolored--;

            int cw = c >> 6;
            uint64_t cb = 1ULL << (c & 63);

            // update neighbors (in complement) that are still uncolored
            for (int w = 0; w < wordsV; w++) {
                uint64_t x = compAdj[v][w];
                while (x) {
                    int b = ctz_u64(x);
                    int u = (w << 6) + b;
                    x &= x - 1;
                    if (u >= N) continue;
                    if (color[u] != 0) continue;
                    if ((neighColorMask[u][cw] & cb) == 0) {
                        neighColorMask[u][cw] |= cb;
                        satDeg[u]++;
                    }
                }
            }
        }

        return {color, maxColor};
    }

    inline bool intersectionEmptyVertexColorClass(int v, const array<uint64_t, MAXW> &classBits) const {
        for (int w = 0; w < wordsV; w++) {
            if (compAdj[v][w] & classBits[w]) return false;
        }
        return true;
    }

    int compressColors(vector<int> &color) const {
        int K = 0;
        for (int i = 0; i < N; i++) K = max(K, color[i]);
        vector<int> used(K + 1, 0);
        for (int i = 0; i < N; i++) used[color[i]] = 1;

        vector<int> mp(K + 1, 0);
        int nk = 0;
        for (int c = 1; c <= K; c++) if (used[c]) mp[c] = ++nk;
        for (int i = 0; i < N; i++) color[i] = mp[color[i]];
        return nk;
    }

    int improveRecolor(vector<int> &color, int K, RNG &rng) const {
        vector<int> ord(N);
        iota(ord.begin(), ord.end(), 0);

        for (int pass = 0; pass < 3; pass++) {
            vector<array<uint64_t, MAXW>> classBits(K + 1);
            for (int c = 0; c <= K; c++) {
                for (int w = 0; w < MAXW; w++) classBits[c][w] = 0;
            }
            for (int v = 0; v < N; v++) {
                int c = color[v];
                classBits[c][v >> 6] |= (1ULL << (v & 63));
            }

            rng.shuffleVec(ord);
            sort(ord.begin(), ord.end(), [&](int a, int b) {
                if (color[a] != color[b]) return color[a] > color[b];
                if (degComp[a] != degComp[b]) return degComp[a] > degComp[b];
                return a < b;
            });

            for (int v : ord) {
                int cur = color[v];
                for (int c = 1; c < cur; c++) {
                    if (intersectionEmptyVertexColorClass(v, classBits[c])) {
                        // move v from cur -> c
                        classBits[cur][v >> 6] &= ~(1ULL << (v & 63));
                        classBits[c][v >> 6] |= (1ULL << (v & 63));
                        color[v] = c;
                        break;
                    }
                }
            }

            K = compressColors(color);
            if (K <= 1) break;
        }
        return K;
    }

    vector<int> solve() {
        buildComplement();

        vector<int> bestColor(N, 1);
        int bestK = N;

        auto t0 = chrono::high_resolution_clock::now();
        auto elapsedMs = [&]() -> long long {
            auto t1 = chrono::high_resolution_clock::now();
            return chrono::duration_cast<chrono::milliseconds>(t1 - t0).count();
        };

        uint64_t baseSeed = (uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count();
        RNG rng0(baseSeed);

        int iter = 0;
        while (elapsedMs() < 1850) {
            uint64_t seed = rng0.nextU64() ^ (0xD1B54A32D192ED03ULL + (uint64_t)iter * 0x9E3779B97F4A7C15ULL);
            RNG rng(seed);

            auto [col, K] = dsaturColoring(rng);
            K = compressColors(col);
            K = improveRecolor(col, K, rng);

            if (K < bestK) {
                bestK = K;
                bestColor = std::move(col);
                if (bestK == 1) break;
            }
            iter++;
        }

        // final compression safety
        bestK = compressColors(bestColor);
        (void)bestK;
        return bestColor;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    if (!(cin >> N >> M)) return 0;

    Solver solver(N, M);
    for (int i = 0; i < M; i++) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        solver.addEdge(u, v);
    }

    vector<int> ans = solver.solve();
    for (int i = 0; i < N; i++) {
        cout << ans[i] << "\n";
    }
    return 0;
}