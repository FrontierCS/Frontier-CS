#include <bits/stdc++.h>
using namespace std;

using ll = long long;
using ull = unsigned long long;
using u128 = __uint128_t;

ull mul_mod(ull a, ull b, ull mod) {
    return (u128)a * b % mod;
}

ull pow_mod(ull a, ull d, ull mod) {
    ull r = 1;
    while (d) {
        if (d & 1) r = mul_mod(r, a, mod);
        a = mul_mod(a, a, mod);
        d >>= 1;
    }
    return r;
}

bool isPrime(ull n) {
    if (n < 2) return false;
    for (ull p : {2ull, 3ull, 5ull, 7ull, 11ull, 13ull, 17ull, 19ull, 23ull, 29ull, 31ull, 37ull}) {
        if (n % p == 0) return n == p;
    }
    ull d = n - 1;
    int s = 0;
    while ((d & 1) == 0) {
        d >>= 1;
        ++s;
    }
    // Deterministic bases for 64-bit
    for (ull a : {2ull, 325ull, 9375ull, 28178ull, 450775ull, 9780504ull, 1795265022ull}) {
        if (a % n == 0) continue;
        ull x = pow_mod(a % n, d, n);
        if (x == 1 || x == n - 1) continue;
        bool comp = true;
        for (int r = 1; r < s; ++r) {
            x = mul_mod(x, x, n);
            if (x == n - 1) {
                comp = false;
                break;
            }
        }
        if (comp) return false;
    }
    return true;
}

mt19937_64 rng((unsigned)chrono::steady_clock::now().time_since_epoch().count());

ull pollard(ull n) {
    if (n % 2 == 0) return 2;
    if (n % 3 == 0) return 3;
    ull c = uniform_int_distribution<ull>(1, n - 1)(rng);
    ull x = uniform_int_distribution<ull>(2, n - 2)(rng);
    ull y = x;
    ull d = 1;
    auto f = [&](ull x) { return (mul_mod(x, x, n) + c) % n; };
    while (d == 1) {
        x = f(x);
        y = f(f(y));
        ull diff = x > y ? x - y : y - x;
        d = std::gcd(diff, n);
        if (d == n) return pollard(n);
    }
    return d;
}

void factor_rec(ull n, map<ull,int> &fac) {
    if (n == 1) return;
    if (isPrime(n)) {
        fac[n]++;
        return;
    }
    ull d = pollard(n);
    factor_rec(d, fac);
    factor_rec(n / d, fac);
}

ll refine_period(ll c, ull diff, int &queriesUsed, int maxQueries) {
    ull g = diff;
    map<ull,int> fac;
    factor_rec(g, fac);
    vector<ull> primes;
    primes.reserve(fac.size());
    for (auto &kv : fac) primes.push_back(kv.first);
    sort(primes.begin(), primes.end());
    for (ull p : primes) {
        while (g % p == 0) {
            ull cand = g / p;
            if (cand == 0) break;
            if (queriesUsed >= maxQueries) break;
            cout << "? " << c << " " << cand << '\n';
            cout.flush();
            ll res;
            if (!(cin >> res)) exit(0);
            ++queriesUsed;
            if (res == c) {
                g = cand;
            } else {
                break;
            }
        }
    }
    return (ll)g;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;

    const int MAX_TOTAL_QUERIES = 2500;

    for (int tc = 0; tc < T; ++tc) {
        int queriesUsed = 0;

        // Get a cycle vertex: next(1)
        cout << "? " << 1 << " " << 1 << '\n';
        cout.flush();
        ll c;
        if (!(cin >> c)) return 0;
        ++queriesUsed;

        unordered_map<ll, ull> first;
        first.reserve(4096);
        first.max_load_factor(0.7f);
        first[c] = 0; // exponent 0 gives vertex c

        ull diff = 0;

        const ull MAXX = 1000000000000ULL; // 1e12
        uniform_int_distribution<ull> dist(1, MAXX);

        int maxSamplingQueries = MAX_TOTAL_QUERIES - 100; // leave some for refinement

        while (queriesUsed < maxSamplingQueries && diff == 0) {
            ull x = dist(rng);
            cout << "? " << c << " " << x << '\n';
            cout.flush();
            ll y;
            if (!(cin >> y)) return 0;
            ++queriesUsed;
            auto it = first.find(y);
            if (it == first.end()) {
                first[y] = x;
            } else {
                ull d = x > it->second ? x - it->second : it->second - x;
                if (d != 0) {
                    diff = d;
                    break;
                }
            }
        }

        ll s;

        if (diff == 0) {
            // Fallback guess (no collision found)
            s = 3;
        } else {
            s = refine_period(c, diff, queriesUsed, MAX_TOTAL_QUERIES);
            if (s < 3) s = 3;
            if (s > 1000000) s = 1000000;
        }

        cout << "! " << s << '\n';
        cout.flush();
        int verdict;
        if (!(cin >> verdict)) return 0;
        if (verdict == -1) return 0;
    }
    return 0;
}