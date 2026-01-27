#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static const int BUFSIZE = 1 << 20;
    int idx, size;
    char buf[BUFSIZE];
    FastScanner(): idx(0), size(0) {}
    inline char getChar() {
        if (idx >= size) {
            size = (int)fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return EOF;
        }
        return buf[idx++];
    }
    template<typename T>
    bool readInt(T &out) {
        char c;
        T sign = 1;
        T val = 0;
        c = getChar();
        if (c == EOF) return false;
        while (c != '-' && (c < '0' || c > '9')) {
            c = getChar();
            if (c == EOF) return false;
        }
        if (c == '-') {
            sign = -1;
            c = getChar();
        }
        for (; c >= '0' && c <= '9'; c = getChar())
            val = val * 10 + (c - '0');
        out = val * sign;
        return true;
    }
};

struct DynBitset {
    int W;
    vector<uint64_t> w;
    DynBitset() : W(0) {}
    DynBitset(int n) { init(n); }
    inline void init(int n) {
        W = (n + 63) >> 6;
        w.assign(W, 0ULL);
    }
    inline void setBit(int pos) {
        w[pos >> 6] |= (1ULL << (pos & 63));
    }
    inline void clearBit(int pos) {
        w[pos >> 6] &= ~(1ULL << (pos & 63));
    }
    inline bool testBit(int pos) const {
        return (w[pos >> 6] >> (pos & 63)) & 1ULL;
    }
    inline int popcount_and(const DynBitset &other) const {
        int res = 0;
        for (int i = 0; i < W; ++i) {
            res += __builtin_popcountll(w[i] & other.w[i]);
        }
        return res;
    }
};

static inline uint64_t mix64(uint64_t z) {
    z += 0x9e3779b97f4a7c15ULL;
    z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
    z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
    return z ^ (z >> 31);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    FastScanner fs;
    int n;
    int m;
    if (!fs.readInt(n)) return 0;
    fs.readInt(m);

    vector<pair<int,int>> edges1;
    vector<pair<int,int>> edges2;
    edges1.reserve(m);
    edges2.reserve(m);

    vector<int> deg1(n, 0), deg2(n, 0);

    for (int i = 0; i < m; ++i) {
        int u, v;
        fs.readInt(u); fs.readInt(v);
        --u; --v;
        edges1.emplace_back(u, v);
        deg1[u]++; deg1[v]++;
    }
    for (int i = 0; i < m; ++i) {
        int u, v;
        fs.readInt(u); fs.readInt(v);
        --u; --v;
        edges2.emplace_back(u, v);
        deg2[u]++; deg2[v]++;
    }

    int W = (n + 63) >> 6;

    vector<DynBitset> A1(n);
    for (int i = 0; i < n; ++i) A1[i].init(n);
    for (auto &e : edges1) {
        int u = e.first, v = e.second;
        A1[u].setBit(v);
        A1[v].setBit(u);
    }

    vector<vector<int>> adj2(n);
    for (int i = 0; i < n; ++i) adj2[i].reserve(deg2[i]);
    for (auto &e : edges2) {
        int u = e.first, v = e.second;
        adj2[u].push_back(v);
        adj2[v].push_back(u);
    }

    vector<vector<int>> adj1(n);
    for (int i = 0; i < n; ++i) adj1[i].reserve(deg1[i]);
    for (auto &e : edges1) {
        int u = e.first, v = e.second;
        adj1[u].push_back(v);
        adj1[v].push_back(u);
    }

    vector<long long> snd1(n, 0), snd2(n, 0);
    for (auto &e : edges1) {
        int u = e.first, v = e.second;
        snd1[u] += deg1[v];
        snd1[v] += deg1[u];
    }
    for (auto &e : edges2) {
        int u = e.first, v = e.second;
        snd2[u] += deg2[v];
        snd2[v] += deg2[u];
    }

    vector<uint64_t> h1(n, 0), h2(n, 0);
    for (int u = 0; u < n; ++u) {
        uint64_t h = 1469598103934665603ULL;
        for (int v : adj1[u]) {
            h ^= mix64((uint64_t)deg1[v] + 0x9e3779b97f4a7c15ULL);
            h *= 1099511628211ULL;
        }
        h1[u] = h;
    }
    for (int u = 0; u < n; ++u) {
        uint64_t h = 1469598103934665603ULL;
        for (int v : adj2[u]) {
            h ^= mix64((uint64_t)deg2[v] + 0x9e3779b97f4a7c15ULL);
            h *= 1099511628211ULL;
        }
        h2[u] = h;
    }

    vector<int> ord1(n), ord2(n);
    iota(ord1.begin(), ord1.end(), 0);
    iota(ord2.begin(), ord2.end(), 0);

    auto cmp1 = [&](int a, int b) {
        if (deg1[a] != deg1[b]) return deg1[a] > deg1[b];
        if (snd1[a] != snd1[b]) return snd1[a] > snd1[b];
        if (h1[a] != h1[b]) return h1[a] > h1[b];
        return a < b;
    };
    auto cmp2 = [&](int a, int b) {
        if (deg2[a] != deg2[b]) return deg2[a] > deg2[b];
        if (snd2[a] != snd2[b]) return snd2[a] > snd2[b];
        if (h2[a] != h2[b]) return h2[a] > h2[b];
        return a < b;
    };

    sort(ord1.begin(), ord1.end(), cmp1);
    sort(ord2.begin(), ord2.end(), cmp2);

    vector<int> p(n), inv(n);
    for (int i = 0; i < n; ++i) {
        int v2 = ord2[i];
        int v1 = ord1[i];
        p[v2] = v1;
        inv[v1] = v2;
    }

    vector<DynBitset> Mnb(n);
    for (int i = 0; i < n; ++i) Mnb[i].init(n);
    for (auto &e : edges2) {
        int u = e.first, v = e.second;
        Mnb[u].setBit(p[v]);
        Mnb[v].setBit(p[u]);
    }

    long long doubleSum = 0;
    for (int i = 0; i < n; ++i) {
        doubleSum += Mnb[i].popcount_and(A1[p[i]]);
    }
    long long matched = doubleSum / 2;

    auto pop_and = [&](int u, int y) -> int {
        return Mnb[u].popcount_and(A1[y]);
    };
    auto test_edge = [&](int a, int b)->int {
        return A1[a].testBit(b) ? 1 : 0;
    };

    auto deltaSwap = [&](int i, int j) -> long long {
        int a = p[i], b = p[j];
        if (a == b) return 0;
        long long di = (long long)pop_and(i, b) - (long long)pop_and(i, a);
        long long dj = (long long)pop_and(j, a) - (long long)pop_and(j, b);
        long long d = di + dj + 2LL * (long long)test_edge(a, b);
        return d;
    };

    auto applySwap = [&](int i, int j) {
        int a = p[i], b = p[j];
        if (a == b) return;
        // Update Mnb for bit b: remove from neighbors of j, add to neighbors of i
        for (int u : adj2[j]) Mnb[u].clearBit(b);
        for (int u : adj2[i]) Mnb[u].setBit(b);
        // Update Mnb for bit a: remove from neighbors of i, add to neighbors of j
        for (int u : adj2[i]) Mnb[u].clearBit(a);
        for (int u : adj2[j]) Mnb[u].setBit(a);
        // Swap p and inv
        p[i] = b; p[j] = a;
        inv[a] = j; inv[b] = i;
    };

    // Local search
    std::mt19937_64 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count());
    auto t_start = chrono::steady_clock::now();
    int time_limit_ms = 1800; // adjust cautiously
    int sampleCount = max(8, min(64, n / 32 + 8));

    while (true) {
        auto now = chrono::steady_clock::now();
        int elapsed = (int)chrono::duration_cast<chrono::milliseconds>(now - t_start).count();
        if (elapsed > time_limit_ms) break;

        // Randomized greedy improvements
        int i = (int)(rng() % n);
        long long bestDelta = 0;
        int bestJ = -1;
        for (int s = 0; s < sampleCount; ++s) {
            int j = (int)(rng() % n);
            if (j == i) continue;
            long long d = deltaSwap(i, j);
            if (d > bestDelta) {
                bestDelta = d;
                bestJ = j;
            }
        }
        if (bestDelta > 0 && bestJ != -1) {
            matched += bestDelta;
            applySwap(i, bestJ);
        } else {
            // Random single swap attempt to escape local minima
            int j = (int)(rng() % n);
            if (j != i) {
                long long d = deltaSwap(i, j);
                if (d > 0) {
                    matched += d;
                    applySwap(i, j);
                }
            }
        }
    }

    // Output permutation p: G2 vertex i maps to G1 vertex p[i] (1-based)
    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << (p[i] + 1);
    }
    cout << '\n';
    return 0;
}