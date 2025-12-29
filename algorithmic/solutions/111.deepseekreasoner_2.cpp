#include <bits/stdc++.h>
using namespace std;

typedef unsigned int uint;

// multiply two elements in GF(2^k) modulo irreducible polynomial poly
uint mul_gf(uint a, uint b, uint poly, int k) {
    uint res = 0;
    uint mask = (1U << k) - 1;
    a &= mask;
    while (b) {
        if (b & 1) res ^= a;
        a <<= 1;
        if (a >> k) a ^= poly;
        b >>= 1;
    }
    return res & mask;
}

// power a^e in GF(2^k)
uint pow_gf(uint a, uint e, uint poly, int k) {
    uint res = 1;
    while (e) {
        if (e & 1) res = mul_gf(res, a, poly, k);
        a = mul_gf(a, a, poly, k);
        e >>= 1;
    }
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    int n;
    cin >> n;

    // required minimum size
    int L = (int)sqrt(n / 2.0);

    // count how many powers of two are <= n
    int count_pow = 0;
    while ((1 << count_pow) <= n) ++count_pow;

    // if powers of two suffice, use them
    if (L <= count_pow) {
        int m = max(L, 1);
        cout << m << '\n';
        for (int i = 0; i < m; ++i) {
            cout << (1 << i);
            if (i < m - 1) cout << ' ';
        }
        cout << '\n';
        return 0;
    }

    // otherwise, use the finite field construction
    int k = (int)ceil(log2(L + 1.0));   // smallest k with 2^k >= L+1
    if (k > 20) k = 20;                 // safety cap

    // precomputed irreducible polynomials for degrees 1..20
    // (each polynomial is represented as an integer with the high bit set)
    vector<uint> irred = {0,
        3,      // k=1:  x+1
        7,      // k=2:  x^2+x+1
        11,     // k=3:  x^3+x+1
        19,     // k=4:  x^4+x+1
        37,     // k=5:  x^5+x^2+1
        67,     // k=6:  x^6+x+1
        131,    // k=7:  x^7+x+1
        285,    // k=8:  x^8+x^4+x^3+x^2+1
        529,    // k=9:  x^9+x^4+1
        1033,   // k=10: x^10+x^3+1
        2053,   // k=11: x^11+x^2+1
        4105,   // k=12: x^12+x^3+1
        8219,   // k=13: x^13+x^4+x^3+x+1
        16427,  // k=14: x^14+x^5+x^3+x+1
        32771,  // k=15: x^15+x+1
        65581,  // k=16: x^16+x^5+x^3+x^2+1
        131081, // k=17: x^17+x^3+1
        262153, // k=18: x^18+x^7+1
        524327, // k=19: x^19+x^5+x^2+x+1
        1048585 // k=20: x^20+x^3+1
    };
    if (k >= (int)irred.size()) k = (int)irred.size() - 1;
    uint poly = irred[k];

    int limit = 1 << k;
    vector<uint> inv(limit, 0);
    uint exponent = (1ULL << k) - 2;   // a^{-1} = a^{2^k-2}
    for (int x = 1; x < limit; ++x) {
        inv[x] = pow_gf(x, exponent, poly, k);
    }

    vector<int> candidates;
    for (int x = 1; x < limit; ++x) {
        uint A = (x << k) | inv[x];   // concatenation of x and inv(x)
        if (A <= (uint)n) {
            candidates.push_back(A);
        }
    }

    // output the found set (its size is at least L by construction)
    int m = candidates.size();
    cout << m << '\n';
    for (int i = 0; i < m; ++i) {
        cout << candidates[i];
        if (i < m - 1) cout << ' ';
    }
    cout << '\n';
    return 0;
}