#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    long long n;
    if (!(cin >> n)) return 0;

    auto flog2 = [](unsigned long long x)->int{
        return x ? 63 - __builtin_clzll(x) : -1;
    };

    // Determine k such that 2^(2k) - 1 <= n
    unsigned long long np1 = (unsigned long long)n + 1;
    int L2 = flog2(np1);
    int k = max(0, L2 / 2);

    // Irreducible polynomials for GF(2^k) with top bit included (bit k)
    // Valid for k = 1..12 (sufficient for n <= 1e7)
    static const unsigned int irred[13] = {
        0,        // 0 (unused)
        0x3,      // x + 1
        0x7,      // x^2 + x + 1
        0xB,      // x^3 + x + 1
        0x13,     // x^4 + x + 1
        0x25,     // x^5 + x^2 + 1
        0x43,     // x^6 + x + 1
        0x83,     // x^7 + x + 1
        0x11B,    // x^8 + x^4 + x^3 + x + 1
        0x211,    // x^9 + x^4 + 1
        0x409,    // x^10 + x^3 + 1
        0x805,    // x^11 + x^2 + 1
        0x1009    // x^12 + x^3 + 1
    };

    auto gf_mul = [&](unsigned int a, unsigned int b, unsigned int mod, int kk)->unsigned int{
        unsigned int res = 0;
        unsigned int top = 1u << kk;
        while (b) {
            if (b & 1u) res ^= a;
            b >>= 1;
            bool carry = (a & top) != 0;
            a <<= 1;
            if (carry) a ^= mod;
        }
        return res & (top - 1);
    };

    auto gf_cube = [&](unsigned int x, unsigned int mod, int kk)->unsigned int{
        unsigned int sq = gf_mul(x, x, mod, kk);
        return gf_mul(sq, x, mod, kk);
    };

    vector<unsigned int> S;

    if (k >= 1) {
        // Ensure 2^(2k) - 1 <= n
        unsigned long long maxValSpace = (1ull << (2*k)) - 1ull;
        if (maxValSpace > (unsigned long long)n) {
            // Adjust k downward if necessary due to rounding
            while (k > 0 && ((1ull << (2*k)) - 1ull) > (unsigned long long)n) --k;
        }
    }
    if (k >= 1) {
        unsigned int mod = irred[k];
        unsigned int size = 1u << k;
        // We skip x = 0 because it maps to 0 which is not in [1..n]
        for (unsigned int x = 1; x < size; ++x) {
            unsigned int fx = gf_cube(x, mod, k); // x^3 in GF(2^k)
            unsigned int val = (fx << k) | x;
            if (val >= 1 && val <= (unsigned int)n) S.push_back(val);
        }
    }

    if (S.empty()) {
        // Fallback for very small n
        unsigned int m = (n >= 1 ? 1u : 0u);
        cout << m << "\n";
        if (m) cout << 1 << "\n";
        else cout << "\n";
        return 0;
    }

    cout << S.size() << "\n";
    for (size_t i = 0; i < S.size(); ++i) {
        if (i) cout << ' ';
        cout << S[i];
    }
    cout << "\n";
    return 0;
}