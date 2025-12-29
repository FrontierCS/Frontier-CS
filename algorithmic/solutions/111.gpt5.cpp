#include <bits/stdc++.h>
using namespace std;

static inline int poly_deg(uint32_t x) {
    if (x == 0) return -1;
    return 31 - __builtin_clz(x);
}

static uint32_t poly_mod(uint32_t a, uint32_t p) {
    int m = poly_deg(p);
    while (a && poly_deg(a) >= m) {
        int shift = poly_deg(a) - m;
        a ^= (p << shift);
    }
    return a;
}

static uint32_t poly_gcd(uint32_t a, uint32_t b) {
    while (b) {
        uint32_t r = poly_mod(a, b);
        a = b;
        b = r;
    }
    return a;
}

static uint32_t poly_square_mod(uint32_t a, uint32_t p) {
    uint32_t res = 0;
    for (int i = 0; i <= poly_deg(a); ++i) {
        if (a & (1u << i)) res ^= (1u << (2*i));
    }
    return poly_mod(res, p);
}

static bool is_irreducible(uint32_t p, int m) {
    if (((p >> m) & 1u) == 0) return false;
    if ((p & 1u) == 0) return false; // constant term must be 1
    uint32_t x = 2; // polynomial 'x'
    uint32_t h = x;
    for (int i = 1; i <= m; ++i) {
        h = poly_square_mod(h, p); // h = h^2 mod p
        if (i <= (m >> 1)) {
            uint32_t g = poly_gcd(h ^ x, p);
            if (g != 1u) return false;
        }
    }
    // Check x^{2^m} == x (mod p)
    return (h == x);
}

static uint32_t find_irreducible_poly(int m) {
    if (m == 0) return 1; // not used
    uint32_t start = (1u << m) | 1u;
    uint32_t end = (1u << (m+1));
    for (uint32_t p = start; p < end; p += 2) { // LSB must be 1
        if (is_irreducible(p, m)) return p;
    }
    // Fallback (should not happen for small m)
    return start;
}

struct GF2 {
    int m;                // degree
    uint32_t poly;        // irreducible polynomial with bit m set
    uint32_t red_low;     // poly without highest bit
    uint32_t mask;        // (1<<m)-1
    GF2(int m_) : m(m_) {
        poly = find_irreducible_poly(m);
        red_low = poly & ((1u << m) - 1);
        mask = (m ? ((1u << m) - 1) : 0);
    }
    inline uint32_t xtime(uint32_t a) const {
        uint32_t carry = (a >> (m - 1)) & 1u;
        a = (a << 1) & mask;
        if (carry) a ^= red_low;
        return a;
    }
    inline uint32_t mul(uint32_t a, uint32_t b) const {
        uint32_t res = 0;
        while (b) {
            if (b & 1u) res ^= a;
            b >>= 1;
            if (b) a = xtime(a);
        }
        return res;
    }
    inline uint32_t pow3(uint32_t a) const {
        if (m == 0) return 0;
        uint32_t a2 = mul(a, a);
        return mul(a2, a);
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    uint32_t n;
    if (!(cin >> n)) return 0;
    if (n == 0) {
        cout << 0 << "\n\n";
        return 0;
    }
    if (n == 1) {
        cout << 1 << "\n1\n";
        return 0;
    }
    int k = 32 - __builtin_clz(n); // number of bits to represent n
    int r = k / 2;
    int s = k - r;
    vector<uint32_t> ans;
    if (r == 0) {
        // k=1
        // n>=1; we can output {1}
        cout << 1 << "\n1\n";
        return 0;
    }
    GF2 gf(r);
    uint32_t c = 1; // nonzero constant to avoid zero output
    if (k % 2 == 1) {
        // odd k: use val = (f(x) << r) | x, topmost bit (k-1) is zero implicitly
        uint32_t M = 1u << r;
        ans.reserve(M);
        for (uint32_t x = 0; x < M; ++x) {
            uint32_t fx = gf.pow3(x) ^ c;
            uint32_t val = (fx << r) | x;
            if (val >= 1 && val <= n) ans.push_back(val);
        }
        // In this construction, all val <= 2^(k-1)-1 <= n, so all included and nonzero due to c=1.
    } else {
        // even k: use val = (x << s) | f(x), take x in [0, H-1]
        uint32_t H = n >> s; // floor(n / 2^s)
        uint32_t M = 1u << r;
        if (H > M) H = M; // just in case
        ans.reserve(H);
        for (uint32_t x = 0; x < H; ++x) {
            uint32_t fx = gf.pow3(x) ^ c;
            uint32_t val = (x << s) | fx;
            // For x in [0, H-1], val <= H*2^s - 1 <= n and val >= 1 due to c=1.
            ans.push_back(val);
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