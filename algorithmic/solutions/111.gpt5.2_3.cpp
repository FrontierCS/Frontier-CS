#include <bits/stdc++.h>
using namespace std;

static inline uint64_t splitmix64(uint64_t &x) {
    x += 0x9e3779b97f4a7c15ULL;
    uint64_t z = x;
    z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
    z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
    return z ^ (z >> 31);
}

static inline uint32_t gf_mul(uint32_t a, uint32_t b, int t, uint32_t irr_no) {
    uint32_t res = 0;
    uint32_t mask = (t == 32) ? 0xFFFFFFFFu : ((1u << t) - 1u);
    a &= mask;
    b &= mask;
    for (int i = 0; i < t; i++) {
        if (b & 1u) res ^= a;
        b >>= 1;
        uint32_t carry = a & (1u << (t - 1));
        a = (a << 1) & mask;
        if (carry) a ^= irr_no;
    }
    return res & mask;
}

static inline uint32_t gf_cube(uint32_t x, int t, uint32_t irr_no) {
    if (x == 0) return 0;
    uint32_t x2 = gf_mul(x, x, t, irr_no);
    return gf_mul(x2, x, t, irr_no);
}

static inline int isqrt_ll(long long v) {
    if (v <= 0) return 0;
    long long r = (long long)floor(sqrt((long double)v));
    while ((r + 1) * (r + 1) <= v) ++r;
    while (r * r > v) --r;
    return (int)r;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;

    long long half = n / 2LL;
    int req = isqrt_ll(half);

    // irreducible polynomials without the leading term x^t (primitive/irreducible choices)
    // index: degree t
    static const uint32_t irr_no[13] = {
        0,
        0x1u,   // 1: x + 1
        0x3u,   // 2: x^2 + x + 1
        0x3u,   // 3: x^3 + x + 1
        0x3u,   // 4: x^4 + x + 1
        0x5u,   // 5: x^5 + x^2 + 1
        0x3u,   // 6: x^6 + x + 1
        0x9u,   // 7: x^7 + x^3 + 1
        0x1Bu,  // 8: x^8 + x^4 + x^3 + x + 1
        0x11u,  // 9: x^9 + x^4 + 1
        0x9u,   // 10: x^10 + x^3 + 1
        0x5u,   // 11: x^11 + x^2 + 1
        0x53u   // 12: x^12 + x^6 + x^4 + x + 1
    };

    vector<int> best;

    for (int t = 1; t <= 12; t++) {
        int q = 1 << t;
        int space = 1 << (2 * t);
        uint32_t irr = irr_no[t];

        vector<uint32_t> E;
        E.reserve(q);
        for (uint32_t x = 0; x < (uint32_t)q; x++) {
            uint32_t x3 = gf_cube(x, t, irr);
            uint32_t e = (x << t) | x3;
            E.push_back(e);
        }

        vector<uint32_t> Esorted = E;
        sort(Esorted.begin(), Esorted.end());

        vector<int> out;

        if (n >= space - 1) {
            uint32_t c = 1;
            while (c < (uint32_t)space && binary_search(Esorted.begin(), Esorted.end(), c)) ++c;
            if (c == (uint32_t)space) c = 0; // should never happen for t>=2; safe fallback
            out.reserve(q);
            for (uint32_t e : E) {
                uint32_t v = e ^ c;
                if (v != 0 && (int)v <= n) out.push_back((int)v);
            }
        } else {
            vector<uint32_t> shifts;
            shifts.reserve(512);
            shifts.push_back(0);
            uint32_t lim = min(space - 1, 64);
            for (uint32_t i = 1; i <= lim; i++) shifts.push_back(i);
            shifts.push_back((uint32_t)(space - 1));
            shifts.push_back((uint32_t)(n & (space - 1)));

            uint64_t seed = 0x1234567890abcdefULL ^ (uint64_t)n * 0x9e3779b97f4a7c15ULL ^ (uint64_t)t;
            int K = (t >= 10 ? 256 : 128);
            for (int i = 0; i < K; i++) {
                uint32_t c = (uint32_t)(splitmix64(seed) % (uint64_t)space);
                shifts.push_back(c);
            }
            sort(shifts.begin(), shifts.end());
            shifts.erase(unique(shifts.begin(), shifts.end()), shifts.end());

            uint32_t bestC = 0;
            int bestCnt = -1;
            for (uint32_t c : shifts) {
                int cnt = 0;
                for (uint32_t e : E) {
                    uint32_t v = e ^ c;
                    if (v != 0 && (int)v <= n) ++cnt;
                }
                if (cnt > bestCnt) {
                    bestCnt = cnt;
                    bestC = c;
                }
            }

            out.reserve(max(0, bestCnt));
            for (uint32_t e : E) {
                uint32_t v = e ^ bestC;
                if (v != 0 && (int)v <= n) out.push_back((int)v);
            }
        }

        if (out.size() > best.size()) best.swap(out);
    }

    if ((int)best.size() < req) {
        // Fallback: trivial (shouldn't be needed), ensure at least requirement
        // Use a small greedy randomized extension from current best.
        const int MAXX = 1 << 24;
        vector<uint64_t> used((MAXX + 63) / 64, 0);

        auto getbit = [&](int x) -> bool {
            return (used[(uint32_t)x >> 6] >> (x & 63)) & 1ULL;
        };
        auto setbit = [&](int x) {
            used[(uint32_t)x >> 6] |= 1ULL << (x & 63);
        };

        unordered_set<int> present;
        present.reserve(best.size() * 2 + 16);
        for (int v : best) present.insert(v);

        for (int i = 0; i < (int)best.size(); i++) {
            for (int j = 0; j < i; j++) {
                setbit(best[i] ^ best[j]);
            }
        }

        uint64_t seed = 0xfeedfacecafebeefULL ^ (uint64_t)n;
        int attempts = 0, maxAttempts = 300000;
        while ((int)best.size() < req && attempts < maxAttempts) {
            ++attempts;
            int x = (int)(splitmix64(seed) % (uint64_t)n) + 1;
            if (present.find(x) != present.end()) continue;

            bool ok = true;
            for (int a : best) {
                int y = a ^ x;
                if (y == 0 || getbit(y)) { ok = false; break; }
            }
            if (!ok) continue;

            for (int a : best) setbit(a ^ x);
            best.push_back(x);
            present.insert(x);
        }

        if (best.empty() && n >= 1) best.push_back(1);
    }

    cout << best.size() << "\n";
    for (size_t i = 0; i < best.size(); i++) {
        if (i) cout << ' ';
        cout << best[i];
    }
    cout << "\n";
    return 0;
}