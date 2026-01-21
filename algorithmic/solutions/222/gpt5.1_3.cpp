#include <bits/stdc++.h>
using namespace std;

using u64 = unsigned long long;
using u128 = __uint128_t;

mt19937_64 rng((u64)chrono::steady_clock::now().time_since_epoch().count());

u64 mul_mod(u64 a, u64 b, u64 mod) {
    return (u128)a * b % mod;
}

u64 pow_mod(u64 a, u64 d, u64 mod) {
    u64 r = 1;
    while (d) {
        if (d & 1) r = mul_mod(r, a, mod);
        a = mul_mod(a, a, mod);
        d >>= 1;
    }
    return r;
}

bool isPrime(u64 n) {
    if (n < 2) return false;
    static const u64 smallPrimes[] = {2,3,5,7,11,13,17,19,23,29,31,37};
    for (u64 p : smallPrimes) {
        if (n == p) return true;
        if (n % p == 0) return n == p;
    }
    u64 d = n - 1, s = 0;
    while ((d & 1) == 0) {
        d >>= 1;
        ++s;
    }
    auto check = [&](u64 a) -> bool {
        if (a % n == 0) return true;
        u64 x = pow_mod(a, d, n);
        if (x == 1 || x == n - 1) return true;
        for (u64 r = 1; r < s; ++r) {
            x = mul_mod(x, x, n);
            if (x == n - 1) return true;
        }
        return false;
    };
    static const u64 testPrimes[] = {
        2ULL, 325ULL, 9375ULL, 28178ULL,
        450775ULL, 9780504ULL, 1795265022ULL
    };
    for (u64 a : testPrimes) {
        if (a % n == 0) continue;
        if (!check(a)) return false;
    }
    return true;
}

u64 pollard_rho(u64 n) {
    if ((n & 1) == 0) return 2;
    while (true) {
        u64 c = uniform_int_distribution<u64>(1, n - 1)(rng);
        u64 x = uniform_int_distribution<u64>(0, n - 1)(rng);
        u64 y = x;
        u64 d = 1;
        auto f = [&](u64 v) {
            return (mul_mod(v, v, n) + c) % n;
        };
        while (d == 1) {
            x = f(x);
            y = f(f(y));
            u64 diff = x > y ? x - y : y - x;
            d = std::gcd(diff, n);
            if (d == n) break;
        }
        if (d > 1 && d < n) return d;
    }
}

void factor(u64 n, vector<u64> &res) {
    if (n == 1) return;
    if (isPrime(n)) {
        res.push_back(n);
        return;
    }
    u64 d = pollard_rho(n);
    factor(d, res);
    factor(n / d, res);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int Q_LIMIT = 2500;
    const int FACTOR_MARGIN = 80; // reserve for factorization phase
    const int SMALL_BOUND = 200;  // scan cycle lengths up to this

    int n;
    if (!(cin >> n)) return 0;

    for (int tc = 0; tc < n; ++tc) {
        int qcnt = 0;

        auto ask = [&](u64 v, u64 x) -> long long {
            if (qcnt >= Q_LIMIT) {
                // Exceeded query limit; terminate gracefully.
                exit(0);
            }
            cout << "? " << v << " " << x << endl;
            cout.flush();
            long long res;
            if (!(cin >> res)) exit(0);
            ++qcnt;
            return res;
        };

        // Get a vertex on the cycle
        long long anchor = ask(1, 1); // exponent 1 from vertex 1
        u64 cycleLen = 0;
        bool done = false;

        // Phase 1: scan small cycle lengths
        for (u64 t = 2; t <= SMALL_BOUND; ++t) {
            long long res = ask((u64)anchor, t);
            if (res == anchor) {
                cycleLen = t;
                done = true;
                break;
            }
        }

        if (!done) {
            // Phase 2: look for collisions to get a multiple of the cycle length
            unordered_map<long long, u64> seen; // vertex -> exponent
            seen.reserve(4096);
            seen.max_load_factor(0.7f);
            seen[anchor] = 0; // treat anchor as exponent 0

            unordered_set<u64> usedX;
            usedX.reserve(4096);
            usedX.max_load_factor(0.7f);

            u64 M = 0;
            const u64 MAX_X = (u64)1e18;

            while (qcnt < Q_LIMIT - FACTOR_MARGIN && M == 0) {
                u64 x;
                do {
                    x = (rng() % MAX_X) + 1;
                } while (usedX.find(x) != usedX.end());
                usedX.insert(x);

                long long v = ask((u64)anchor, x);
                auto it = seen.find(v);
                if (it != seen.end()) {
                    u64 prev = it->second;
                    u64 d = x > prev ? x - prev : prev - x;
                    if (d > 0) {
                        M = d;
                        break;
                    }
                } else {
                    seen[v] = x;
                }
            }

            if (M == 0) {
                // Fallback guess (very unlikely to be used in practice)
                cycleLen = max<u64>(SMALL_BOUND + 1, 3);
            } else {
                // Factor M and reduce to the exact order
                vector<u64> pf;
                factor(M, pf);
                sort(pf.begin(), pf.end());

                u64 order = M;

                // Confirm that M is indeed a multiple of the cycle length (optional)
                // ask((u64)anchor, order);

                for (size_t i = 0; i < pf.size();) {
                    u64 p = pf[i];
                    int cnt = 0;
                    while (i < pf.size() && pf[i] == p) {
                        ++cnt;
                        ++i;
                    }
                    for (int e = 0; e < cnt; ++e) {
                        if (order % p != 0) break;
                        u64 cand = order / p;
                        if (cand == 0) break;
                        long long res = ask((u64)anchor, cand);
                        if (res == anchor) {
                            order = cand;
                        } else {
                            break;
                        }
                    }
                }

                cycleLen = order;
            }
        }

        if (cycleLen < 3) cycleLen = 3; // safety, though shouldn't happen

        cout << "! " << cycleLen << endl;
        cout.flush();

        int verdict;
        if (!(cin >> verdict)) return 0;
        if (verdict == -1) return 0;
    }

    return 0;
}