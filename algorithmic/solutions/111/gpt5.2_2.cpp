#include <bits/stdc++.h>
using namespace std;

struct SplitMix64 {
    uint64_t x;
    explicit SplitMix64(uint64_t seed = 0) : x(seed) {}
    uint64_t next() {
        uint64_t z = (x += 0x9e3779b97f4a7c15ULL);
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
        return z ^ (z >> 31);
    }
    uint32_t next_u32() { return (uint32_t)next(); }
};

static inline long long isqrt_ll(long long v) {
    if (v <= 0) return 0;
    long long r = (long long) sqrt((long double)v);
    while ((r + 1) > 0 && (r + 1) * (r + 1) <= v) ++r;
    while (r * r > v) --r;
    return r;
}

struct GF2m {
    int m;
    uint32_t mask;
    uint32_t red; // modulus without x^m term
    explicit GF2m(int mm) : m(mm) {
        static const uint32_t poly[13] = {
            0,
            0x3,    // 1: x + 1
            0x7,    // 2: x^2 + x + 1
            0xB,    // 3: x^3 + x + 1
            0x13,   // 4: x^4 + x + 1
            0x25,   // 5: x^5 + x^2 + 1
            0x43,   // 6: x^6 + x + 1
            0x83,   // 7: x^7 + x + 1
            0x11D,  // 8: x^8 + x^4 + x^3 + x^2 + 1
            0x211,  // 9: x^9 + x^4 + 1
            0x409,  // 10: x^10 + x^3 + 1
            0x805,  // 11: x^11 + x^2 + 1
            0x1053  // 12: x^12 + x^6 + x^4 + x + 1
        };
        uint32_t p = poly[m];
        mask = (m == 32) ? 0xFFFFFFFFu : ((1u << m) - 1u);
        red = p ^ (1u << m);
    }

    inline uint32_t mul(uint32_t a, uint32_t b) const {
        uint32_t res = 0;
        for (int i = 0; i < m; ++i) {
            if (b & 1u) res ^= a;
            b >>= 1u;
            uint32_t carry = a & (1u << (m - 1));
            a = (a << 1) & mask;
            if (carry) a ^= red;
        }
        return res;
    }
};

static inline bool testBit(const vector<uint64_t>& bs, uint32_t idx) {
    return (bs[idx >> 6] & (1ULL << (idx & 63))) != 0;
}
static inline void setBit(vector<uint64_t>& bs, uint32_t idx) {
    bs[idx >> 6] |= (1ULL << (idx & 63));
}

static vector<int> build_initial(int n, int k, int m, SplitMix64 &rng) {
    GF2m gf(m);
    const int Q = 1 << m;
    vector<uint32_t> base;
    base.reserve(Q);
    for (uint32_t x = 0; x < (uint32_t)Q; ++x) {
        uint32_t x2 = gf.mul(x, x);
        uint32_t x3 = gf.mul(x2, x);
        uint32_t val = (x3 << m) | x;
        base.push_back(val);
    }

    uint32_t bestB = 0;
    int bestCnt = -1;

    if (2 * m == k) {
        uint32_t fullMask = (k == 32) ? 0xFFFFFFFFu : ((1u << k) - 1u);
        uint32_t fullMax = fullMask;

        // If n covers all (except 0), no need to shift-search.
        if ((uint32_t)n != fullMax) {
            auto evalB = [&](uint32_t b) {
                int cnt = 0;
                for (uint32_t v : base) {
                    uint32_t y = (v ^ b) & fullMask;
                    if (y >= 1u && y <= (uint32_t)n) ++cnt;
                }
                if (cnt > bestCnt) {
                    bestCnt = cnt;
                    bestB = b & fullMask;
                }
            };

            evalB(0);
            evalB(fullMask);
            evalB((uint32_t)n & fullMask);
            evalB(((uint32_t)n ^ 0xAAAAAAAAu) & fullMask);
            evalB(((uint32_t)n ^ 0x55555555u) & fullMask);

            int trials = (m >= 11 ? 3000 : 6000);
            for (int t = 0; t < trials; ++t) {
                uint32_t b = rng.next_u32() & fullMask;
                evalB(b);
            }
        } else {
            bestB = 0;
        }
    } else {
        bestB = 0;
    }

    vector<int> S;
    S.reserve(base.size());
    if (2 * m == k) {
        uint32_t fullMask = (k == 32) ? 0xFFFFFFFFu : ((1u << k) - 1u);
        for (uint32_t v : base) {
            uint32_t y = (v ^ bestB) & fullMask;
            if (y >= 1u && y <= (uint32_t)n) S.push_back((int)y);
        }
    } else {
        // All base values fit into [0, 2^(2m)-1] and 2^(2m) <= 2^(k-1) <= n
        for (uint32_t v : base) {
            if (v >= 1u && v <= (uint32_t)n) S.push_back((int)v);
        }
    }

    // Randomize order (helps early-break in extension)
    for (int i = (int)S.size() - 1; i > 0; --i) {
        int j = (int)(rng.next() % (uint64_t)(i + 1));
        swap(S[i], S[j]);
    }
    return S;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    long long target = isqrt_ll((long long)n / 2);
    if (n <= 0) {
        cout << 0 << "\n\n";
        return 0;
    }
    if (n == 1) {
        cout << 1 << "\n1\n";
        return 0;
    }

    int k = 32 - __builtin_clz((unsigned)n);
    uint32_t sizeX = 1u << k;

    SplitMix64 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count() ^ (uint64_t)n * 0x9e3779b97f4a7c15ULL);

    // Candidate initial constructions
    vector<int> bestS;
    vector<int> candidates_m;
    if (k >= 2) {
        int m_big = (k % 2 == 0) ? (k / 2) : ((k - 1) / 2);
        candidates_m.push_back(m_big);
        if (m_big - 1 >= 1) candidates_m.push_back(m_big - 1);
    }

    for (int m : candidates_m) {
        if (m < 1) continue;
        if (2 * m > k) continue;
        auto S = build_initial(n, k, m, rng);
        if (S.size() > bestS.size()) bestS = std::move(S);
    }

    if (bestS.empty()) {
        // Fallback: start with {1}
        bestS.push_back(1);
    }

    vector<int> S = std::move(bestS);

    // Presence array
    vector<uint8_t> present((size_t)n + 1, 0);
    for (int x : S) if (1 <= x && x <= n) present[x] = 1;

    // Used XOR bitset
    vector<uint64_t> used(((uint64_t)sizeX + 63) >> 6, 0);

    // Build used XORs from initial S (assumed valid)
    for (size_t i = 0; i < S.size(); ++i) {
        uint32_t xi = (uint32_t)S[i];
        for (size_t j = 0; j < i; ++j) {
            uint32_t v = xi ^ (uint32_t)S[j];
            setBit(used, v);
        }
    }

    vector<uint32_t> buf;
    buf.reserve(7000);

    auto start = chrono::steady_clock::now();
    const double T_ensure = 0.55;
    const double T_total = 0.96;

    int failStreak = 0;
    uint64_t iter = 0;

    auto elapsed = [&]() -> double {
        return chrono::duration<double>(chrono::steady_clock::now() - start).count();
    };

    auto tryAdd = [&](int x) -> bool {
        buf.clear();
        buf.reserve(S.size());
        uint32_t xu = (uint32_t)x;
        for (int s : S) {
            uint32_t v = xu ^ (uint32_t)s;
            if (testBit(used, v)) return false;
            buf.push_back(v);
        }
        for (uint32_t v : buf) setBit(used, v);
        S.push_back(x);
        present[x] = 1;
        return true;
    };

    // Phase 1: ensure reaching target
    while ((long long)S.size() < target) {
        if ((iter & 2047) == 0) {
            if (elapsed() > T_total) break;
        }
        int x = (int)(rng.next() % (uint64_t)n) + 1;
        if (present[x]) { ++iter; continue; }
        if (tryAdd(x)) failStreak = 0;
        else ++failStreak;
        ++iter;
    }

    // Phase 2: maximize while time remains
    failStreak = 0;
    while (true) {
        if ((iter & 2047) == 0) {
            double e = elapsed();
            if (e > T_total) break;
        }
        int x = (int)(rng.next() % (uint64_t)n) + 1;
        if (present[x]) { ++iter; continue; }

        bool ok = true;
        buf.clear();
        buf.reserve(S.size());
        uint32_t xu = (uint32_t)x;
        for (int s : S) {
            uint32_t v = xu ^ (uint32_t)s;
            if (testBit(used, v)) { ok = false; break; }
            buf.push_back(v);
        }

        if (!ok) {
            ++failStreak;
            ++iter;
            if (failStreak > 20000 && elapsed() > T_ensure) break;
            continue;
        }

        for (uint32_t v : buf) setBit(used, v);
        S.push_back(x);
        present[x] = 1;
        failStreak = 0;
        ++iter;
    }

    if (S.empty()) {
        S.push_back(1);
    }

    cout << S.size() << "\n";
    for (size_t i = 0; i < S.size(); ++i) {
        if (i) cout << ' ';
        cout << S[i];
    }
    cout << "\n";
    return 0;
}