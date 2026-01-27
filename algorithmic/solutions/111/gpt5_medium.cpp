#include <bits/stdc++.h>
using namespace std;

static const unsigned int polys[11] = {
    0,
    0b11,          // m=1: x + 1
    0b111,         // m=2: x^2 + x + 1
    0b1011,        // m=3: x^3 + x + 1
    0b10011,       // m=4: x^4 + x + 1
    0b100101,      // m=5: x^5 + x^2 + 1
    0b1000001,     // m=6: x^6 + x + 1
    0b10000011,    // m=7: x^7 + x + 1
    0x11D,         // m=8: x^8 + x^4 + x^3 + x^2 + 1
    0x211,         // m=9: x^9 + x^4 + 1
    0x409          // m=10: x^10 + x^3 + 1
};

static inline uint32_t gf_mul(uint32_t a, uint32_t b, int m, uint32_t poly) {
    uint32_t res = 0;
    while (b) {
        if (b & 1) res ^= a;
        b >>= 1;
        a <<= 1;
        if (a & (1u << m)) a ^= poly;
    }
    return res;
}

vector<unsigned int> greedy_small(unsigned int n) {
    if (n == 0) return {};
    int L = 0;
    while ((1u << L) <= n) ++L;
    vector<uint8_t> used(1u << L, 0);
    vector<unsigned int> S;
    S.reserve(n);
    for (unsigned int x = 1; x <= n; ++x) {
        bool ok = true;
        for (unsigned int s : S) {
            unsigned int v = x ^ s;
            if (used[v]) { ok = false; break; }
        }
        if (ok) {
            for (unsigned int s : S) {
                used[x ^ s] = 1;
            }
            S.push_back(x);
        }
    }
    return S;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    unsigned int n;
    if (!(cin >> n)) return 0;

    // Find maximum m with (2^(3m) - 1) <= n
    int m = 0;
    while (true) {
        int nm = m + 1;
        if (3 * nm >= 63) break; // safe guard for shifts, though n <= 1e7
        uint64_t maxv = (1ULL << (3 * nm)) - 1;
        if (maxv <= n) m = nm;
        else break;
    }

    vector<unsigned int> ans;

    if (m >= 2) {
        // Use construction: S = { (i, j, i*j) } over GF(2^m), concatenated blocks, optionally shifted by 1
        uint32_t poly = polys[m];
        uint32_t q = 1u << m;
        uint64_t vmax = (1ULL << (3 * m)) - 1;
        bool shift = ((1ULL << (3 * m)) <= n);
        ans.reserve((size_t)q * (size_t)q);
        for (uint32_t i = 0; i < q; ++i) {
            for (uint32_t j = 0; j < q; ++j) {
                uint32_t prod = gf_mul(i, j, m, poly);
                uint32_t v = (i << (2 * m)) | (j << m) | prod;
                if (!shift && v == 0) continue; // avoid zero
                if (shift) ++v;
                ans.push_back(v);
            }
        }
    } else {
        // Small n: greedy build
        ans = greedy_small(n);
    }

    cout << ans.size() << "\n";
    if (!ans.empty()) {
        for (size_t i = 0; i < ans.size(); ++i) {
            if (i) cout << ' ';
            cout << ans[i];
        }
    }
    cout << "\n";
    return 0;
}