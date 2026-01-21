#include <bits/stdc++.h>
using namespace std;

using ull = unsigned long long;
using u128 = __uint128_t;
using i64 = long long;

static const ull LIM = 1000000000000000000ULL;

struct SplitMix64 {
    ull x;
    explicit SplitMix64(ull seed = 0) : x(seed) {}
    ull next() {
        ull z = (x += 0x9e3779b97f4a7c15ULL);
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
        return z ^ (z >> 31);
    }
};

static inline ull mul_mod(ull a, ull b, ull mod) {
    return (ull)((u128)a * b % mod);
}
static inline ull pow_mod(ull a, ull d, ull mod) {
    ull r = 1;
    while (d) {
        if (d & 1) r = mul_mod(r, a, mod);
        a = mul_mod(a, a, mod);
        d >>= 1;
    }
    return r;
}

static bool isPrime64(ull n) {
    if (n < 2) return false;
    static ull smallPrimes[] = {2ULL,3ULL,5ULL,7ULL,11ULL,13ULL,17ULL,19ULL,23ULL,29ULL,31ULL,37ULL};
    for (ull p : smallPrimes) {
        if (n == p) return true;
        if (n % p == 0) return n == p;
    }
    ull d = n - 1, s = 0;
    while ((d & 1) == 0) { d >>= 1; ++s; }
    auto witness = [&](ull a) -> bool {
        if (a % n == 0) return false;
        ull x = pow_mod(a % n, d, n);
        if (x == 1 || x == n - 1) return false;
        for (ull i = 1; i < s; i++) {
            x = mul_mod(x, x, n);
            if (x == n - 1) return false;
        }
        return true;
    };
    static ull bases[] = {2ULL, 325ULL, 9375ULL, 28178ULL, 450775ULL, 9780504ULL, 1795265022ULL};
    for (ull a : bases) if (witness(a)) return false;
    return true;
}

static ull pollard_rho(ull n, SplitMix64 &rng) {
    if ((n & 1ULL) == 0) return 2;
    if (n % 3ULL == 0) return 3;

    ull c = rng.next() % (n - 1) + 1;
    ull x = rng.next() % (n - 2) + 2;
    ull y = x;
    ull d = 1;

    auto f = [&](ull v) -> ull {
        return (mul_mod(v, v, n) + c) % n;
    };

    while (d == 1) {
        x = f(x);
        y = f(f(y));
        ull diff = x > y ? x - y : y - x;
        d = std::gcd(diff, n);
    }
    if (d == n) return pollard_rho(n, rng);
    return d;
}

static void factor_rec(ull n, map<ull,int> &fac, SplitMix64 &rng) {
    if (n == 1) return;
    if (isPrime64(n)) {
        fac[n]++;
        return;
    }
    ull d = pollard_rho(n, rng);
    factor_rec(d, fac, rng);
    factor_rec(n / d, fac, rng);
}

static ull pow_ull(ull a, int e) {
    u128 r = 1, b = a;
    while (e) {
        if (e & 1) r *= b;
        b *= b;
        e >>= 1;
    }
    return (ull)r;
}

static i64 ask(const vector<ull> &v) {
    cout << "0 " << v.size();
    for (ull x : v) cout << ' ' << x;
    cout << '\n';
    cout.flush();
    i64 res;
    if (!(cin >> res)) exit(0);
    if (res < 0) exit(0);
    return res;
}

static bool divides_n(ull x) {
    // query [1, 1+x], collision iff n | x
    vector<ull> v;
    v.reserve(2);
    v.push_back(1);
    v.push_back(1 + x);
    i64 res = ask(v);
    return res == 1;
}

static pair<ull,ull> cross_pair(vector<ull> A, vector<ull> B) {
    // A and B individually collision-free, but there is at least one collision across them.
    // Find a in A:
    while (A.size() > 1) {
        size_t mid = A.size() / 2;
        vector<ull> L(A.begin(), A.begin() + mid);
        vector<ull> Q;
        Q.reserve(L.size() + B.size());
        Q.insert(Q.end(), L.begin(), L.end());
        Q.insert(Q.end(), B.begin(), B.end());
        i64 c = ask(Q);
        if (c > 0) {
            A.swap(L);
        } else {
            vector<ull> R(A.begin() + mid, A.end());
            A.swap(R);
        }
    }
    ull a = A[0];

    // Find b in B:
    while (B.size() > 1) {
        size_t mid = B.size() / 2;
        vector<ull> L(B.begin(), B.begin() + mid);
        vector<ull> Q;
        Q.reserve(1 + L.size());
        Q.push_back(a);
        Q.insert(Q.end(), L.begin(), L.end());
        i64 c = ask(Q);
        if (c > 0) {
            B.swap(L);
        } else {
            vector<ull> R(B.begin() + mid, B.end());
            B.swap(R);
        }
    }
    ull b = B[0];
    return {a, b};
}

static pair<ull,ull> find_colliding_pair(vector<ull> v, i64 totalCollisions, SplitMix64 &rng) {
    (void)totalCollisions;
    const size_t CROSS_THRESHOLD = 4096;

    while (true) {
        if (v.size() == 2) return {v[0], v[1]};
        if (v.size() < 2) exit(0);

        if (v.size() <= CROSS_THRESHOLD) {
            // Deterministic shrink; handle cross directly.
            while (v.size() > 2) {
                size_t mid = v.size() / 2;
                vector<ull> A(v.begin(), v.begin() + mid);
                vector<ull> B(v.begin() + mid, v.end());
                i64 cA = ask(A);
                if (cA > 0) { v.swap(A); continue; }
                i64 cB = ask(B);
                if (cB > 0) { v.swap(B); continue; }
                return cross_pair(std::move(A), std::move(B));
            }
            return {v[0], v[1]};
        }

        // For larger sets: randomize to avoid expensive cross-resolution; cross will be rare when collisions are plenty.
        for (int attempt = 0; attempt < 50; attempt++) {
            shuffle(v.begin(), v.end(), std::mt19937_64(rng.next()));
            size_t mid = v.size() / 2;
            vector<ull> A(v.begin(), v.begin() + mid);
            vector<ull> B(v.begin() + mid, v.end());

            i64 cA = ask(A);
            if (cA > 0) { v.swap(A); goto next_iter; }

            i64 cB = ask(B);
            if (cB > 0) { v.swap(B); goto next_iter; }

            // Cross-only; try another shuffle. When v is big and collisions sparse, this could loop,
            // but in practice with our initial size it quickly reduces.
        }
        // If extremely unlucky, fall back to threshold by forcibly reducing size via repeated shuffles until size small.
        // We do a controlled reduction: keep sampling subsets until one has internal collision.
        while (v.size() > CROSS_THRESHOLD) {
            shuffle(v.begin(), v.end(), std::mt19937_64(rng.next()));
            size_t mid = v.size() / 2;
            vector<ull> A(v.begin(), v.begin() + mid);
            i64 cA = ask(A);
            if (cA > 0) { v.swap(A); break; }
            vector<ull> B(v.begin() + mid, v.end());
            i64 cB = ask(B);
            if (cB > 0) { v.swap(B); break; }
        }
    next_iter:
        continue;
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    ull seed = (ull)chrono::high_resolution_clock::now().time_since_epoch().count();
    SplitMix64 rng(seed);

    const int M = 200000;
    vector<ull> S;
    S.reserve(M);

    struct ULLHash {
        size_t operator()(ull x) const noexcept {
            x += 0x9e3779b97f4a7c15ULL;
            x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
            x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
            x = x ^ (x >> 31);
            return (size_t)x;
        }
    };

    unordered_set<ull, ULLHash> used;
    used.reserve((size_t)M * 2);
    used.max_load_factor(0.7f);

    auto gen_set = [&]() {
        S.clear();
        used.clear();
        used.reserve((size_t)M * 2);
        used.max_load_factor(0.7f);
        while ((int)S.size() < M) {
            ull x = (rng.next() % LIM) + 1;
            if (used.insert(x).second) S.push_back(x);
        }
    };

    i64 c = 0;
    for (int tries = 0; tries < 5; tries++) {
        gen_set();
        c = ask(S);
        if (c > 0) break;
    }
    if (c <= 0) {
        // Extremely unlikely; guess minimal.
        cout << "1 2\n";
        cout.flush();
        return 0;
    }

    auto pr = find_colliding_pair(S, c, rng);
    ull a = pr.first, b = pr.second;
    ull D = (a > b) ? (a - b) : (b - a);
    if (D == 0) {
        cout << "1 2\n";
        cout.flush();
        return 0;
    }

    map<ull,int> fac;
    factor_rec(D, fac, rng);

    ull n = 1;
    for (auto [p, e] : fac) {
        vector<ull> pows(e + 1);
        pows[0] = 1;
        for (int i = 1; i <= e; i++) pows[i] = mul_mod(pows[i - 1], p, ULLONG_MAX); // not mod, but safe for small e?
        // The above is incorrect for true multiplication without mod; recompute safely:
        pows[0] = 1;
        for (int i = 1; i <= e; i++) pows[i] = (ull)((u128)pows[i - 1] * p);

        int lo = 0, hi = e; // removable exponent
        while (lo < hi) {
            int mid = (lo + hi + 1) / 2;
            ull x = D / pows[mid];
            if (divides_n(x)) lo = mid;
            else hi = mid - 1;
        }
        int removable = lo;
        int need = e - removable;
        if (need > 0) {
            ull mult = pow_ull(p, need);
            n = (ull)((u128)n * mult);
        }
    }

    // Final output
    cout << "1 " << n << '\n';
    cout.flush();
    return 0;
}