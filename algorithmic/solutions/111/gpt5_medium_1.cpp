#include <bits/stdc++.h>
using namespace std;

using u32 = uint32_t;
using u64 = uint64_t;

// Degree of polynomial over GF(2) represented as bitmask
int poly_deg(u32 p) {
    if (p == 0) return -1;
#if defined(__GNUG__)
    return 31 - __builtin_clz(p);
#else
    int d = -1;
    while (p) { ++d; p >>= 1; }
    return d;
#endif
}

// Polynomial modulo operation over GF(2)
u32 poly_mod(u32 a, u32 b) {
    int db = poly_deg(b);
    if (db < 0) return a;
    while (poly_deg(a) >= db) {
        int shift = poly_deg(a) - db;
        a ^= (b << shift);
    }
    return a;
}

// Polynomial GCD over GF(2)
u32 poly_gcd(u32 a, u32 b) {
    while (b) {
        u32 r = poly_mod(a, b);
        a = b;
        b = r;
    }
    return a;
}

// Multiply in GF(2^m) modulo irreducible polynomial 'modPoly' (includes x^m term)
u32 gf_mul(u32 a, u32 b, u32 modPoly, int m) {
    u32 res = 0;
    u32 mask = (m == 32 ? 0xFFFFFFFFu : ((1u << (m+1)) - 1)); // safety
    while (b) {
        if (b & 1u) res ^= a;
        b >>= 1;
        // shift a
        a <<= 1;
        if (a & (1u << m)) a ^= modPoly;
        a &= ((1u << m) - 1);
    }
    return res;
}

u32 gf_square(u32 a, u32 modPoly, int m) {
    return gf_mul(a, a, modPoly, m);
}

// Check irreducibility of polynomial f of degree m over GF(2) using Rabin's test
bool is_irreducible(u32 f, int m) {
    if (((f >> m) & 1u) == 0) return false; // must be monic
    if ((f & 1u) == 0) return false;        // constant term must be 1
    // Compute x^{2^i} mod f and check gcd(x^{2^i} - x, f) == 1 for i=1..floor(m/2)
    u32 x = 2u; // polynomial 'x'
    u32 xp = x; // x^{2^i} mod f, start with x^{2^0} = x
    for (int i = 1; i <= m / 2; ++i) {
        // square to get x^{2^i}
        xp = gf_square(xp, f, m);
        u32 g = poly_gcd(xp ^ x, f);
        if (g != 1u) return false;
    }
    // Final check: x^{2^m} mod f should be x
    xp = x;
    for (int i = 0; i < m; ++i) xp = gf_square(xp, f, m);
    if (xp != x) return false;
    return true;
}

// Find an irreducible polynomial of degree m over GF(2)
u32 find_irreducible(int m) {
    if (m == 1) return 0b11u; // x + 1
    u32 start = (1u << m) | 1u; // monic and constant term 1
    u32 end = (1u << (m + 1));
    for (u32 f = start; f < end; f += 2u) {
        if (is_irreducible(f, m)) return f;
    }
    // Fallback (should not happen for small m)
    return start;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    u64 n;
    if (!(cin >> n)) return 0;

    if (n == 0) {
        cout << 0 << "\n\n";
        return 0;
    }

    int k0 = 63 - __builtin_clzll(n);
    int m = max(1, (k0 + 1) / 2);
    u32 modPoly = find_irreducible(m);

    int sizeU = 1 << m;
    vector<u32> baseVals(sizeU);
    for (int u = 0; u < sizeU; ++u) {
        u32 u2 = gf_mul(u, u, modPoly, m);
        u32 u3 = gf_mul(u2, u, modPoly, m);
        u32 val = (u3 << m) | (u32)u;
        baseVals[u] = val;
    }

    u64 maxValAll = (1ull << (2 * m)) - 1ull;

    vector<u32> bestAns;
    u32 bestC = 0;

    if (maxValAll <= n) {
        // All values fit; choose C=1 to avoid zero
        u32 C = 1u;
        bestAns.reserve(sizeU);
        for (int i = 0; i < sizeU; ++i) {
            u32 y = baseVals[i] ^ C;
            if (y >= 1 && y <= n) bestAns.push_back(y);
        }
    } else {
        int B = min(12, 2 * m);
        int maxC = (1 << B) - 1;
        size_t bestCnt = 0;
        // Try C=1 first
        for (int pass = 0; pass < 2; ++pass) {
            if (pass == 0) {
                u32 C = 1u;
                vector<u32> temp;
                temp.reserve(sizeU);
                for (int i = 0; i < sizeU; ++i) {
                    u32 y = baseVals[i] ^ C;
                    if (y >= 1 && y <= n) temp.push_back(y);
                }
                if (temp.size() > bestCnt) {
                    bestCnt = temp.size();
                    bestC = C;
                    bestAns.swap(temp);
                }
            } else {
                for (u32 C = 0; C <= (u32)maxC; ++C) {
                    vector<u32> temp;
                    temp.reserve(sizeU);
                    for (int i = 0; i < sizeU; ++i) {
                        u32 y = baseVals[i] ^ C;
                        if (y >= 1 && y <= n) temp.push_back(y);
                    }
                    if (temp.size() > bestCnt) {
                        bestCnt = temp.size();
                        bestC = C;
                        bestAns.swap(temp);
                    }
                }
            }
        }
    }

    cout << bestAns.size() << "\n";
    for (size_t i = 0; i < bestAns.size(); ++i) {
        if (i) cout << ' ';
        cout << bestAns[i];
    }
    cout << "\n";
    return 0;
}