#include <bits/stdc++.h>
using namespace std;

static const uint32_t polys[] = {
    0x0,
    0x3,     // x^1 + x^0
    0x7,     // x^2 + x^1 + 1
    0xB,     // x^3 + x + 1
    0x13,    // x^4 + x + 1
    0x25,    // x^5 + x^2 + 1
    0x43,    // x^6 + x + 1
    0x89,    // x^7 + x^3 + 1
    0x11D,   // x^8 + x^4 + x^3 + x^2 + 1
    0x211,   // x^9 + x^4 + 1
    0x409,   // x^10 + x^3 + 1
    0x805,   // x^11 + x^2 + 1
    0x1053   // x^12 + x^6 + x^4 + x + 1
};

inline uint32_t gf_mul(uint32_t a, uint32_t b, int m, uint32_t poly) {
    uint32_t res = 0;
    uint32_t mask = (1u << m) - 1u;
    uint32_t pr = poly & mask; // poly without the leading x^m term
    while (b) {
        if (b & 1u) res ^= a;
        b >>= 1u;
        uint32_t carry = (a >> (m - 1)) & 1u;
        a = (a << 1) & mask;
        if (carry) a ^= pr;
    }
    return res & mask;
}

uint32_t gf_pow(uint32_t x, uint32_t e, int m, uint32_t poly) {
    uint32_t res = 1;
    while (e) {
        if (e & 1u) res = gf_mul(res, x, m, poly);
        x = gf_mul(x, x, m, poly);
        e >>= 1u;
    }
    return res;
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

    // Compute m = floor(log2(n+1) / 2)
    unsigned long long K = (unsigned long long)n + 1ull;
    int k2 = 0;
    unsigned long long tmpK = K;
    while ((tmpK >> 1) > 0) {
        tmpK >>= 1;
        k2++;
    }
    int m = k2 / 2;

    if (m == 0) {
        // Minimal valid set
        cout << 1 << "\n" << 1 << "\n";
        return 0;
    }

    uint32_t poly = polys[m];
    uint32_t q = 1u << m;
    uint32_t maskm = q - 1u;

    // Build base set S0 in low 2m bits: (x, x^{-1}) for x in F_{2^m}^*
    vector<uint32_t> base;
    base.reserve(q - 1);
    for (uint32_t x = 1; x < q; ++x) {
        uint32_t inv = gf_pow(x, q - 2, m, poly); // inverse in GF(2^m)
        uint32_t val = (x << m) | inv;            // concatenate
        base.push_back(val);
    }

    // Number of available high prefixes
    unsigned long long blockSize = 1ull << (2 * m);
    unsigned long long Pcount = K / blockSize; // number of prefixes available (0..Pcount-1)
    if (Pcount == 0) Pcount = 1; // safety

    // Build prefix Sidon set: {0} U {1,2,4,...} up to <= Pcount-1
    vector<unsigned long long> pref;
    pref.push_back(0);
    if (Pcount >= 2) {
        unsigned long long limit = Pcount - 1;
        unsigned long long p = 1;
        while (p <= limit) {
            pref.push_back(p);
            p <<= 1;
        }
    }

    // Assemble final set
    vector<unsigned long long> ans;
    ans.reserve((size_t)pref.size() * base.size());
    for (auto p : pref) {
        unsigned long long high = p << (2 * m);
        for (auto b : base) {
            unsigned long long val = high | b;
            if (val <= (unsigned long long)n) ans.push_back(val);
        }
    }

    cout << ans.size() << "\n";
    for (size_t i = 0; i < ans.size(); ++i) {
        if (i) cout << ' ';
        cout << ans[i];
    }
    cout << "\n";
    return 0;
}