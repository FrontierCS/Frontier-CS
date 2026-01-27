#include <bits/stdc++.h>
using namespace std;

using u64 = unsigned long long;
using u128 = __uint128_t;

static u64 rng_state;

static inline u64 splitmix64() {
    u64 z = (rng_state += 0x9e3779b97f4a7c15ULL);
    z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
    z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
    return z ^ (z >> 31);
}

static inline u64 mod_mul(u64 a, u64 b, u64 mod) {
    return (u128)a * b % mod;
}

static inline u64 mod_pow(u64 a, u64 d, u64 mod) {
    u64 r = 1;
    while (d) {
        if (d & 1) r = mod_mul(r, a, mod);
        a = mod_mul(a, a, mod);
        d >>= 1;
    }
    return r;
}

static inline bool isPrime(u64 n) {
    if (n < 2) return false;
    static u64 smallPrimes[] = {2ULL,3ULL,5ULL,7ULL,11ULL,13ULL,17ULL,19ULL,23ULL,29ULL,31ULL,37ULL};
    for (u64 p : smallPrimes) {
        if (n == p) return true;
        if (n % p == 0) return false;
    }
    u64 d = n - 1, s = 0;
    while ((d & 1) == 0) { d >>= 1; ++s; }

    auto witness = [&](u64 a) -> bool {
        if (a % n == 0) return false;
        u64 x = mod_pow(a, d, n);
        if (x == 1 || x == n - 1) return false;
        for (u64 i = 1; i < s; i++) {
            x = mod_mul(x, x, n);
            if (x == n - 1) return false;
        }
        return true;
    };

    // Deterministic for 64-bit
    static u64 bases[] = {2ULL, 325ULL, 9375ULL, 28178ULL, 450775ULL, 9780504ULL, 1795265022ULL};
    for (u64 a : bases) {
        if (witness(a)) return false;
    }
    return true;
}

static inline u64 gcd_u64(u64 a, u64 b) {
    while (b) {
        u64 t = a % b;
        a = b;
        b = t;
    }
    return a;
}

static u64 pollard_rho(u64 n) {
    if ((n & 1ULL) == 0) return 2;
    if (n % 3ULL == 0) return 3;
    u64 c = splitmix64() % (n - 2) + 1;
    u64 x = splitmix64() % (n - 2) + 2;
    u64 y = x;
    u64 d = 1;

    auto f = [&](u64 v) -> u64 {
        return (mod_mul(v, v, n) + c) % n;
    };

    while (d == 1) {
        x = f(x);
        y = f(f(y));
        u64 diff = x > y ? x - y : y - x;
        d = gcd_u64(diff, n);
    }
    if (d == n) return pollard_rho(n);
    return d;
}

static void factor_rec(u64 n, vector<u64>& fac) {
    if (n == 1) return;
    if (isPrime(n)) {
        fac.push_back(n);
        return;
    }
    u64 d = pollard_rho(n);
    factor_rec(d, fac);
    factor_rec(n / d, fac);
}

struct Interactor {
    int ask(int v, u64 x) {
        cout << "? " << v << " " << x << "\n" << flush;
        int ans;
        if (!(cin >> ans)) exit(0);
        if (ans == -1) exit(0);
        return ans;
    }
    void answer(u64 s) {
        cout << "! " << s << "\n" << flush;
    }
};

static u64 find_d(Interactor& it, int a, int b) {
    const int m = 1024;

    unordered_map<int, int> mp;
    mp.reserve(m * 2 + 10);
    mp.max_load_factor(0.7f);

    mp.emplace(b, 0);
    for (int i = 1; i < m; i++) {
        int v = it.ask(b, (u64)i);
        mp.try_emplace(v, i); // keep smallest i for each vertex
    }

    for (int j = 0; j <= m; j++) {
        u64 exp = (u64)j * (u64)m;
        int w = (j == 0) ? a : it.ask(a, exp);
        auto itf = mp.find(w);
        if (itf == mp.end()) continue;
        int i = itf->second;
        if (exp < (u64)i) continue;
        u64 d = exp - (u64)i;
        if (d == 0) {
            if (a == b) return 0;
            continue;
        }
        // Usually guaranteed; keep one verification for safety.
        int chk = it.ask(a, d);
        if (chk == b) return d;
    }

    // Fallback (should never happen): brute verify among candidates without extra queries is not possible.
    return 0;
}

static u64 deduce_cycle_length(Interactor& it, int c0, u64 M) {
    vector<u64> fac;
    factor_rec(M, fac);
    sort(fac.begin(), fac.end());

    vector<u64> primes;
    primes.reserve(fac.size());
    for (u64 p : fac) {
        if (primes.empty() || primes.back() != p) primes.push_back(p);
    }

    u64 cand = M;
    for (u64 p : primes) {
        while (cand % p == 0) {
            u64 k = cand / p;
            if (k == 0) break;
            int res = it.ask(c0, k);
            if (res == c0) cand = k;
            else break;
        }
    }
    return cand;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    rng_state = (u64)chrono::high_resolution_clock::now().time_since_epoch().count();

    int n;
    if (!(cin >> n)) return 0;

    Interactor it;

    const u64 L = 5000000000000000000ULL - 1234567ULL; // <= 5e18

    for (int tc = 0; tc < n; tc++) {
        int c0 = it.ask(1, 1);
        int b = it.ask(c0, L);

        u64 d = find_d(it, c0, b);
        u64 M = L - d;

        u64 s = deduce_cycle_length(it, c0, M);
        it.answer(s);

        int verdict;
        if (!(cin >> verdict)) return 0;
        if (verdict == -1) return 0;
    }
    return 0;
}