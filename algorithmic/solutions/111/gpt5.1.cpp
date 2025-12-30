#include <bits/stdc++.h>
using namespace std;

int poly_deg(uint32_t p) {
    return p ? 31 - __builtin_clz(p) : -1;
}

bool poly_divisible(uint32_t p, uint32_t q) {
    int dq = poly_deg(q);
    uint32_t r = p;
    int dr = poly_deg(r);
    while (dr >= dq) {
        r ^= q << (dr - dq);
        dr = poly_deg(r);
    }
    return r == 0;
}

bool is_irreducible(uint32_t p, int m) {
    for (int d = 1; d <= m / 2; ++d) {
        uint32_t max_mid = 1u << (d - 1);
        for (uint32_t mid = 0; mid < max_mid; ++mid) {
            uint32_t q = (1u << d) | (mid << 1) | 1u; // monic deg d, const 1
            if (poly_divisible(p, q)) return false;
        }
    }
    return true;
}

uint32_t find_irreducible_poly(int m) {
    uint32_t max_mid = 1u << (m - 1);
    for (uint32_t mid = 0; mid < max_mid; ++mid) {
        uint32_t p = (1u << m) | (mid << 1) | 1u; // degree m, const=1
        if (is_irreducible(p, m)) return p;
    }
    return 0; // should not happen
}

inline uint32_t gf_mul(uint32_t a, uint32_t b, int m, uint32_t poly) {
    uint32_t res = 0;
    while (b) {
        if (b & 1u) res ^= a;
        b >>= 1;
        a <<= 1;
        if (a & (1u << m)) a ^= poly;
    }
    return res;
}

long long isqrt_ll(long long x) {
    if (x <= 0) return 0;
    long long r = sqrt((long double)x);
    while ((r + 1) * (r + 1) <= x) ++r;
    while (r * r > x) --r;
    return r;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    long long n;
    if (!(cin >> n)) return 0;

    if (n <= 0) {
        cout << 0 << "\n\n";
        return 0;
    }

    if (n <= 7) {
        cout << 1 << "\n1\n";
        return 0;
    }

    long long half = n / 2;
    int target = (int)isqrt_ll(half); // floor(sqrt(n/2))

    if (target <= 1) {
        cout << 1 << "\n1\n";
        return 0;
    }

    int m = 0;
    while ((1 << m) < target) ++m;
    if (m < 1) m = 1;
    if (m > 12) m = 12; // for safety; not needed for n <= 1e7

    uint32_t poly = find_irreducible_poly(m);
    uint32_t q = 1u << m;
    int B = 2 * m;
    uint32_t M = 1u << B;

    vector<uint32_t> codes;
    codes.reserve(q);
    for (uint32_t x = 0; x < q; ++x) {
        uint32_t x2 = gf_mul(x, x, m, poly);
        uint32_t x3 = gf_mul(x2, x, m, poly);
        uint32_t code = x | (x3 << m); // 2m bits
        codes.push_back(code);
    }

    mt19937_64 rng(123456789);
    const int maxAttempts = 8192;

    vector<int> bestS;
    bestS.reserve(target);
    int bestCnt = 0;

    for (int attempt = 0; attempt < maxAttempts; ++attempt) {
        uint32_t s;
        if (attempt == 0) s = 0;
        else s = (uint32_t)(rng() & (M - 1));

        vector<int> cur;
        cur.reserve(target);
        for (uint32_t c : codes) {
            uint32_t v = c ^ s;
            if (v >= 1u && v <= (uint32_t)n) {
                cur.push_back((int)v);
            }
        }
        if ((int)cur.size() > bestCnt) {
            bestCnt = (int)cur.size();
            bestS.swap(cur);
        }
        if (bestCnt >= target) break;
    }

    if (bestCnt == 0) {
        // Extremely unlikely fallback
        cout << 1 << "\n1\n";
        return 0;
    }

    cout << bestCnt << "\n";
    for (int i = 0; i < bestCnt; ++i) {
        if (i) cout << ' ';
        cout << bestS[i];
    }
    cout << '\n';
    return 0;
}