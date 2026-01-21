#include <bits/stdc++.h>
using namespace std;

// Polynomial operations over GF(2)
static inline int poly_deg(uint32_t a) {
    if (a == 0) return -1;
    return 31 - __builtin_clz(a);
}

static uint32_t poly_mod(uint32_t a, uint32_t b) {
    int db = poly_deg(b);
    while (a != 0) {
        int da = poly_deg(a);
        if (da < db) break;
        a ^= (b << (da - db));
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

static inline uint32_t gf_mul(uint32_t a, uint32_t b, uint32_t mod, int l) {
    uint32_t res = 0;
    uint32_t top = 1u << l;
    while (b) {
        if (b & 1u) res ^= a;
        b >>= 1u;
        a <<= 1u;
        if (a & top) a ^= mod;
    }
    return res;
}

static inline uint32_t gf_square(uint32_t a, uint32_t mod, int l) {
    return gf_mul(a, a, mod, l);
}

static inline uint32_t pow_x_2k_mod(uint32_t mod, int l, int times) {
    uint32_t x = 2u; // polynomial 'x'
    for (int i = 0; i < times; ++i) {
        x = gf_square(x, mod, l);
    }
    return x;
}

static vector<int> factorize_int(int x) {
    vector<int> res;
    int t = x;
    for (int p = 2; p * p <= t; ++p) {
        if (t % p == 0) {
            res.push_back(p);
            while (t % p == 0) t /= p;
        }
    }
    if (t > 1) res.push_back(t);
    return res;
}

static uint32_t find_irreducible(int l) {
    if (l == 0) return 1; // dummy
    // Rabin irreducibility test
    vector<int> primes = factorize_int(l);
    uint32_t start = (1u << l) | 1u; // ensure constant term is 1
    for (uint32_t p = start; p < (1u << (l + 1)); p += 2u) { // step by 2 to keep constant term 1
        if ((p & (1u << l)) == 0) continue; // must be degree l
        // Check x^(2^l) = x (mod p)
        uint32_t r = pow_x_2k_mod(p, l, l);
        if (r != 2u) continue;
        bool ok = true;
        for (int q : primes) {
            int e = l / q;
            uint32_t t = pow_x_2k_mod(p, l, e);
            uint32_t g = poly_gcd(p, t ^ 2u);
            if (g != 1u) {
                ok = false;
                break;
            }
        }
        if (ok) return p;
    }
    // Fallback (should not happen for small l), but ensure some return
    return (1u << l) | 1u;
}

static pair<uint32_t,int> choose_best_K_deterministic(const vector<uint32_t>& s, int k, uint32_t n) {
    int m = (int)s.size();
    vector<int> eq, eq0, eq1;
    eq.reserve(m);
    eq0.reserve(m);
    eq1.reserve(m);
    for (int i = 0; i < m; ++i) eq.push_back(i);
    uint32_t K = 0;
    for (int j = k - 1; j >= 0; --j) {
        eq0.clear(); eq1.clear();
        for (int idx : eq) {
            if ((s[idx] >> j) & 1u) eq1.push_back(idx);
            else eq0.push_back(idx);
        }
        int nbit = (n >> j) & 1u;
        int mbit = (int)(eq1.size() >= eq0.size()); // majority bit among s at bit j for current equal-set
        if (nbit == 0) {
            // Keep those with s_j == K_j to remain equal; choose K_j = majority bit to keep more
            if (mbit) {
                K |= (1u << j);
                eq.swap(eq1);
            } else {
                // K_j already 0
                eq.swap(eq0);
            }
        } else { // nbit == 1
            // Those with s_j == K_j become 'less' (counted), those with s_j != K_j remain equal
            if (mbit) {
                K |= (1u << j);
                eq.swap(eq0); // equal becomes minority group
            } else {
                // K_j = 0
                eq.swap(eq1);
            }
        }
    }
    // The actual count will be computed externally considering [1..n]
    return {K, 0};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    uint32_t n;
    if (!(cin >> n)) return 0;

    int k = 32 - __builtin_clz(n); // bits to represent n (n>=1)
    int l = k / 2;

    vector<uint32_t> base;
    if (l == 0) {
        base.push_back(0u);
    } else {
        uint32_t poly = find_irreducible(l);
        int m = 1 << l;
        base.resize(m);
        for (int i = 0; i < m; ++i) {
            uint32_t ii = (uint32_t)i;
            uint32_t sq = gf_mul(ii, ii, poly, l);
            uint32_t cube = gf_mul(ii, sq, poly, l);
            uint32_t val = (cube << l) | ii; // high l bits: cube, low l bits: i
            base[i] = val;
        }
    }

    uint32_t maskK = (k == 32) ? 0xFFFFFFFFu : ((1u << k) - 1u);

    auto compute_answer = [&](uint32_t K, vector<uint32_t>& out) {
        out.clear();
        for (uint32_t v : base) {
            uint32_t x = (v ^ K) & maskK;
            if (x >= 1u && x <= n) out.push_back(x);
        }
    };

    // Deterministic best K using bitwise greedy DP
    auto pr = choose_best_K_deterministic(base, k, n);
    uint32_t bestK = pr.first;
    vector<uint32_t> bestAns;
    bestAns.reserve(base.size());
    compute_answer(bestK, bestAns);
    size_t bestSz = bestAns.size();

    // If needed, try some random Ks to potentially improve or to avoid zero issue
    // Also try some heuristic Ks
    uint64_t rng = 0x9E3779B97F4A7C15ull; // fixed seed
    auto rnd = [&]() {
        rng ^= rng << 7;
        rng ^= rng >> 9;
        rng ^= rng << 8;
        return rng;
    };
    vector<uint32_t> cand;
    cand.reserve(base.size());

    // Heuristic tries: try toggling some low bits of bestK
    for (int j = 0; j < min(k, 8); ++j) {
        uint32_t K2 = bestK ^ (1u << j);
        compute_answer(K2, cand);
        if (cand.size() > bestSz) {
            bestSz = cand.size();
            bestK = K2;
            bestAns = cand;
        }
    }
    // Random tries to possibly improve count
    int TRIES = 3000;
    for (int t = 0; t < TRIES; ++t) {
        uint32_t K2 = (uint32_t)(rnd() & maskK);
        compute_answer(K2, cand);
        if (cand.size() > bestSz) {
            bestSz = cand.size();
            bestK = K2;
            bestAns = cand;
        }
    }

    // Ensure at least floor(sqrt(n/2))
    uint32_t need = (uint32_t)floor(sqrt((long double)n / 2.0L));
    if (bestSz < need) {
        // As a safety, continue more random tries
        for (int t = 0; t < 20000 && bestSz < need; ++t) {
            uint32_t K2 = (uint32_t)(rnd() & maskK);
            compute_answer(K2, cand);
            if (cand.size() > bestSz) {
                bestSz = cand.size();
                bestK = K2;
                bestAns = cand;
            }
        }
    }

    // Output
    cout << bestAns.size() << "\n";
    for (size_t i = 0; i < bestAns.size(); ++i) {
        if (i) cout << ' ';
        cout << bestAns[i];
    }
    if (!bestAns.empty()) cout << "\n";
    return 0;
}