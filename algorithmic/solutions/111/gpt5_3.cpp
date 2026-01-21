#include <bits/stdc++.h>
using namespace std;

using u64 = unsigned long long;
using u32 = unsigned int;

// Polynomial utilities over F2 (bit representation)

// Degree of polynomial (highest set bit index), -1 for 0
int poly_deg(u64 p) {
    if (!p) return -1;
    return 63 - __builtin_clzll(p);
}

// Multiply two polynomials over F2 (no modulus), return raw product
u64 poly_mul_raw(u64 a, u64 b) {
    u64 res = 0;
    while (b) {
        if (b & 1) res ^= a;
        b >>= 1;
        a <<= 1;
    }
    return res;
}

// Remainder of a / b (polynomials over F2)
u64 poly_mod(u64 a, u64 b) {
    int db = poly_deg(b);
    if (db < 0) return a;
    while (poly_deg(a) >= db) {
        int shift = poly_deg(a) - db;
        a ^= (b << shift);
    }
    return a;
}

// GCD of two polynomials over F2
u64 poly_gcd(u64 a, u64 b) {
    while (b) {
        u64 r = poly_mod(a, b);
        a = b;
        b = r;
    }
    return a;
}

// Check irreducibility of polynomial P of degree r over F2 using Rabin test
bool is_irreducible(u64 P, int r) {
    if (!(P & 1)) return false;                   // constant term must be 1
    if (((P >> r) & 1ULL) == 0) return false;     // leading coefficient must be 1
    // Compute x^{2^i} mod P for i = 1..r
    u64 x = 2ULL; // polynomial 'x'
    u64 q = x;
    for (int i = 1; i <= r; ++i) {
        // square mod P: q = q^2 mod P
        q = poly_mod(poly_mul_raw(q, q), P);
        if (i <= r / 2) {
            u64 g = poly_gcd(q ^ x, P);
            if (g != 1ULL) return false;
        }
    }
    // Must have x^{2^r} ≡ x (mod P)
    if (q != x) return false;
    return true;
}

// Find any irreducible polynomial of degree r over F2 (monic, constant term 1)
u64 find_irreducible(int r) {
    if (r == 1) return (1ULL << 1) | 1ULL; // x + 1
    // Try trinomials x^r + x^a + 1
    for (int a = 1; a < r; ++a) {
        u64 P = (1ULL << r) | (1ULL << a) | 1ULL;
        if (is_irreducible(P, r)) return P;
    }
    // Try quadrinomials x^r + x^a + x^b + 1
    for (int a = r - 1; a >= 1; --a) {
        for (int b = a - 1; b >= 1; --b) {
            u64 P = (1ULL << r) | (1ULL << a) | (1ULL << b) | 1ULL;
            if (is_irreducible(P, r)) return P;
        }
    }
    // Full enumeration over polynomials with top and constant bits set
    u64 maxMask = (r >= 2) ? (1ULL << (r - 1)) : 1ULL; // bits for positions 1..r-1
    for (u64 mask = 0; mask < maxMask; ++mask) {
        u64 middle = (mask << 1);
        u64 P = (1ULL << r) | middle | 1ULL;
        if (is_irreducible(P, r)) return P;
    }
    // Fallback (should never reach here for small r)
    return (1ULL << r) | 1ULL;
}

// GF(2^r) multiplication modulo irreducible polynomial P (with degree r)
u32 gf_mul(u32 a, u32 b, u32 P, int r) {
    u32 res = 0;
    u32 top = 1u << r;
    while (b) {
        if (b & 1u) res ^= a;
        b >>= 1u;
        a <<= 1u;
        if (a & top) a ^= P;
    }
    return res;
}

// Cube in GF(2^r): x^3 = x * x^2
u32 gf_cube(u32 x, u32 P, int r) {
    u32 sq = gf_mul(x, x, P, r);
    return gf_mul(sq, x, P, r);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    unsigned long long n;
    if (!(cin >> n)) return 0;

    if (n <= 3) {
        // For very small n, output trivial maximal sets
        cout << n << "\n";
        for (unsigned long long i = 1; i <= n; ++i) {
            if (i > 1) cout << ' ';
            cout << i;
        }
        cout << "\n";
        return 0;
    }

    int maxR = 24; // enough since n <= 1e7 < 2^24
    long long bestM = -1;
    int bestR = -1;
    u32 bestP = 0;

    for (int r = 1; r <= maxR; ++r) {
        u64 domain = 1ULL << r;
        u64 c = n >> r; // floor(n / 2^r)
        long long M = 0;
        if (c == 0) {
            M = 0;
        } else if (c >= domain) {
            M = (long long)domain - 1; // can include all x=1..2^r-1
        } else {
            u64 rem = n & (domain - 1);
            u64 P = find_irreducible(r);
            u32 fc = gf_cube((u32)c, (u32)P, r);
            int delta = (fc <= rem) ? 1 : 0;
            M = (long long)c - 1 + delta; // exclude x=0
        }
        if (M > bestM) {
            bestM = M;
            bestR = r;
        }
    }

    if (bestM <= 0) {
        // Fallback: choose simple small set
        // For n >= 4, we can output 4 numbers {1,2,3,4} which are valid
        if (n >= 4) {
            cout << 4 << "\n1 2 3 4\n";
        } else if (n == 3) {
            cout << 3 << "\n1 2 3\n";
        } else if (n == 2) {
            cout << 2 << "\n1 2\n";
        } else {
            cout << 1 << "\n1\n";
        }
        return 0;
    }

    int r = bestR;
    u64 domain = 1ULL << r;
    u32 P = (u32)find_irreducible(r);

    u64 c = n >> r;
    u64 rem = n & (domain - 1);

    vector<u64> ans;
    ans.reserve((size_t)bestM);

    if (c >= domain) {
        for (u64 x = 1; x < domain; ++x) {
            u32 y = gf_cube((u32)x, P, r);
            u64 s = (x << r) ^ (u64)y;
            // s <= 2^{2r}-1 <= n here
            ans.push_back(s);
        }
    } else {
        for (u64 x = 1; x < c; ++x) {
            u32 y = gf_cube((u32)x, P, r);
            u64 s = (x << r) ^ (u64)y;
            if (s <= n) ans.push_back(s);
        }
        if (c >= 1 && c < domain) {
            u32 fc = gf_cube((u32)c, P, r);
            if ((u64)fc <= rem) {
                u64 s = (c << r) ^ (u64)fc;
                if (s >= 1 && s <= n) ans.push_back(s);
            }
        }
    }

    // As an extra safety to reach at least floor(sqrt(n/2)), if somehow we are short,
    // we can add simple small numbers not conflicting (though theoretically we shouldn't be short).
    // But this is generally unnecessary; keeping minimal.

    cout << ans.size() << "\n";
    for (size_t i = 0; i < ans.size(); ++i) {
        if (i) cout << ' ';
        cout << ans[i];
    }
    cout << "\n";
    return 0;
}