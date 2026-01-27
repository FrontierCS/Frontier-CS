#include <bits/stdc++.h>
using namespace std;

static inline uint32_t gf_mul(uint32_t a, uint32_t b, int m, uint32_t poly) {
    uint32_t res = 0;
    uint32_t mask = (m == 32) ? 0xFFFFFFFFu : ((1u << m) - 1u);
    uint32_t mod = poly & mask; // poly without x^m term
    for (int i = 0; i < m; i++) {
        if (b & 1u) res ^= a;
        b >>= 1u;
        uint32_t carry = a & (1u << (m - 1));
        a = (a << 1u) & mask;
        if (carry) a ^= mod;
    }
    return res & mask;
}

static inline uint32_t gf_cube(uint32_t x, int m, uint32_t poly) {
    uint32_t sq = gf_mul(x, x, m, poly);
    return gf_mul(sq, x, m, poly);
}

static vector<uint32_t> build_base(int m, uint32_t poly) {
    uint32_t sz = 1u << m;
    vector<uint32_t> base;
    base.reserve(sz);
    for (uint32_t x = 0; x < sz; x++) {
        uint32_t y = gf_cube(x, m, poly) ^ 1u; // shift by 1 to avoid 0 element
        uint32_t v = (x << m) | y;
        base.push_back(v);
    }
    return base;
}

static vector<uint32_t> gen_translations(int m, uint32_t n, uint32_t mask2, size_t limit) {
    vector<uint32_t> ts;
    ts.reserve(limit + 64);

    auto add = [&](uint32_t t) {
        ts.push_back(t & mask2);
    };

    add(0u);
    add(mask2);
    add(n & mask2);
    add((n + 1u) & mask2);
    add((n >> 1u) & mask2);
    add((n << 1u) & mask2);
    add((~n) & mask2);
    add(((n & mask2) ^ mask2) & mask2);

    int bits = 2 * m;
    for (int b = 0; b < bits; b++) {
        add(1u << b);
        add((n & mask2) ^ (1u << b));
    }

    uint64_t seed = (uint64_t)n * 1315423911ull + (uint64_t)m * 2654435761ull + 0x9E3779B97F4A7C15ull;
    while (ts.size() < limit) {
        seed ^= seed << 7;
        seed ^= seed >> 9;
        seed ^= seed << 8;
        add((uint32_t)seed);
    }

    sort(ts.begin(), ts.end());
    ts.erase(unique(ts.begin(), ts.end()), ts.end());
    if (ts.size() > limit) ts.resize(limit);
    return ts;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    uint32_t n;
    if (!(cin >> n)) return 0;

    // Primitive/irreducible polynomials (with leading x^m term included).
    // poly bits: x^m + ... + 1
    static const uint32_t poly[13] = {
        0,
        0x3,    // m=1: x + 1
        0x7,    // m=2: x^2 + x + 1
        0xB,    // m=3: x^3 + x + 1
        0x13,   // m=4: x^4 + x + 1
        0x25,   // m=5: x^5 + x^2 + 1
        0x43,   // m=6: x^6 + x + 1
        0x89,   // m=7: x^7 + x^3 + 1
        0x11D,  // m=8: x^8 + x^4 + x^3 + x^2 + 1
        0x211,  // m=9: x^9 + x^4 + 1
        0x409,  // m=10: x^10 + x^3 + 1
        0x805,  // m=11: x^11 + x^2 + 1
        0x1009  // m=12: x^12 + x^3 + 1
    };

    vector<uint32_t> bestS;
    bestS.reserve(4096);

    for (int m = 1; m <= 12; m++) {
        auto base = build_base(m, poly[m]);

        int bits2 = 2 * m;
        uint32_t mask2 = (bits2 == 32) ? 0xFFFFFFFFu : ((1u << bits2) - 1u);

        uint32_t bestT = 0;
        int bestCnt = -1;

        if (bits2 <= 16) {
            for (uint32_t t = 0; t <= mask2; t++) {
                int cnt = 0;
                for (uint32_t a : base) {
                    uint32_t v = (a ^ t) & mask2;
                    if (v != 0 && v <= n) cnt++;
                }
                if (cnt > bestCnt) {
                    bestCnt = cnt;
                    bestT = t;
                }
            }
        } else {
            auto ts = gen_translations(m, n, mask2, 512);
            for (uint32_t t : ts) {
                int cnt = 0;
                for (uint32_t a : base) {
                    uint32_t v = (a ^ t) & mask2;
                    if (v != 0 && v <= n) cnt++;
                }
                if (cnt > bestCnt) {
                    bestCnt = cnt;
                    bestT = t;
                }
            }
        }

        vector<uint32_t> cur;
        cur.reserve(base.size());
        for (uint32_t a : base) {
            uint32_t v = (a ^ bestT) & mask2;
            if (v != 0 && v <= n) cur.push_back(v);
        }

        if (cur.size() > bestS.size()) bestS.swap(cur);
    }

    if (bestS.empty()) bestS.push_back(1);

    cout << bestS.size() << "\n";
    for (size_t i = 0; i < bestS.size(); i++) {
        if (i) cout << ' ';
        cout << bestS[i];
    }
    cout << "\n";
    return 0;
}