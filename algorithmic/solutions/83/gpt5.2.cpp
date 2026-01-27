#include <bits/stdc++.h>
using namespace std;

static inline uint64_t splitmix64(uint64_t x) {
    x += 0x9e3779b97f4a7c15ULL;
    x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
    x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
    return x ^ (x >> 31);
}

static inline int powmod_small(int a, int e, int mod) {
    long long r = 1, x = a % mod;
    while (e > 0) {
        if (e & 1) r = (r * x) % mod;
        x = (x * x) % mod;
        e >>= 1;
    }
    return (int)r;
}

enum Type : int {
    LIOUVILLE = 0,
    MOD4 = 1,
    MOD3 = 2,
    LEGENDRE = 3,
    RANDOM = 4
};

struct Candidate {
    Type type;
    uint64_t seed;
    int specialPrime;     // for MOD4: 2, for MOD3: 3, for LEGENDRE: q
    int specialSign;      // sign for specialPrime
};

static inline void appendVal(string &out, int v) {
    if (v == 1) out.push_back('1');
    else { out.push_back('-'); out.push_back('1'); }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    vector<int> spf(n + 1, 0);
    vector<int> primes;
    primes.reserve((int)(n / log(max(2, n)) * 1.1) + 100);
    spf[1] = 1;
    for (int i = 2; i <= n; i++) {
        if (spf[i] == 0) {
            spf[i] = i;
            primes.push_back(i);
        }
        for (int p : primes) {
            long long v = 1LL * i * p;
            if (v > n) break;
            spf[(int)v] = p;
            if (p == spf[i]) break;
        }
    }

    // Precompute Legendre tables for some small primes q.
    auto build_legendre_tab = [&](int q) {
        vector<int8_t> tab(q, 1);
        int e = (q - 1) / 2;
        for (int r = 1; r < q; r++) {
            int t = powmod_small(r, e, q);
            tab[r] = (t == 1) ? 1 : -1;
        }
        tab[0] = 1; // will be overridden by special handling when p==q
        return tab;
    };

    const int qs[] = {5, 7, 11};
    unordered_map<int, vector<int8_t>> legTab;
    legTab.reserve(8);
    for (int q : qs) legTab.emplace(q, build_legendre_tab(q));

    vector<int8_t> primeSign(n + 1, 1);
    vector<int8_t> cur(n + 1, 1);

    auto fill_prime_signs = [&](const Candidate &cand) {
        if (cand.type == LIOUVILLE) {
            for (int p : primes) primeSign[p] = -1;
        } else if (cand.type == MOD4) {
            for (int p : primes) {
                if (p == 2) primeSign[p] = (int8_t)cand.specialSign;
                else primeSign[p] = (p % 4 == 1) ? (int8_t)1 : (int8_t)-1;
            }
        } else if (cand.type == MOD3) {
            for (int p : primes) {
                if (p == 3) primeSign[p] = (int8_t)cand.specialSign;
                else primeSign[p] = (p % 3 == 1) ? (int8_t)1 : (int8_t)-1;
            }
        } else if (cand.type == LEGENDRE) {
            int q = cand.specialPrime;
            auto it = legTab.find(q);
            const vector<int8_t> &tab = it->second;
            for (int p : primes) {
                if (p == q) primeSign[p] = (int8_t)cand.specialSign;
                else primeSign[p] = tab[p % q];
            }
        } else { // RANDOM
            uint64_t seed = cand.seed;
            for (int p : primes) {
                uint64_t h = splitmix64(seed ^ (uint64_t)p);
                primeSign[p] = (h & 1ULL) ? (int8_t)1 : (int8_t)-1;
            }
        }
        primeSign[1] = 1;
    };

    auto evaluate = [&](const Candidate &cand, int bestMx) -> int {
        fill_prime_signs(cand);

        cur[1] = 1;
        int s = 1;
        int mx = 1;
        if (mx >= bestMx) return mx;

        for (int i = 2; i <= n; i++) {
            int p = spf[i];
            cur[i] = (int8_t)(cur[i / p] * primeSign[p]);
            s += (int)cur[i];
            int a = s >= 0 ? s : -s;
            if (a > mx) {
                mx = a;
                if (mx >= bestMx) return mx;
            }
        }
        return mx;
    };

    vector<Candidate> candidates;
    candidates.push_back({LIOUVILLE, 0, 0, 0});
    candidates.push_back({MOD4, 0, 2, 1});
    candidates.push_back({MOD4, 0, 2, -1});
    candidates.push_back({MOD3, 0, 3, 1});
    candidates.push_back({MOD3, 0, 3, -1});
    candidates.push_back({LEGENDRE, 0, 5, 1});
    candidates.push_back({LEGENDRE, 0, 7, 1});
    candidates.push_back({LEGENDRE, 0, 11, 1});

    const uint64_t seeds[] = {
        0x123456789abcdef0ULL,
        0xfedcba9876543210ULL,
        0x0f0e0d0c0b0a0908ULL,
        0x3141592653589793ULL,
        0x2718281828459045ULL,
        0x9e3779b97f4a7c15ULL,
        0xdeadbeefcafebabeULL,
        0xabcdef0123456789ULL,
        0x6a09e667f3bcc909ULL,
        0xbb67ae8584caa73bULL,
        0x3c6ef372fe94f82bULL,
        0xa54ff53a5f1d36f1ULL
    };
    for (uint64_t sd : seeds) candidates.push_back({RANDOM, sd, 0, 0});

    int bestMx = INT_MAX;
    Candidate bestCand = candidates[0];
    for (const auto &cand : candidates) {
        int mx = evaluate(cand, bestMx);
        if (mx < bestMx) {
            bestMx = mx;
            bestCand = cand;
        }
    }

    // Build final sequence for output.
    fill_prime_signs(bestCand);
    cur[1] = 1;
    for (int i = 2; i <= n; i++) {
        int p = spf[i];
        cur[i] = (int8_t)(cur[i / p] * primeSign[p]);
    }

    string out;
    out.reserve((size_t)n * 4 + 8);
    for (int i = 1; i <= n; i++) {
        appendVal(out, (int)cur[i]);
        out.push_back(i == n ? '\n' : ' ');
    }
    cout.write(out.data(), (streamsize)out.size());
    return 0;
}