#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static constexpr size_t BUFSIZE = 1 << 20;
    char buf[BUFSIZE];
    size_t idx = 0, size = 0;

    inline char readChar() {
        if (idx >= size) {
            size = fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }

    template <class T>
    inline bool readInt(T &out) {
        char c;
        do {
            c = readChar();
            if (!c) return false;
        } while (c <= ' ');

        bool neg = false;
        if (c == '-') {
            neg = true;
            c = readChar();
        }
        T val = 0;
        while (c > ' ') {
            val = val * 10 + (c - '0');
            c = readChar();
        }
        out = neg ? -val : val;
        return true;
    }
};

static inline uint64_t splitmix64(uint64_t x) {
    x += 0x9e3779b97f4a7c15ULL;
    x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
    x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
    return x ^ (x >> 31);
}

struct RNG {
    uint64_t s;
    explicit RNG(uint64_t seed) : s(seed) {}
    inline uint64_t nextU64() {
        s += 0x9e3779b97f4a7c15ULL;
        return splitmix64(s);
    }
    inline uint32_t nextU32() { return (uint32_t)nextU64(); }
    inline int nextInt(int mod) { return (int)(nextU64() % (uint64_t)mod); }
};

struct Key {
    int v;
    int deg;
    uint64_t sumDeg;
    uint64_t a, b;
};

int main() {
    FastScanner fs;

    int n;
    int m;
    if (!fs.readInt(n)) return 0;
    fs.readInt(m);

    vector<int> deg1(n, 0), deg2(n, 0);
    vector<pair<int,int>> edges1;
    vector<pair<int,int>> edges2;
    edges1.reserve(m);
    edges2.reserve(m);

    for (int i = 0; i < m; i++) {
        int u, v;
        fs.readInt(u); fs.readInt(v);
        --u; --v;
        edges1.emplace_back(u, v);
        deg1[u]++; deg1[v]++;
    }
    for (int i = 0; i < m; i++) {
        int u, v;
        fs.readInt(u); fs.readInt(v);
        --u; --v;
        edges2.emplace_back(u, v);
        deg2[u]++; deg2[v]++;
    }

    int W = (n + 63) >> 6;
    vector<vector<uint64_t>> adj1mat(n, vector<uint64_t>(W, 0));

    vector<vector<int>> g1(n), g2(n);
    for (int i = 0; i < n; i++) {
        g1[i].reserve(deg1[i]);
        g2[i].reserve(deg2[i]);
    }

    for (auto [u, v] : edges1) {
        g1[u].push_back(v);
        g1[v].push_back(u);
        adj1mat[u][v >> 6] |= 1ULL << (v & 63);
        adj1mat[v][u >> 6] |= 1ULL << (u & 63);
    }
    for (auto [u, v] : edges2) {
        g2[u].push_back(v);
        g2[v].push_back(u);
    }

    auto hasEdge1 = [&](int u, int v) -> int {
        return (int)((adj1mat[u][v >> 6] >> (v & 63)) & 1ULL);
    };

    vector<uint64_t> sumDeg1(n, 0), sumDeg2(n, 0);
    for (int v = 0; v < n; v++) {
        uint64_t s = 0;
        for (int to : g1[v]) s += (uint64_t)deg1[to];
        sumDeg1[v] = s;
    }
    for (int v = 0; v < n; v++) {
        uint64_t s = 0;
        for (int to : g2[v]) s += (uint64_t)deg2[to];
        sumDeg2[v] = s;
    }

    vector<uint64_t> a1(n), b1(n), a2(n), b2(n);
    for (int v = 0; v < n; v++) {
        a1[v] = splitmix64((uint64_t)deg1[v] * 1315423911ULL + sumDeg1[v] + 0x123456789abcdef0ULL);
        b1[v] = splitmix64((uint64_t)deg1[v] * 2654435761ULL + sumDeg1[v] * 97531ULL + 0xfedcba9876543210ULL);
        a2[v] = splitmix64((uint64_t)deg2[v] * 1315423911ULL + sumDeg2[v] + 0x123456789abcdef0ULL);
        b2[v] = splitmix64((uint64_t)deg2[v] * 2654435761ULL + sumDeg2[v] * 97531ULL + 0xfedcba9876543210ULL);
    }

    vector<uint64_t> na1(n), nb1(n), na2(n), nb2(n);
    const int T = 5;
    const uint64_t P1 = 0x9e3779b185ebca87ULL;
    const uint64_t Q1 = 0xc2b2ae3d27d4eb4fULL;
    const uint64_t R1 = 0x165667b19e3779f9ULL;
    const uint64_t P2 = 0xd6e8feb86659fd93ULL;
    const uint64_t Q2 = 0xa0761d6478bd642fULL;
    const uint64_t R2 = 0xe7037ed1a0b428dbULL;

    for (int it = 1; it <= T; it++) {
        uint64_t K1 = 0x243f6a8885a308d3ULL ^ (uint64_t)it * 0x9e3779b97f4a7c15ULL;
        uint64_t K2 = 0x13198a2e03707344ULL ^ (uint64_t)it * 0xbf58476d1ce4e5b9ULL;

        for (int v = 0; v < n; v++) {
            uint64_t sumA = 0, xrA = 0, sumB = 0, xrB = 0;
            for (int to : g1[v]) {
                uint64_t x = a1[to];
                sumA += x;
                xrA ^= x * 0x9e3779b97f4a7c15ULL;
                uint64_t y = b1[to];
                sumB += y;
                xrB ^= y * 0xbf58476d1ce4e5b9ULL;
            }
            na1[v] = splitmix64(a1[v] + sumA * P1 + (xrA ^ K1) + (uint64_t)deg1[v] * R1 + (uint64_t)it * 0x94d049bb133111ebULL);
            nb1[v] = splitmix64(b1[v] + sumB * P2 + (xrB ^ K2) + (uint64_t)deg1[v] * R2 + (uint64_t)it * 0xbf58476d1ce4e5b9ULL);
        }

        for (int v = 0; v < n; v++) {
            uint64_t sumA = 0, xrA = 0, sumB = 0, xrB = 0;
            for (int to : g2[v]) {
                uint64_t x = a2[to];
                sumA += x;
                xrA ^= x * 0x9e3779b97f4a7c15ULL;
                uint64_t y = b2[to];
                sumB += y;
                xrB ^= y * 0xbf58476d1ce4e5b9ULL;
            }
            na2[v] = splitmix64(a2[v] + sumA * P1 + (xrA ^ K1) + (uint64_t)deg2[v] * R1 + (uint64_t)it * 0x94d049bb133111ebULL);
            nb2[v] = splitmix64(b2[v] + sumB * P2 + (xrB ^ K2) + (uint64_t)deg2[v] * R2 + (uint64_t)it * 0xbf58476d1ce4e5b9ULL);
        }

        a1.swap(na1); b1.swap(nb1);
        a2.swap(na2); b2.swap(nb2);
    }

    vector<Key> keys1(n), keys2(n);
    for (int v = 0; v < n; v++) {
        keys1[v] = Key{v, deg1[v], sumDeg1[v], a1[v], b1[v]};
        keys2[v] = Key{v, deg2[v], sumDeg2[v], a2[v], b2[v]};
    }

    auto cmpKey = [](const Key& x, const Key& y) {
        if (x.deg != y.deg) return x.deg < y.deg;
        if (x.sumDeg != y.sumDeg) return x.sumDeg < y.sumDeg;
        if (x.a != y.a) return x.a < y.a;
        return x.b < y.b;
    };

    sort(keys1.begin(), keys1.end(), cmpKey);
    sort(keys2.begin(), keys2.end(), cmpKey);

    vector<int> p(n, 0);
    for (int i = 0; i < n; i++) {
        p[keys2[i].v] = keys1[i].v;
    }

    vector<vector<int>> buckets(n);
    for (int v = 0; v < n; v++) buckets[deg2[v]].push_back(v);

    long long matched = 0;
    for (auto [u, v] : edges2) matched += hasEdge1(p[u], p[v]);

    auto deltaSwap = [&](int a, int b) -> long long {
        int pa = p[a], pb = p[b];
        long long delta = 0;
        for (int x : g2[a]) {
            if (x == b) continue;
            int px = p[x];
            delta += (long long)hasEdge1(pb, px) - (long long)hasEdge1(pa, px);
        }
        for (int x : g2[b]) {
            if (x == a) continue;
            int px = p[x];
            delta += (long long)hasEdge1(pa, px) - (long long)hasEdge1(pb, px);
        }
        return delta;
    };

    double avgDeg = (n ? (2.0 * (double)m) / (double)n : 0.0);
    long long targetVisits = 50000000LL;
    long long denom = (long long)max(1.0, 2.0 * avgDeg + 1.0);
    int iters = (int)min<long long>(200000LL, max<long long>(2000LL, targetVisits / denom));

    RNG rng(splitmix64((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count() ^ (uint64_t)n * 0x9e3779b97f4a7c15ULL ^ (uint64_t)m));

    for (int it = 0; it < iters; it++) {
        int a = rng.nextInt(n);
        int b;
        if ((rng.nextU32() % 10) != 0) {
            auto &bucket = buckets[deg2[a]];
            if ((int)bucket.size() < 2) continue;
            b = bucket[rng.nextInt((int)bucket.size())];
        } else {
            b = rng.nextInt(n);
        }
        if (a == b) continue;

        long long d = deltaSwap(a, b);
        if (d > 0) {
            swap(p[a], p[b]);
            matched += d;
        }
    }

    string out;
    out.reserve((size_t)n * 7);
    for (int i = 0; i < n; i++) {
        if (i) out.push_back(' ');
        int val = p[i] + 1;
        char buf[16];
        int len = 0;
        int x = val;
        while (x > 0) {
            buf[len++] = char('0' + (x % 10));
            x /= 10;
        }
        if (len == 0) buf[len++] = '0';
        while (len--) out.push_back(buf[len]);
    }
    out.push_back('\n');
    fwrite(out.data(), 1, out.size(), stdout);
    return 0;
}