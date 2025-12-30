#include <bits/stdc++.h>
using namespace std;

static uint32_t xorshift32(uint32_t &state) {
    state ^= state << 13;
    state ^= state >> 17;
    state ^= state << 5;
    return state;
}

static uint32_t gf_mul(uint32_t a, uint32_t b, int deg, uint32_t poly) {
    if (deg == 0) return 0;
    uint32_t res = 0;
    uint32_t mask = (1u << deg) - 1u;
    uint32_t polyLow = poly & mask; // poly without leading term implicitly used on reduction
    for (int i = 0; i < deg; i++) {
        if (b & 1u) res ^= a;
        b >>= 1u;

        uint32_t carry = a & (1u << (deg - 1));
        a = (a << 1u) & mask;
        if (carry) a ^= polyLow;
    }
    return res & ((1u << deg) - 1u);
}

static vector<uint32_t> build_base(int deg) {
    if (deg == 0) return {0u};

    // Irreducible / primitive polynomials over GF(2), with the x^deg term included.
    static const uint32_t poly[13] = {
        0u,
        0b11u,          // 1: x + 1
        0b111u,         // 2: x^2 + x + 1
        0b1011u,        // 3: x^3 + x + 1
        0b10011u,       // 4: x^4 + x + 1
        0b100101u,      // 5: x^5 + x^2 + 1
        0b1000011u,     // 6: x^6 + x + 1
        0b10001001u,    // 7: x^7 + x^3 + 1
        0b100011101u,   // 8: x^8 + x^4 + x^3 + x^2 + 1 (0x11D)
        0b1000010001u,  // 9: x^9 + x^4 + 1 (0x211)
        0b10000001001u, // 10: x^10 + x^3 + 1 (0x409)
        0b100000000101u,// 11: x^11 + x^2 + 1 (0x805)
        0b1000001010011u// 12: x^12 + x^6 + x^4 + x + 1 (0x1053)
    };

    uint32_t p = poly[deg];
    int sz = 1 << deg;

    vector<uint32_t> cube(sz);
    for (int x = 0; x < sz; x++) {
        uint32_t xx = gf_mul((uint32_t)x, (uint32_t)x, deg, p);
        cube[x] = gf_mul(xx, (uint32_t)x, deg, p); // x^3 in GF(2^deg)
    }

    vector<uint32_t> base;
    base.reserve(sz);
    for (int x = 0; x < sz; x++) {
        uint32_t y = cube[x];
        uint32_t v = (y << deg) | (uint32_t)x;
        base.push_back(v);
    }
    return base;
}

static long long req_size(long long n) {
    long double val = (long double)n / 2.0L;
    long long r = (long long) floor(sqrtl(val));
    while ((r + 1) * (r + 1) * 2LL <= n) r++;
    while (r * r * 2LL > n) r--;
    return r;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    uint32_t n;
    cin >> n;

    if (n == 0) {
        cout << 0 << "\n\n";
        return 0;
    }

    long long need = req_size(n);

    int k = 32 - __builtin_clz(n);
    int deg = k / 2; // floor
    if (deg == 0) {
        // Just output {1} if possible
        if (n >= 1) {
            cout << 1 << "\n1\n";
        } else {
            cout << 0 << "\n\n";
        }
        return 0;
    }

    auto try_build = [&](int useDeg) -> vector<uint32_t> {
        vector<uint32_t> base = build_base(useDeg);
        int dim = 2 * useDeg;
        uint32_t maskLimit = (dim == 32) ? 0xFFFFFFFFu : ((1u << dim) - 1u);

        vector<uint32_t> baseSorted = base;
        sort(baseSorted.begin(), baseSorted.end());

        auto in_base = [&](uint32_t x) -> bool {
            return binary_search(baseSorted.begin(), baseSorted.end(), x);
        };

        // If dim < k, all values are < 2^dim <= 2^(k-1) <= n; we can output all 2^useDeg elements
        // by choosing a mask within [1, 2^dim) that is not in base (so no element maps to 0).
        if (dim < k) {
            uint32_t mask = 1;
            while (mask <= maskLimit && in_base(mask)) mask++;
            if (mask > maskLimit) mask = 0; // shouldn't happen
            vector<uint32_t> out;
            out.reserve(base.size());
            for (uint32_t a : base) {
                uint32_t v = a ^ mask;
                if (v >= 1 && v <= n) out.push_back(v);
            }
            return out;
        }

        // dim == k: need to choose XOR-mask so many land in [1..n]
        uint32_t bestMask = 0;
        int bestCnt = -1;

        auto eval_mask = [&](uint32_t mask) {
            int cnt = 0;
            for (uint32_t a : base) {
                uint32_t v = a ^ mask;
                if (v && v <= n) cnt++;
            }
            if (cnt > bestCnt) {
                bestCnt = cnt;
                bestMask = mask;
            }
        };

        // Deterministic candidates
        vector<uint32_t> cand;
        cand.reserve(64);
        cand.push_back(0u);
        cand.push_back(1u);
        cand.push_back(maskLimit);
        cand.push_back(1u << (dim - 1));
        cand.push_back(n & maskLimit);
        cand.push_back((n ^ maskLimit) & maskLimit);
        cand.push_back((n >> 1) & maskLimit);
        cand.push_back(((n >> 1) ^ maskLimit) & maskLimit);

        for (uint32_t m : cand) eval_mask(m);

        // Random-ish deterministic masks
        uint32_t state = 0x9E3779B9u ^ n ^ (uint32_t)(useDeg * 1234567u);
        int attempts = (useDeg >= 11 ? 40000 : 20000);
        for (int i = 0; i < attempts; i++) {
            uint32_t m = xorshift32(state) & maskLimit;
            eval_mask(m);
            if (bestCnt == (int)base.size()) break;
        }

        vector<uint32_t> out;
        out.reserve(base.size());
        for (uint32_t a : base) {
            uint32_t v = a ^ bestMask;
            if (v >= 1 && v <= n) out.push_back(v);
        }
        return out;
    };

    vector<uint32_t> ans = try_build(deg);

    if (deg >= 2) {
        vector<uint32_t> ans2 = try_build(deg - 1);
        if (ans2.size() > ans.size()) ans.swap(ans2);
    }

    // Ensure requirement met (should be)
    if ((long long)ans.size() < need) {
        // Very unlikely fallback: output simple small valid set {1..m} for m=need (only safe for tiny need).
        // We'll instead output powers of two plus 1..something if need small; otherwise keep ans.
        if (need <= 5000 && n >= (uint32_t)need) {
            // Brute greedy for small need
            int kk = 32 - __builtin_clz(n);
            uint32_t xorLimit = (kk == 32) ? 0xFFFFFFFFu : ((1u << kk) - 1u);
            vector<uint8_t> used(xorLimit + 1u, 0);
            vector<uint32_t> s;
            s.reserve((size_t)need);

            auto can_add = [&](uint32_t x) -> bool {
                for (uint32_t a : s) {
                    uint32_t v = a ^ x;
                    if (used[v]) return false;
                }
                return true;
            };
            auto add = [&](uint32_t x) {
                for (uint32_t a : s) used[a ^ x] = 1;
                s.push_back(x);
            };

            for (uint32_t x = 1; x <= n && (long long)s.size() < need; x++) {
                if (can_add(x)) add(x);
            }
            if ((long long)s.size() >= need) ans = std::move(s);
        }
    }

    cout << ans.size() << "\n";
    for (size_t i = 0; i < ans.size(); i++) {
        if (i) cout << ' ';
        cout << ans[i];
    }
    cout << "\n";
    return 0;
}