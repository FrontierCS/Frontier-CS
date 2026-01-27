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

struct SplitMix64 {
    uint64_t x;
    explicit SplitMix64(uint64_t seed) : x(seed) {}
    inline uint64_t nextU64() {
        uint64_t z = (x += 0x9e3779b97f4a7c15ULL);
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
        return z ^ (z >> 31);
    }
    inline uint32_t nextU32() { return (uint32_t)nextU64(); }
    inline int nextInt(int bound) { return (int)(nextU64() % (uint64_t)bound); }
};

static inline bool testBit(const vector<uint64_t> &bs, int v) {
    int idx = (v - 1) >> 6;
    int bit = (v - 1) & 63;
    return (bs[idx] >> bit) & 1ULL;
}
static inline void setBit(vector<uint64_t> &bs, int v) {
    int idx = (v - 1) >> 6;
    int bit = (v - 1) & 63;
    bs[idx] |= (1ULL << bit);
}
static inline void clearBit(vector<uint64_t> &bs, int v) {
    int idx = (v - 1) >> 6;
    int bit = (v - 1) & 63;
    bs[idx] &= ~(1ULL << bit);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    FastScanner fs;
    int N, M;
    if (!fs.readInt(N)) return 0;
    fs.readInt(M);

    int W = (N + 63) / 64;
    vector<uint64_t> adjFlat((size_t)(N + 1) * W, 0);
    vector<int> deg(N + 1, 0);

    auto adjRow = [&](int u) -> uint64_t* { return &adjFlat[(size_t)u * W]; };
    auto testAdj = [&](int u, int v) -> bool {
        int wi = (v - 1) >> 6;
        int bi = (v - 1) & 63;
        return (adjRow(u)[wi] >> bi) & 1ULL;
    };
    auto setAdj = [&](int u, int v) {
        int wi = (v - 1) >> 6;
        int bi = (v - 1) & 63;
        uint64_t mask = 1ULL << bi;
        uint64_t &word = adjRow(u)[wi];
        if (!(word & mask)) {
            word |= mask;
            deg[u]++;
        }
    };

    for (int i = 0; i < M; i++) {
        int u, v;
        fs.readInt(u);
        fs.readInt(v);
        if (u == v) continue;
        setAdj(u, v);
        setAdj(v, u);
    }

    uint64_t seed = (uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count();
    SplitMix64 rng(seed);

    auto now = []() { return chrono::steady_clock::now(); };
    auto t0 = now();
    auto deadline = t0 + chrono::milliseconds(1900);

    vector<int> baseOrder(N);
    iota(baseOrder.begin(), baseOrder.end(), 1);

    auto buildOrder = [&](vector<int> &order) {
        vector<uint64_t> key(N + 1);
        for (int i = 1; i <= N; i++) {
            uint64_t r = rng.nextU32();
            key[i] = (uint64_t)(uint32_t)deg[i] << 32 | r;
        }
        order = baseOrder;
        sort(order.begin(), order.end(), [&](int a, int b) { return key[a] < key[b]; });
    };

    auto greedyBuild = [&](const vector<int> &order, vector<uint64_t> &IS, int &sz) {
        IS.assign(W, 0);
        vector<uint64_t> forbidden(W, 0);
        sz = 0;
        for (int v : order) {
            if (!testBit(forbidden, v)) {
                setBit(IS, v);
                setBit(forbidden, v);
                uint64_t *row = adjRow(v);
                for (int k = 0; k < W; k++) forbidden[k] |= row[k];
                sz++;
            }
        }
    };

    auto augmentToMaximal = [&](vector<uint64_t> &IS, vector<char> &inSet, vector<uint64_t> &forbidden,
                               const vector<int> &order) -> int {
        inSet.assign(N + 1, 0);
        int sz = 0;
        for (int v = 1; v <= N; v++) {
            if (testBit(IS, v)) {
                inSet[v] = 1;
                sz++;
            }
        }

        forbidden = IS;
        for (int u = 1; u <= N; u++) {
            if (!inSet[u]) continue;
            uint64_t *row = adjRow(u);
            for (int k = 0; k < W; k++) forbidden[k] |= row[k];
        }

        for (int v : order) {
            if (inSet[v]) continue;
            if (!testBit(forbidden, v)) {
                inSet[v] = 1;
                sz++;
                setBit(IS, v);
                setBit(forbidden, v);
                uint64_t *row = adjRow(v);
                for (int k = 0; k < W; k++) forbidden[k] |= row[k];
            }
        }
        return sz;
    };

    vector<uint64_t> bestIS(W, 0);
    int bestSz = 0;

    vector<int> order;
    vector<int> scanVerts(N);
    iota(scanVerts.begin(), scanVerts.end(), 1);

    vector<uint64_t> IS;
    vector<char> inSet;
    vector<uint64_t> forbidden;

    vector<uint64_t> candIS;
    vector<char> candInSet;
    vector<uint64_t> candForbidden;

    while (now() < deadline) {
        buildOrder(order);

        int curSz = 0;
        greedyBuild(order, IS, curSz);

        // local improvement with (1,1) and (2,1) swaps + augmentation
        curSz = augmentToMaximal(IS, inSet, forbidden, order);

        int steps = 0;
        while (now() < deadline && steps < 200) {
            steps++;
            // shuffle scan order
            for (int i = N - 1; i > 0; i--) {
                int j = rng.nextInt(i + 1);
                swap(scanVerts[i], scanVerts[j]);
            }

            bool improved = false;
            for (int v : scanVerts) {
                if (now() >= deadline) break;
                if (inSet[v]) continue;

                int cnt = 0;
                int neigh[3];

                for (int k = 0; k < W; k++) {
                    uint64_t x = adjRow(v)[k] & IS[k];
                    while (x) {
                        int b = __builtin_ctzll(x);
                        int u = (k << 6) + b + 1;
                        if (u <= N) {
                            if (cnt < 3) neigh[cnt] = u;
                            cnt++;
                            if (cnt > 2) goto next_v;
                        }
                        x &= x - 1;
                    }
                }

                if (cnt == 0) continue; // should not happen if maximal
                if (cnt == 1 || cnt == 2) {
                    candIS = IS;
                    for (int i = 0; i < cnt; i++) clearBit(candIS, neigh[i]);
                    setBit(candIS, v);

                    int candSz = augmentToMaximal(candIS, candInSet, candForbidden, order);
                    if (candSz > curSz) {
                        IS.swap(candIS);
                        inSet.swap(candInSet);
                        forbidden.swap(candForbidden);
                        curSz = candSz;
                        improved = true;
                        break;
                    }
                }

            next_v:
                ;
            }

            if (!improved) break;
        }

        if (curSz > bestSz) {
            bestSz = curSz;
            bestIS = IS;
        }
    }

    // Output
    for (int i = 1; i <= N; i++) {
        cout << (testBit(bestIS, i) ? 1 : 0) << '\n';
    }
    return 0;
}