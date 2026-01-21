#include <bits/stdc++.h>
using namespace std;
using u32 = uint32_t;

// Polynomial degree over GF(2)
int poly_deg(u32 x) {
    return 31 - __builtin_clz(x);
}

// Polynomial modulo over GF(2)
u32 poly_mod(u32 a, u32 mod) {
    if (!a) return 0;
    int dm = poly_deg(mod);
    int da = poly_deg(a);
    while (da >= dm) {
        a ^= (mod << (da - dm));
        if (!a) break;
        da = poly_deg(a);
    }
    return a;
}

// Check irreducibility of polynomial p of degree m over GF(2)
bool is_irreducible(u32 p, int m) {
    for (int d = 1; d <= m / 2; ++d) {
        u32 high = 1u << d;
        u32 maxMask = 1u << (d - 1);
        for (u32 mask = 0; mask < maxMask; ++mask) {
            u32 q = high | (mask << 1) | 1u; // monic, constant term 1
            if (poly_mod(p, q) == 0u) return false;
        }
    }
    return true;
}

// Find an irreducible polynomial of degree m over GF(2)
u32 find_irreducible(int m) {
    u32 high = 1u << m;
    u32 maxMask = 1u << (m - 1);
    for (u32 mask = 0; mask < maxMask; ++mask) {
        u32 p = high | (mask << 1) | 1u; // monic, constant 1
        if (is_irreducible(p, m)) return p;
    }
    // Should never reach here for m <= 12
    return high | 3u;
}

// Multiplication in GF(2^m) with modulus poly (degree m)
u32 gf_mul(u32 a, u32 b, int m, u32 poly) {
    u32 res = 0;
    u32 top = 1u << m;
    while (b) {
        if (b & 1u) res ^= a;
        b >>= 1;
        a <<= 1;
        if (a & top) a ^= poly;
    }
    return res;
}

// Compute x^3 in GF(2^m)
u32 gf_cube(u32 x, int m, u32 poly) {
    u32 x2 = gf_mul(x, x, m, poly);
    u32 x3 = gf_mul(x2, x, m, poly);
    return x3;
}

// Build full-subcube-based set: S0 from GF(2^m) (excluding 0) plus high-bit singles
vector<int> build_full_subcube_set(int n, int m, int B, u32 poly) {
    int q = 1 << m;
    vector<int> res;
    // S0: encoded (x, x^3) for x = 1..q-1
    res.reserve(q + max(0, B + 1 - 2 * m));
    for (int x = 1; x < q; ++x) {
        u32 c = gf_cube((u32)x, m, poly);
        u32 e = ((u32)x << m) | c; // uses 2m bits
        // When 2m <= B, e < 2^(2m) <= 2^B <= n, but keep check for safety
        if (e >= 1u && e <= (u32)n)
            res.push_back((int)e);
    }
    // Add S1: single-bit numbers on bits [2m .. B]
    if (2 * m <= B) {
        for (int bit = 2 * m; bit <= B; ++bit) {
            u32 val = 1u << bit;
            if (val >= 1u && val <= (u32)n)
                res.push_back((int)val);
        }
    }
    return res;
}

// Build truncated set: subset of GF(2^m)-encoded elements with value in [1..n]
vector<int> build_truncated_set(int n, int m, u32 poly) {
    int q = 1 << m;
    vector<int> res;
    res.reserve(q);
    for (int x = 0; x < q; ++x) {
        u32 c = gf_cube((u32)x, m, poly);
        u32 e = ((u32)x << m) | c;
        if (e >= 1u && e <= (u32)n)
            res.push_back((int)e);
    }
    return res;
}

// Greedy fallback (used only if constructed set size < required, which should not happen)
vector<int> greedy_fallback(int n, int need) {
    const int MAXX = 1 << 24; // since n <= 1e7 < 2^24
    static vector<char> usedXor;
    usedXor.assign(MAXX, 0);
    vector<int> S;
    S.reserve(need);
    for (int val = 1; val <= n && (int)S.size() < need; ++val) {
        bool ok = true;
        for (int a : S) {
            int x = val ^ a;
            if (usedXor[x]) {
                ok = false;
                break;
            }
        }
        if (!ok) continue;
        for (int a : S) usedXor[val ^ a] = 1;
        S.push_back(val);
    }
    return S;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    // Small n: trivial solutions
    if (n <= 3) {
        cout << n << "\n";
        for (int i = 1; i <= n; ++i) {
            if (i > 1) cout << ' ';
            cout << i;
        }
        cout << "\n";
        return 0;
    }

    int R = (int)floor(sqrt((long double)n / 2.0L));

    // Precompute irreducible polynomials for m = 1..12
    const int MAXM = 12;
    u32 poly[MAXM + 1];
    for (int m = 1; m <= MAXM; ++m) {
        poly[m] = find_irreducible(m);
    }

    int B = 31 - __builtin_clz((unsigned int)n); // floor(log2 n)

    vector<int> result;

    if (B % 2 == 0) {
        // Even B: choose m = B/2, use full subcube + one high bit
        int m = B / 2;
        result = build_full_subcube_set(n, m, B, poly[m]);
    } else {
        // Odd B >= 3: consider m = (B-1)/2 with full subcube, and m+1 truncated
        int r = (B - 1) / 2; // r >= 1 since n > 3 -> B >= 2
        vector<int> setA = build_full_subcube_set(n, r, B, poly[r]);
        vector<int> setB = build_truncated_set(n, r + 1, poly[r + 1]);
        if (setB.size() > setA.size())
            result.swap(setB);
        else
            result.swap(setA);
    }

    // Safety fallback if somehow not enough (should not trigger)
    if ((int)result.size() < R) {
        vector<int> fallback = greedy_fallback(n, R);
        if ((int)fallback.size() >= R) result.swap(fallback);
    }

    cout << result.size() << "\n";
    for (size_t i = 0; i < result.size(); ++i) {
        if (i) cout << ' ';
        cout << result[i];
    }
    cout << "\n";
    return 0;
}