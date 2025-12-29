#include <bits/stdc++.h>
using namespace std;

static inline int degPoly(uint32_t a) {
    if (!a) return -1;
    return 31 - __builtin_clz(a);
}

static uint32_t polyMod(uint32_t a, uint32_t mod) {
    int db = degPoly(mod);
    while (a) {
        int da = degPoly(a);
        if (da < db) break;
        a ^= (mod << (da - db));
    }
    return a;
}

static uint32_t polyGCD(uint32_t a, uint32_t b) {
    while (b) {
        uint32_t r = polyMod(a, b);
        a = b;
        b = r;
    }
    return a;
}

struct GF2m {
    int m;
    uint32_t irr;  // modulus polynomial without x^m term (lower m bits)
    uint32_t mask;

    uint32_t mul(uint32_t a, uint32_t b) const {
        uint32_t res = 0;
        for (int i = 0; i < m; i++) {
            if (b & 1u) res ^= a;
            b >>= 1;
            uint32_t carry = a & (1u << (m - 1));
            a = (a << 1) & mask;
            if (carry) a ^= irr;
        }
        return res;
    }

    uint32_t cube(uint32_t x) const {
        uint32_t x2 = mul(x, x);
        return mul(x2, x);
    }
};

static vector<int> primeFactors(int x) {
    vector<int> pf;
    for (int p = 2; p * p <= x; p++) {
        if (x % p == 0) {
            pf.push_back(p);
            while (x % p == 0) x /= p;
        }
    }
    if (x > 1) pf.push_back(x);
    return pf;
}

static bool isIrreduciblePoly(uint32_t poly, int m) {
    // poly is monic degree m (bit m set), constant term should be 1 for field
    if (((poly >> m) & 1u) == 0u) return false;
    if ((poly & 1u) == 0u) return false;

    uint32_t mask = (m == 32) ? 0xFFFFFFFFu : ((1u << m) - 1u);
    uint32_t irr = poly & mask;
    GF2m gf{m, irr, mask};

    const uint32_t x = 2u; // polynomial 'x' in residue representation

    // Check x^{2^m} == x mod poly
    uint32_t p = x;
    for (int i = 0; i < m; i++) p = gf.mul(p, p);
    if (p != x) return false;

    // For each prime divisor q of m: gcd(x^{2^{m/q}} - x, poly) == 1
    vector<int> pf = primeFactors(m);
    for (int q : pf) {
        int e = m / q;
        uint32_t t = x;
        for (int i = 0; i < e; i++) t = gf.mul(t, t);
        uint32_t g = polyGCD(t ^ x, poly);
        if (g != 1u) return false;
    }
    return true;
}

static uint32_t findIrreduciblePoly(int m) {
    // Search monic polynomials of degree m with constant term 1
    uint32_t start = (1u << m) | 1u;
    uint32_t end = (1u << (m + 1));
    for (uint32_t poly = start; poly < end; poly += 2u) {
        if (isIrreduciblePoly(poly, m)) return poly;
    }
    // Fallback (should not happen for small m)
    return 0;
}

static long long isqrtll(long long x) {
    long long r = (long long) floor(sqrt((long double)x));
    while ((r + 1) > 0 && (r + 1) * (r + 1) <= x) ++r;
    while (r * r > x) --r;
    return r;
}

static vector<int> buildGreedyOrder(int n, const vector<int>& order) {
    int bits = 0;
    while ((1u << bits) <= (unsigned)n) ++bits;
    if (bits == 0) bits = 1;
    int maxX = 1u << bits;
    vector<uint8_t> used(maxX, 0);

    vector<int> S;
    S.reserve(256);

    for (int x : order) {
        bool ok = true;
        for (int a : S) {
            int d = a ^ x;
            if (used[d]) { ok = false; break; }
        }
        if (!ok) continue;
        for (int a : S) used[a ^ x] = 1;
        S.push_back(x);
    }
    return S;
}

static vector<int> buildGreedy(int n) {
    vector<int> best;

    vector<int> ord1(n);
    iota(ord1.begin(), ord1.end(), 1);
    best = buildGreedyOrder(n, ord1);

    vector<int> ord2 = ord1;
    reverse(ord2.begin(), ord2.end());
    auto tmp = buildGreedyOrder(n, ord2);
    if (tmp.size() > best.size()) best.swap(tmp);

    vector<int> ord3 = ord1;
    stable_sort(ord3.begin(), ord3.end(), [](int a, int b) {
        int pa = __builtin_popcount((unsigned)a);
        int pb = __builtin_popcount((unsigned)b);
        if (pa != pb) return pa < pb;
        return a < b;
    });
    tmp = buildGreedyOrder(n, ord3);
    if (tmp.size() > best.size()) best.swap(tmp);

    // A few randomized attempts
    std::mt19937 rng(712367u + (unsigned)n);
    vector<int> ordR = ord1;
    for (int it = 0; it < 5; it++) {
        shuffle(ordR.begin(), ordR.end(), rng);
        tmp = buildGreedyOrder(n, ordR);
        if (tmp.size() > best.size()) best.swap(tmp);
    }

    return best;
}

static vector<int> buildAPN(int n) {
    if (n <= 0) return {};

    long long limitX = isqrtll(2LL * n) + 2;
    int maxM = 0;
    while ((1LL << (maxM + 1)) <= limitX && maxM < 20) ++maxM;
    maxM = max(maxM, 1);

    unordered_map<int, uint32_t> polyCache;
    vector<int> best;

    for (int m = 1; m <= maxM; m++) {
        uint32_t poly;
        auto it = polyCache.find(m);
        if (it != polyCache.end()) poly = it->second;
        else {
            poly = findIrreduciblePoly(m);
            if (!poly) continue;
            polyCache[m] = poly;
        }

        uint32_t mask = (1u << m) - 1u;
        uint32_t irr = poly & mask;
        GF2m gf{m, irr, mask};

        int N = 1 << m;
        vector<uint32_t> cube(N);
        for (int x = 0; x < N; x++) cube[x] = gf.cube((uint32_t)x);

        uint32_t mask2 = (uint32_t)((1ULL << (2 * m)) - 1ULL);

        vector<uint32_t> base1(N), base2(N);
        for (int x = 0; x < N; x++) {
            uint32_t y = cube[x];
            base1[x] = ((uint32_t)x << m) | y;
            base2[x] = (y << m) | (uint32_t)x;
        }

        vector<uint32_t> trans;
        trans.reserve(16);
        auto addT = [&](uint32_t t) {
            t &= mask2;
            for (uint32_t u : trans) if (u == t) return;
            trans.push_back(t);
        };

        addT(0);
        addT(1);
        addT(mask2);
        addT(mask2 >> 1);
        addT((uint32_t)n);
        addT((uint32_t)(n >> 1));
        addT(((uint32_t)n) ^ mask2);

        uint32_t seed = (uint32_t)(n * 2654435761u) ^ (uint32_t)(m * 2246822519u);
        for (int i = 0; i < 8; i++) {
            seed = seed * 1664525u + 1013904223u;
            addT(seed);
        }

        auto eval = [&](const vector<uint32_t>& base) {
            for (uint32_t t : trans) {
                vector<int> cur;
                cur.reserve(N);
                for (uint32_t v : base) {
                    uint32_t u = (v ^ t);
                    if (u >= 1u && u <= (uint32_t)n) cur.push_back((int)u);
                }
                if (cur.size() > best.size()) best.swap(cur);
            }
        };

        eval(base1);
        eval(base2);
    }

    if (best.empty()) best.push_back(1);
    return best;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;

    vector<int> best = buildAPN(n);

    if (n <= 5000) {
        vector<int> g = buildGreedy(n);
        if (g.size() > best.size()) best.swap(g);
    }

    cout << best.size() << "\n";
    for (size_t i = 0; i < best.size(); i++) {
        if (i) cout << ' ';
        cout << best[i];
    }
    cout << "\n";
    return 0;
}