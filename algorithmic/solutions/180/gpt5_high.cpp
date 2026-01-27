#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static const int S = 1 << 20;
    int idx, size;
    char buf[S];
    FastScanner() : idx(0), size(0) {}
    inline char getChar() {
        if (idx >= size) {
            size = (int)fread(buf, 1, S, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }
    template<typename T>
    bool readInt(T &out) {
        char c; T sign = 1; T val = 0;
        c = getChar();
        if (!c) return false;
        while (c != '-' && (c < '0' || c > '9')) {
            c = getChar();
            if (!c) return false;
        }
        if (c == '-') {
            sign = -1; c = getChar();
        }
        for (; c >= '0' && c <= '9'; c = getChar())
            val = val * 10 + (c - '0');
        out = val * sign;
        return true;
    }
};

static inline uint64_t splitmix64(uint64_t x) {
    x += 0x9e3779b97f4a7c15ULL;
    x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
    x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
    x = x ^ (x >> 31);
    return x;
}
static inline uint64_t rotl64(uint64_t x, int k) {
    return (x << k) | (x >> (64 - k));
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    FastScanner fs;
    int n; long long m;
    if (!fs.readInt(n)) return 0;
    fs.readInt(m);
    int N = n;
    vector<vector<int>> g1(n), g2(n);
    g1.reserve(n);
    g2.reserve(n);
    auto add_edge = [](vector<vector<int>>& g, int u, int v) {
        g[u].push_back(v);
        g[v].push_back(u);
    };
    for (long long i = 0; i < m; ++i) {
        int u, v; fs.readInt(u); fs.readInt(v);
        --u; --v;
        if (u == v) continue;
        add_edge(g1, u, v);
    }
    for (long long i = 0; i < m; ++i) {
        int u, v; fs.readInt(u); fs.readInt(v);
        --u; --v;
        if (u == v) continue;
        add_edge(g2, u, v);
    }

    // Precompute degrees
    vector<int> deg1(n), deg2(n);
    for (int i = 0; i < n; ++i) {
        deg1[i] = (int)g1[i].size();
        deg2[i] = (int)g2[i].size();
    }

    // Build adjacency bitset for G1
    int WORDS = (n + 63) >> 6;
    vector<vector<uint64_t>> bit1(n, vector<uint64_t>(WORDS, 0ULL));
    for (int u = 0; u < n; ++u) {
        for (int v : g1[u]) {
            bit1[u][v >> 6] |= (1ULL << (v & 63));
        }
    }
    auto has1 = [&](int u, int v) -> int {
        return (bit1[u][v >> 6] >> (v & 63)) & 1ULL;
    };

    // Feature computation: degree, sum of neighbor degrees, WL-like hashes
    auto compute_features = [&](const vector<vector<int>>& g, const vector<int>& deg) {
        vector<uint64_t> color(n);
        for (int i = 0; i < n; ++i) {
            color[i] = splitmix64((uint64_t)deg[i] * 0x9e3779b97f4a7c15ULL + (uint64_t)i);
        }
        // Sum of neighbor degrees
        vector<long long> sumdeg(n, 0);
        vector<long long> sumdeg2(n, 0);
        for (int i = 0; i < n; ++i) {
            long long s = 0, s2 = 0;
            for (int j : g[i]) {
                s += deg[j];
                s2 += 1LL * deg[j] * deg[j];
            }
            sumdeg[i] = s;
            sumdeg2[i] = s2;
        }
        const int iters = 3;
        uint64_t baseSalt = splitmix64(n * 123456789ULL + g.size());
        for (int it = 0; it < iters; ++it) {
            vector<uint64_t> nc(n);
            uint64_t salt1 = splitmix64(baseSalt + it * 0x9e3779b97f4a7c15ULL + 0x1234567890abcdefULL);
            uint64_t salt2 = splitmix64(baseSalt + it * 0x85ebca6b + 0xfaa8ff9b);
            for (int i = 0; i < n; ++i) {
                uint64_t add = splitmix64(color[i] + salt1) + (uint64_t)deg[i] * 0x9e3779b97f4a7c15ULL;
                uint64_t xr = splitmix64(color[i] + salt2);
                uint64_t mn = UINT64_MAX;
                uint64_t mx = 0;
                for (int j : g[i]) {
                    uint64_t hv = splitmix64(color[j] + salt1);
                    add += hv;
                    xr ^= rotl64(hv, (j % 31) + 1);
                    mn = min(mn, hv);
                    mx = max(mx, hv);
                }
                uint64_t mix = splitmix64(add ^ (xr + 0x9e3779b97f4a7c15ULL) ^ (mn * 0xbf58476d1ce4e5b9ULL) ^ (mx * 0x94d049bb133111ebULL));
                mix ^= (uint64_t)sumdeg[i] * 0x27d4eb2d;
                mix ^= rotl64((uint64_t)sumdeg2[i], (i % 23) + 1);
                nc[i] = mix;
            }
            color.swap(nc);
        }
        struct Feature {
            int deg;
            long long sdeg;
            uint64_t col;
            int id;
        };
        vector<Feature> feats(n);
        for (int i = 0; i < n; ++i) {
            feats[i] = Feature{deg[i], sumdeg[i], color[i], i};
        }
        return feats;
    };

    auto feats1 = compute_features(g1, deg1);
    auto feats2 = compute_features(g2, deg2);

    uint64_t seed = chrono::steady_clock::now().time_since_epoch().count();
    auto rnd64 = [&](uint64_t x) { return splitmix64(x + seed); };

    // Sort order for both graphs
    auto cmpFeat = [&](const auto& A, const auto& B) {
        if (A.deg != B.deg) return A.deg < B.deg;
        if (A.sdeg != B.sdeg) return A.sdeg < B.sdeg;
        if (A.col != B.col) return A.col < B.col;
        // random tie-breaker to diversify
        uint64_t ra = rnd64(A.id);
        uint64_t rb = rnd64(B.id);
        return ra < rb;
    };
    vector<int> ord1(n), ord2(n);
    {
        vector<decltype(feats1[0])> f1 = feats1, f2 = feats2;
        stable_sort(f1.begin(), f1.end(), cmpFeat);
        stable_sort(f2.begin(), f2.end(), cmpFeat);
        for (int i = 0; i < n; ++i) {
            ord1[i] = f1[i].id;
            ord2[i] = f2[i].id;
        }
    }

    // Initial mapping: p[u] is image in G1 of vertex u in G2
    vector<int> p(n, -1);
    vector<int> inv(n, -1);
    for (int i = 0; i < n; ++i) {
        int u2 = ord2[i];
        int u1 = ord1[i];
        p[u2] = u1;
        inv[u1] = u2;
    }

    // Prepare edges list for G2 for scoring
    vector<pair<int,int>> edges2;
    edges2.reserve(m);
    for (int u = 0; u < n; ++u) {
        for (int v : g2[u]) if (u < v) {
            edges2.emplace_back(u, v);
        }
    }

    auto compute_matched = [&](const vector<int>& mapP) -> long long {
        long long matched = 0;
        for (auto &e : edges2) {
            int u = e.first, v = e.second;
            int iu = mapP[u];
            int iv = mapP[v];
            matched += has1(iu, iv);
        }
        return matched;
    };

    long long matched = compute_matched(p);

    // Local search: hill climbing with random swaps and delta evaluation
    auto delta_swap = [&](int a, int b) -> int {
        if (a == b) return 0;
        int pa = p[a], pb = p[b];
        int d = 0;
        // neighbors of a
        for (int t : g2[a]) {
            if (t == b) continue;
            int pt = p[t];
            d += has1(pb, pt) - has1(pa, pt);
        }
        // neighbors of b
        for (int t : g2[b]) {
            if (t == a) continue;
            int pt = p[t];
            d += has1(pa, pt) - has1(pb, pt);
        }
        return d;
    };

    auto do_swap = [&](int a, int b) {
        int pa = p[a], pb = p[b];
        swap(p[a], p[b]);
        inv[pa] = b;
        inv[pb] = a;
    };

    // RNG for local search
    uint64_t rngstate = seed ^ 0x9e3779b97f4a7c15ULL;
    auto rng = [&]() -> uint64_t {
        rngstate += 0x9e3779b97f4a7c15ULL;
        return splitmix64(rngstate);
    };
    auto randint = [&](int lim) -> int { return (int)(rng() % (uint64_t)lim); };

    int avgDeg2 = (int)((2LL * m) / max(1, n));
    int K = max(5, min(50, 2000 / max(1, avgDeg2)));
    int passes = 0;

    auto start = chrono::steady_clock::now();
    const int TIME_LIMIT_MS = 1800; // adjust conservatively
    auto time_left = [&]() -> bool {
        auto now = chrono::steady_clock::now();
        return chrono::duration_cast<chrono::milliseconds>(now - start).count() < TIME_LIMIT_MS;
    };

    vector<int> order(n);
    iota(order.begin(), order.end(), 0);

    while (time_left()) {
        ++passes;
        shuffle(order.begin(), order.end(), std::mt19937_64(seed + passes));
        bool improved_any = false;
        for (int idx = 0; idx < n && time_left(); ++idx) {
            int a = order[idx];
            int best_b = -1;
            int best_delta = 0;
            // Try K random candidates
            for (int t = 0; t < K; ++t) {
                int b = randint(n);
                if (b == a) continue;
                // Prefer similar degree pairs (optional)
                if ((deg2[a] != deg2[b]) && (rng() & 3ULL) == 0ULL) {
                    // 25% of time allow different degree; otherwise resample once
                    b = randint(n);
                    if (b == a) continue;
                }
                int d = delta_swap(a, b);
                if (d > 0) {
                    do_swap(a, b);
                    matched += d;
                    improved_any = true;
                    // Immediate accept first positive delta
                    goto next_vertex;
                } else if (d > best_delta) {
                    best_delta = d;
                    best_b = b;
                }
            }
            // If no positive, occasionally accept zero or small negative if time allows? Skip to keep safe.
            // Could attempt swapping with best_b if zero delta and random chance
            next_vertex:;
        }
        if (!improved_any) break;
    }

    // Small random improvement loop
    int randomTries = 3 * n;
    for (int t = 0; t < randomTries && time_left(); ++t) {
        int a = randint(n);
        int b = randint(n);
        if (a == b) continue;
        int d = delta_swap(a, b);
        if (d > 0) {
            do_swap(a, b);
            matched += d;
        }
    }

    // Output mapping (1-based)
    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << (p[i] + 1);
    }
    cout << '\n';
    return 0;
}