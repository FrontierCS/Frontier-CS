#include <bits/stdc++.h>
using namespace std;

// GF(2^3) with primitive polynomial x^3 + x + 1 (binary 0b1011)
static inline uint8_t gf_mul(uint8_t a, uint8_t b) {
    uint8_t res = 0;
    for (int i = 0; i < 3; ++i) {
        if ((b >> i) & 1) res ^= (a << i);
    }
    // Reduce modulo x^3 + x + 1
    for (int t = 4; t >= 3; --t) {
        if (res & (1u << t)) {
            res ^= (0b1011u << (t - 3));
        }
    }
    return res & 0b111u;
}

static inline uint8_t gf_add(uint8_t a, uint8_t b) {
    return (a ^ b) & 0b111u;
}

static inline uint8_t gf_eval_poly(const uint8_t *m, uint8_t x) {
    // m[0] + m[1]*x + m[2]*x^2 + m[3]*x^3
    uint8_t acc = m[3];
    acc = gf_mul(acc, x); acc = gf_add(acc, m[2]);
    acc = gf_mul(acc, x); acc = gf_add(acc, m[1]);
    acc = gf_mul(acc, x); acc = gf_add(acc, m[0]);
    return acc;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int R, H;
    if (!(cin >> R >> H)) {
        return 0;
    }

    const int q = 8;        // GF(8)
    const int n0 = 8;       // RS length
    const int k = 4;        // RS dimension
    const int Npos = 1000;  // number of positions
    const int mtests = n0 * q; // 64 tests

    // Precompute code symbols for positions 1..1000
    vector<array<uint8_t, n0>> sym(Npos + 1);
    vector<uint64_t> mask(Npos + 1, 0);

    for (int pos = 1; pos <= Npos; ++pos) {
        int v = pos - 1;
        uint8_t m[4];
        for (int i = 0; i < k; ++i) {
            m[i] = v % q;
            v /= q;
        }
        for (int i = 0; i < n0; ++i) {
            uint8_t beta = (uint8_t)i; // use all 8 field elements {0..7}
            uint8_t s = gf_eval_poly(m, beta);
            sym[pos][i] = s;
            int testIndex = i * q + s;
            mask[pos] |= (1ULL << testIndex);
        }
    }

    // Build tests: for each of 64 tests, list positions included
    vector<vector<int>> tests(mtests);
    for (int pos = 1; pos <= Npos; ++pos) {
        for (int i = 0; i < n0; ++i) {
            uint8_t s = sym[pos][i];
            tests[i * q + s].push_back(pos);
        }
    }

    // Send queries
    for (int t = 0; t < mtests; ++t) {
        cout << "? " << tests[t].size();
        for (int x : tests[t]) cout << ' ' << x;
        cout << endl;
    }

    // Get results
    cout << "@" << endl;

    int L;
    if (!(cin >> L)) return 0;
    vector<int> ans(L);
    for (int i = 0; i < L; ++i) cin >> ans[i];

    // Build result mask
    uint64_t ymask = 0;
    for (int i = 0; i < L && i < mtests; ++i) {
        if (ans[i]) ymask |= (1ULL << i);
    }

    // First pass: candidates whose mask is subset of ymask
    vector<int> cand;
    cand.reserve(2);
    for (int pos = 1; pos <= Npos; ++pos) {
        if ((mask[pos] & ~ymask) == 0ULL) {
            cand.push_back(pos);
            if (cand.size() > 4) break; // safeguard
        }
    }

    auto matches = [&](int a, int b) -> bool {
        uint64_t mm = mask[a] | mask[b];
        return mm == ymask;
    };

    int a = 1, b = 1;

    if (cand.size() == 1) {
        a = b = cand[0];
    } else if (cand.size() >= 2) {
        // Try all pairs among candidates first
        bool found = false;
        for (size_t i = 0; i < cand.size() && !found; ++i) {
            for (size_t j = i; j < cand.size(); ++j) {
                if (matches(cand[i], cand[j])) {
                    a = cand[i];
                    b = cand[j];
                    found = true;
                    break;
                }
            }
        }
        if (!found) {
            // Fallback full search (unlikely needed)
            bool ok = false;
            for (int i = 1; i <= Npos && !ok; ++i) {
                for (int j = i; j <= Npos; ++j) {
                    if (matches(i, j)) {
                        a = i; b = j; ok = true; break;
                    }
                }
            }
        }
    } else {
        // No candidate found via subset check: do full search
        bool ok = false;
        for (int i = 1; i <= Npos && !ok; ++i) {
            for (int j = i; j <= Npos; ++j) {
                if (matches(i, j)) {
                    a = i; b = j; ok = true; break;
                }
            }
        }
    }

    cout << "! " << a << ' ' << b << endl;
    return 0;
}