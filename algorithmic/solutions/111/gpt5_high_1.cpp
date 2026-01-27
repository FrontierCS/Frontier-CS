#include <bits/stdc++.h>
using namespace std;

static inline int poly_deg(uint32_t p) {
    if (p == 0) return -1;
    return 31 - __builtin_clz(p);
}

static inline uint32_t poly_mod(uint32_t a, uint32_t mod) {
    int dm = poly_deg(mod);
    if (dm < 0) return 0;
    while (poly_deg(a) >= dm) {
        int shift = poly_deg(a) - dm;
        a ^= (mod << shift);
    }
    return a;
}

static inline uint32_t poly_mul(uint32_t a, uint32_t b) {
    uint32_t res = 0;
    while (b) {
        if (b & 1) res ^= a;
        b >>= 1;
        a <<= 1;
    }
    return res;
}

static inline uint32_t poly_mul_mod(uint32_t a, uint32_t b, uint32_t mod) {
    uint32_t m = poly_mul(a, b);
    return poly_mod(m, mod);
}

static inline uint32_t poly_square_mod(uint32_t a, uint32_t mod) {
    return poly_mul_mod(a, a, mod);
}

static inline uint32_t poly_gcd(uint32_t a, uint32_t b) {
    while (b) {
        uint32_t r = poly_mod(a, b);
        a = b;
        b = r;
    }
    return a;
}

static bool is_irreducible(uint32_t f, int k) {
    if ((f & 1) == 0) return false; // constant term must be 1
    if (poly_deg(f) != k) return false;
    uint32_t x_mod = poly_mod(2u, f); // x modulo f
    uint32_t g = x_mod;
    for (int i = 1; i <= k / 2; ++i) {
        g = poly_square_mod(g, f); // g = x^{2^i} mod f
        uint32_t h = poly_gcd(f, g ^ x_mod);
        if (h != 1u) return false;
    }
    // compute x^{2^k} mod f
    for (int i = k / 2 + 1; i <= k; ++i) {
        g = poly_square_mod(g, f);
    }
    return g == x_mod;
}

static uint32_t find_irreducible_poly(int k) {
    if (k == 0) return 1; // dummy
    uint32_t start = (1u << k) | 1u;
    uint32_t end = (1u << (k + 1));
    for (uint32_t p = start; p < end; p += 2) { // odd polynomials only
        if (is_irreducible(p, k)) return p;
    }
    // Fallback (should never happen for k<=16)
    return start;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    long long n;
    if (!(cin >> n)) return 0;

    // Determine number of usable bits d such that (2^d - 1) <= n
    int d = 0;
    while (((1ULL << d) - 1ULL) <= (unsigned long long)n) d++;
    d--;

    vector<uint32_t> res;
    if (d <= 0) {
        // n >= 1 by constraints; but handle safety
        if (n >= 1) {
            cout << 1 << "\n1\n";
        } else {
            cout << 0 << "\n\n";
        }
        return 0;
    }

    if (d % 2 == 0) {
        int k = d / 2;
        if (k == 0) {
            // Only numbers 0..1; exclude 0
            if (n >= 1) res.push_back(1);
        } else {
            uint32_t modpoly = find_irreducible_poly(k);
            int lim = 1 << k;
            for (int x = 0; x < lim; ++x) {
                uint32_t xx = (uint32_t)x;
                uint32_t f = poly_mul_mod(poly_mul_mod(xx, xx, modpoly), xx, modpoly); // x^3
                uint32_t val = ((uint32_t)x << k) | f;
                if (val != 0 && (unsigned long long)val <= (unsigned long long)n) res.push_back(val);
            }
        }
    } else {
        int k = (d - 1) / 2;
        if (k == 0) {
            // Two layers, k=0: values are b (0 or 1). Exclude 0.
            if (n >= 1) res.push_back(1);
        } else {
            uint32_t modpoly = find_irreducible_poly(k);
            int lim = 1 << k;
            for (int b = 0; b < 2; ++b) {
                for (int x = 0; x < lim; ++x) {
                    uint32_t xx = (uint32_t)x;
                    uint32_t f = poly_mul_mod(poly_mul_mod(xx, xx, modpoly), xx, modpoly); // x^3
                    uint32_t val = ((uint32_t)b << (2 * k)) | ((uint32_t)x << k) | f;
                    if (val != 0 && (unsigned long long)val <= (unsigned long long)n) res.push_back(val);
                }
            }
        }
    }

    cout << res.size() << "\n";
    for (size_t i = 0; i < res.size(); ++i) {
        if (i) cout << ' ';
        cout << res[i];
    }
    cout << "\n";
    return 0;
}