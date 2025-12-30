#include <bits/stdc++.h>
using namespace std;

static inline int poly_deg(uint32_t p) {
    if (p == 0) return -1;
    return 31 - __builtin_clz(p);
}

static uint32_t poly_mod(uint32_t a, uint32_t mod) {
    int dm = poly_deg(mod);
    while (a && poly_deg(a) >= dm) {
        int shift = poly_deg(a) - dm;
        a ^= (mod << shift);
    }
    return a;
}

static uint32_t poly_gcd(uint32_t a, uint32_t b) {
    while (b) {
        uint32_t t = poly_mod(a, b);
        a = b;
        b = t;
    }
    return a;
}

static uint32_t gf_mul(uint32_t a, uint32_t b, uint32_t mod, int m) {
    uint32_t res = 0;
    while (b) {
        if (b & 1) res ^= a;
        b >>= 1;
        a <<= 1;
        if (a & (1u << m)) a ^= mod;
    }
    return res;
}

static bool is_irreducible(uint32_t f, int m) {
    if (poly_deg(f) != m) return false;
    if ((f & 1u) == 0) return false; // must be monic with constant term 1

    // factor m into primes
    int t = m;
    vector<int> pf;
    for (int p = 2; p * p <= t; ++p) {
        if (t % p == 0) {
            pf.push_back(p);
            while (t % p == 0) t /= p;
        }
    }
    if (t > 1) pf.push_back(t);

    auto frob_pow = [&](int e) {
        uint32_t xpow = 2; // polynomial 'x'
        for (int i = 0; i < e; ++i) {
            xpow = gf_mul(xpow, xpow, f, m); // square modulo f
        }
        return xpow;
    };

    // gcd(x^{2^{m/p}} - x, f) == 1 for all prime p | m
    for (int p : pf) {
        int e = m / p;
        uint32_t xp = frob_pow(e);
        uint32_t g = poly_gcd(xp ^ 2u, f);
        if (g != 1u) return false;
    }
    // x^{2^m} - x ≡ 0 (mod f)
    uint32_t xm = frob_pow(m);
    if ((xm ^ 2u) != 0u) return false;

    return true;
}

static uint32_t find_irreducible(int m) {
    if (m == 0) return 1;
    uint32_t start = (1u << m) | 1u;
    uint32_t end = 1u << (m + 1);
    for (uint32_t c = start; c < end; c += 2u) {
        if (is_irreducible(c, m)) return c;
    }
    // Fallback should never happen for m <= 12
    return start;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    uint32_t n;
    if (!(cin >> n)) return 0;

    // We will consider m from 1 up to 12 (since n <= 1e7 < 2^24, so m<=12 is sufficient)
    int max_m = 12;

    vector<uint32_t> best;
    size_t bestSize = 0;

    for (int m = 1; m <= max_m; ++m) {
        uint32_t mod = find_irreducible(m);
        int M = 1 << m;
        vector<uint32_t> cur;
        cur.reserve(M);

        for (int x = 0; x < M; ++x) {
            uint32_t xx = (uint32_t)x;
            uint32_t sq = gf_mul(xx, xx, mod, m);
            uint32_t cube = gf_mul(sq, xx, mod, m); // x^3 in GF(2^m)
            uint32_t low = cube ^ 1u; // add constant to avoid 0
            uint32_t y = (xx << m) | low;
            if (y >= 1u && y <= n) cur.push_back(y);
        }
        if (cur.size() > bestSize) {
            bestSize = cur.size();
            best = move(cur);
        }
    }

    if (best.empty()) {
        // As a fallback (shouldn't happen with n>=1), output 1
        cout << 1 << "\n" << 1 << "\n";
        return 0;
    }

    cout << best.size() << "\n";
    for (size_t i = 0; i < best.size(); ++i) {
        if (i) cout << ' ';
        cout << best[i];
    }
    cout << "\n";
    return 0;
}