#include <bits/stdc++.h>
using namespace std;

static inline uint32_t rotl32(uint32_t x, int r) {
    return (x << r) | (x >> (32 - r));
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    uint32_t n;
    if (!(cin >> n)) return 0;

    // Target size
    uint32_t T = (uint32_t)floor(sqrt((long double)n / 2.0));
    if (T == 0) T = 1;

    // Choose low block size L so that max value <= n for i in [1..T]
    // Need (T+1) * 2^L - 1 <= n  =>  2^L <= (n+1)/(T+1)
    uint64_t limit = (uint64_t)n + 1;
    uint32_t L = 0;
    while (((uint64_t)1 << (L + 1)) <= limit / (uint64_t)(T + 1)) ++L;
    uint32_t lowMask = (L == 32 ? 0xFFFFFFFFu : ((1u << L) - 1u)); // L <= 31 here given constraints

    // Size for seen XOR bitset: need to cover up to maximum XOR of two numbers <= 2^k - 1, where 2^k > n
    uint32_t k = 0;
    while ((1u << k) <= n) ++k;
    uint32_t sizeX = 1u << k;

    vector<uint8_t> seenX(sizeX);
    vector<uint32_t> vals(T + 1);

    std::mt19937 rng((uint32_t)chrono::high_resolution_clock::now().time_since_epoch().count());

    auto gen_val = [&](uint32_t i, uint32_t A, uint32_t B, uint32_t C, int s1, int s2, int r1, int r2) -> uint32_t {
        uint32_t x = i;
        uint32_t y1 = (uint32_t)((uint64_t)x * A);
        uint32_t y2 = (uint32_t)((uint64_t)x * B);
        uint32_t y3 = (uint32_t)((uint64_t)x * x);
        uint32_t y = y1 ^ (y2 << s1) ^ (y1 >> s2) ^ (y3 * C);
        y ^= rotl32(x, r1);
        y ^= rotl32(y1, r2);
        y &= lowMask;
        return (i << L) | y;
    };

    bool ok = false;
    const int MAX_ATTEMPTS = 80;
    for (int attempt = 0; attempt < MAX_ATTEMPTS && !ok; ++attempt) {
        // Random parameters
        uint32_t A = (rng() | 1u);
        uint32_t B = (rng() | 1u);
        uint32_t C = (rng() | 1u);
        int s1 = (rng() % max(1u, L)) % 16;
        int s2 = (rng() % 16) + 1;
        int r1 = (rng() % 31) + 1;
        int r2 = (rng() % 31) + 1;

        // Build values
        for (uint32_t i = 1; i <= T; ++i) {
            vals[i] = gen_val(i, A, B, C, s1, s2, r1, r2);
        }

        // Verify bounds (should hold by construction), but ensure <= n
        bool in_range = true;
        for (uint32_t i = 1; i <= T; ++i) {
            if (vals[i] == 0 || vals[i] > n) { in_range = false; break; }
        }
        if (!in_range) continue;

        // Clear seenX
        memset(seenX.data(), 0, sizeX * sizeof(uint8_t));

        // Check pairwise XOR uniqueness
        ok = true;
        for (uint32_t i = 1; i <= T && ok; ++i) {
            for (uint32_t j = i + 1; j <= T; ++j) {
                uint32_t z = vals[i] ^ vals[j];
                if (seenX[z]) { ok = false; break; }
                seenX[z] = 1;
            }
        }
    }

    // Fallback: if somehow not ok (extremely unlikely), output simple increasing numbers
    if (!ok) {
        cout << T << "\n";
        for (uint32_t i = 1; i <= T; ++i) {
            if (i > 1) cout << ' ';
            cout << i;
        }
        cout << "\n";
        return 0;
    }

    cout << T << "\n";
    for (uint32_t i = 1; i <= T; ++i) {
        if (i > 1) cout << ' ';
        cout << vals[i];
    }
    cout << "\n";
    return 0;
}