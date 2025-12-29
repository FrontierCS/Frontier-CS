#include <bits/stdc++.h>
using namespace std;

using ull = unsigned long long;
using ld = long double;

static inline ull splitmix64(ull x) {
    x += 0x9e3779b97f4a7c15ULL;
    x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
    x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
    return x ^ (x >> 31);
}

static inline int dnaIdx(char c) {
    switch (c) {
        case 'A': return 0;
        case 'C': return 1;
        case 'G': return 2;
        case 'T': return 3;
        default: return -1;
    }
}

static ld solve_small_n_5ary(int n, int m, istream &in) {
    const ull LIM5 = 50000000ULL;
    ull states = 1;
    for (int i = 0; i < n; i++) states *= 5ULL;

    vector<ull> pow5(n + 1, 1);
    for (int i = 1; i <= n; i++) pow5[i] = pow5[i - 1] * 5ULL;

    vector<uint8_t> f(states, 0);

    for (int i = 0; i < m; i++) {
        string s;
        in >> s;
        ull idx = 0;
        for (int p = 0; p < n; p++) {
            int d;
            if (s[p] == '?') d = 4;
            else d = dnaIdx(s[p]);
            idx = idx * 5ULL + (ull)d;
        }
        f[idx] = 1;
    }

    for (int pos = 0; pos < n; pos++) {
        ull stride = pow5[n - pos - 1]; // 5^(n-pos-1)
        ull block = stride * 5ULL;
        for (ull base = 0; base < states; base += block) {
            ull qBase = base + 4ULL * stride;
            for (ull off = 0; off < stride; off++) {
                if (f[qBase + off]) {
                    f[base + off] = 1;
                    f[base + stride + off] = 1;
                    f[base + 2ULL * stride + off] = 1;
                    f[base + 3ULL * stride + off] = 1;
                }
            }
        }
    }

    ull total4 = 1;
    for (int i = 0; i < n; i++) total4 *= 4ULL;

    ull cnt = 0;
    for (ull code = 0; code < total4; code++) {
        ull tmp = code;
        ull idx5 = 0;
        // last position weight pow5[0]=1, first weight pow5[n-1]
        for (int p = n - 1; p >= 0; --p) {
            ull d = tmp & 3ULL;
            tmp >>= 2ULL;
            idx5 += d * pow5[n - 1 - p];
        }
        cnt += (ull)f[idx5];
    }

    return (ld)cnt / (ld)total4;
}

struct U64Hash {
    size_t operator()(ull x) const noexcept {
        static const ull FIXED_RANDOM = chrono::steady_clock::now().time_since_epoch().count();
        return (size_t)splitmix64(x + FIXED_RANDOM);
    }
};

struct Key2 {
    ull lo, hi;
    bool operator==(const Key2 &o) const noexcept { return lo == o.lo && hi == o.hi; }
};
struct Key2Hash {
    size_t operator()(const Key2 &k) const noexcept {
        static const ull FIXED_RANDOM = chrono::steady_clock::now().time_since_epoch().count();
        ull h1 = splitmix64(k.lo + FIXED_RANDOM);
        ull h2 = splitmix64(k.hi + FIXED_RANDOM + 0x9e3779b97f4a7c15ULL);
        return (size_t)(h1 ^ (h2 + 0x9e3779b97f4a7c15ULL + (h1 << 6) + (h1 >> 2)));
    }
};

static constexpr int MAXB = 64;
static int gBlocks = 0;

struct KeyN {
    array<ull, MAXB> w{};
};
struct KeyNHash {
    size_t operator()(KeyN const& k) const noexcept {
        static const ull FIXED_RANDOM = chrono::steady_clock::now().time_since_epoch().count();
        ull h = 0x123456789abcdef0ULL ^ FIXED_RANDOM;
        for (int i = 0; i < gBlocks; i++) {
            ull x = splitmix64(k.w[i] + (ull)(i + 1) * 0x9e3779b97f4a7c15ULL);
            h ^= x + 0x9e3779b97f4a7c15ULL + (h << 6) + (h >> 2);
        }
        return (size_t)h;
    }
};
struct KeyNEq {
    bool operator()(KeyN const& a, KeyN const& b) const noexcept {
        for (int i = 0; i < gBlocks; i++) if (a.w[i] != b.w[i]) return false;
        return true;
    }
};

static ld solve_subset_dp(int n, int m, istream &in) {
    int blocks = (m + 63) / 64;
    gBlocks = blocks;

    if (blocks == 1) {
        vector<array<ull, 4>> allow(n);
        for (int i = 0; i < m; i++) {
            string s;
            in >> s;
            ull bit = 1ULL << i;
            for (int p = 0; p < n; p++) {
                char ch = s[p];
                if (ch == '?') {
                    allow[p][0] |= bit;
                    allow[p][1] |= bit;
                    allow[p][2] |= bit;
                    allow[p][3] |= bit;
                } else {
                    allow[p][dnaIdx(ch)] |= bit;
                }
            }
        }

        ull allMask = (m == 64) ? ~0ULL : ((1ULL << m) - 1ULL);

        unordered_map<ull, ld, U64Hash> dp, ndp;
        dp.reserve(1024);
        ndp.reserve(1024);
        dp.emplace(allMask, (ld)1.0);

        ld p0 = 0.0L;
        const ld quarter = 0.25L;

        for (int p = 0; p < n; p++) {
            if (dp.empty()) break;
            ndp.clear();
            ndp.reserve(dp.size() * 2 + 8);
            ld new0 = p0;

            ull a0 = allow[p][0], a1 = allow[p][1], a2 = allow[p][2], a3 = allow[p][3];

            for (auto &kv : dp) {
                ull mask = kv.first;
                ld prob = kv.second;
                ld w = prob * quarter;

                ull nm = mask & a0;
                if (!nm) new0 += w; else ndp[nm] += w;

                nm = mask & a1;
                if (!nm) new0 += w; else ndp[nm] += w;

                nm = mask & a2;
                if (!nm) new0 += w; else ndp[nm] += w;

                nm = mask & a3;
                if (!nm) new0 += w; else ndp[nm] += w;
            }

            dp.swap(ndp);
            p0 = new0;
        }

        ld ans = 1.0L - p0;
        if (ans < 0) ans = 0;
        if (ans > 1) ans = 1;
        return ans;
    }

    if (blocks == 2) {
        vector<array<Key2, 4>> allow(n);
        for (int i = 0; i < m; i++) {
            string s;
            in >> s;
            int b = i >> 6;
            ull bit = 1ULL << (i & 63);
            for (int p = 0; p < n; p++) {
                char ch = s[p];
                if (ch == '?') {
                    for (int c = 0; c < 4; c++) {
                        if (b == 0) allow[p][c].lo |= bit;
                        else allow[p][c].hi |= bit;
                    }
                } else {
                    int c = dnaIdx(ch);
                    if (b == 0) allow[p][c].lo |= bit;
                    else allow[p][c].hi |= bit;
                }
            }
        }

        Key2 all{};
        if (m >= 64) all.lo = ~0ULL;
        else all.lo = (m == 64 ? ~0ULL : ((1ULL << m) - 1ULL));
        if (m > 64) {
            int r = m - 64;
            if (r == 64) all.hi = ~0ULL;
            else all.hi = (r == 0 ? 0ULL : ((1ULL << r) - 1ULL));
        } else all.hi = 0ULL;

        unordered_map<Key2, ld, Key2Hash> dp, ndp;
        dp.reserve(1024);
        ndp.reserve(1024);
        dp.emplace(all, (ld)1.0);

        ld p0 = 0.0L;
        const ld quarter = 0.25L;

        for (int p = 0; p < n; p++) {
            if (dp.empty()) break;
            ndp.clear();
            ndp.reserve(dp.size() * 2 + 8);
            ld new0 = p0;

            const Key2 a0 = allow[p][0], a1 = allow[p][1], a2 = allow[p][2], a3 = allow[p][3];

            for (auto &kv : dp) {
                const Key2 &mask = kv.first;
                ld prob = kv.second;
                ld w = prob * quarter;

                Key2 nm{mask.lo & a0.lo, mask.hi & a0.hi};
                if ((nm.lo | nm.hi) == 0ULL) new0 += w; else ndp[nm] += w;

                nm = Key2{mask.lo & a1.lo, mask.hi & a1.hi};
                if ((nm.lo | nm.hi) == 0ULL) new0 += w; else ndp[nm] += w;

                nm = Key2{mask.lo & a2.lo, mask.hi & a2.hi};
                if ((nm.lo | nm.hi) == 0ULL) new0 += w; else ndp[nm] += w;

                nm = Key2{mask.lo & a3.lo, mask.hi & a3.hi};
                if ((nm.lo | nm.hi) == 0ULL) new0 += w; else ndp[nm] += w;
            }

            dp.swap(ndp);
            p0 = new0;
        }

        ld ans = 1.0L - p0;
        if (ans < 0) ans = 0;
        if (ans > 1) ans = 1;
        return ans;
    }

    if (blocks > MAXB) {
        // No feasible exact method under this representation.
        // Attempt fallback to 5-ary method would have been chosen earlier.
        // Here, return 0 as a safe default; expected constraints should avoid this.
        for (int i = 0; i < m; i++) {
            string dummy;
            in >> dummy;
        }
        return 0.0L;
    }

    vector<ull> allowFlat((size_t)n * 4ULL * (size_t)blocks, 0ULL);

    for (int i = 0; i < m; i++) {
        string s;
        in >> s;
        int b = i >> 6;
        ull bit = 1ULL << (i & 63);
        for (int p = 0; p < n; p++) {
            char ch = s[p];
            if (ch == '?') {
                for (int c = 0; c < 4; c++) {
                    allowFlat[((size_t)p * 4ULL + (size_t)c) * (size_t)blocks + (size_t)b] |= bit;
                }
            } else {
                int c = dnaIdx(ch);
                allowFlat[((size_t)p * 4ULL + (size_t)c) * (size_t)blocks + (size_t)b] |= bit;
            }
        }
    }

    KeyN all{};
    {
        int full = m / 64;
        int rem = m % 64;
        for (int i = 0; i < full; i++) all.w[i] = ~0ULL;
        if (rem) all.w[full] = (rem == 64 ? ~0ULL : ((1ULL << rem) - 1ULL));
    }

    unordered_map<KeyN, ld, KeyNHash, KeyNEq> dp, ndp;
    dp.reserve(1024);
    ndp.reserve(1024);
    dp.emplace(all, (ld)1.0);

    ld p0 = 0.0L;
    const ld quarter = 0.25L;

    for (int p = 0; p < n; p++) {
        if (dp.empty()) break;
        ndp.clear();
        ndp.reserve(dp.size() * 2 + 8);
        ld new0 = p0;

        const ull* a0 = &allowFlat[((size_t)p * 4ULL + 0ULL) * (size_t)blocks];
        const ull* a1 = &allowFlat[((size_t)p * 4ULL + 1ULL) * (size_t)blocks];
        const ull* a2 = &allowFlat[((size_t)p * 4ULL + 2ULL) * (size_t)blocks];
        const ull* a3 = &allowFlat[((size_t)p * 4ULL + 3ULL) * (size_t)blocks];

        for (auto &kv : dp) {
            const KeyN &mask = kv.first;
            ld prob = kv.second;
            ld w = prob * quarter;

            for (int c = 0; c < 4; c++) {
                const ull* am = (c == 0 ? a0 : c == 1 ? a1 : c == 2 ? a2 : a3);
                KeyN nm{};
                ull acc = 0ULL;
                for (int b = 0; b < blocks; b++) {
                    ull v = mask.w[b] & am[b];
                    nm.w[b] = v;
                    acc |= v;
                }
                if (acc == 0ULL) new0 += w;
                else ndp[nm] += w;
            }
        }

        dp.swap(ndp);
        p0 = new0;
    }

    ld ans = 1.0L - p0;
    if (ans < 0) ans = 0;
    if (ans > 1) ans = 1;
    return ans;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    cin >> n >> m;

    const ull LIM5 = 50000000ULL;
    ull states5 = 1;
    bool use5 = true;
    for (int i = 0; i < n; i++) {
        if (states5 > LIM5 / 5ULL) { use5 = false; break; }
        states5 *= 5ULL;
    }

    ld ans;
    if (use5) ans = solve_small_n_5ary(n, m, cin);
    else ans = solve_subset_dp(n, m, cin);

    cout << setprecision(20) << (long double)ans << "\n";
    return 0;
}