#include <bits/stdc++.h>
using namespace std;

using u64 = unsigned long long;
using u128 = __uint128_t;

static mt19937_64 rng((u64)chrono::high_resolution_clock::now().time_since_epoch().count());

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
    for (u64 p : {2ULL, 3ULL, 5ULL, 7ULL, 11ULL, 13ULL, 17ULL, 19ULL, 23ULL, 29ULL, 31ULL, 37ULL}) {
        if (n % p == 0) return n == p;
    }
    u64 d = n - 1;
    int s = 0;
    while ((d & 1) == 0) {
        d >>= 1;
        ++s;
    }
    auto witness = [&](u64 a) -> bool {
        if (a % n == 0) return false;
        u64 x = pow_mod(a, d, n);
        if (x == 1 || x == n - 1) return false;
        for (int r = 1; r < s; ++r) {
            x = mul_mod(x, x, n);
            if (x == n - 1) return false;
        }
        return true;
    };
    for (u64 a : {2ULL, 3ULL, 5ULL, 7ULL, 11ULL, 13ULL, 17ULL}) {
        if (a >= n) continue;
        if (witness(a)) return false;
    }
    return true;
}

u64 rho(u64 n) {
    if ((n & 1) == 0) return 2;
    if (n % 3 == 0) return 3;
    uniform_int_distribution<u64> dist(2, n - 2);
    while (true) {
        u64 c = dist(rng);
        u64 x = dist(rng);
        u64 y = x;
        u64 d = 1;
        auto f = [&](u64 v) { return (mul_mod(v, v, n) + c) % n; };
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

void factor(u64 n, vector<u64>& fac) {
    if (n == 1) return;
    if (isPrime(n)) {
        fac.push_back(n);
        return;
    }
    u64 d = rho(n);
    factor(d, fac);
    factor(n / d, fac);
}

static int qcount = 0;

u64 ask(u64 v, u64 x) {
    cout << "? " << v << " " << x << endl;
    cout.flush();
    long long res;
    if (!(cin >> res)) exit(0);
    if (res == -1) exit(0);
    ++qcount;
    return (u64)res;
}

bool eq_cached_base(u64 v, u64 baseRes, u64 baseX, u64 T) {
    u64 r = ask(v, baseX + T);
    return r == baseRes;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    const u64 MAX_X = 5000000000000000000ULL; // 5e18
    for (int tc = 0; tc < n; ++tc) {
        qcount = 0;
        u64 v0 = 1;
        u64 baseX = 1;
        u64 baseRes = ask(v0, baseX);

        unordered_map<u64, u64> seen;
        seen.reserve(4096);
        seen.max_load_factor(0.7f);

        u64 M = 0;
        int collisions = 0;

        // Sampling phase
        int sampleBudget = 2350; // leave room for factorization and answer/ack
        uniform_int_distribution<u64> distX(2, MAX_X - 10);
        unordered_set<u64> usedX;
        usedX.reserve(sampleBudget * 2);
        usedX.insert(baseX);

        while (qcount < sampleBudget) {
            u64 x;
            do {
                x = distX(rng);
            } while (usedX.find(x) != usedX.end());
            usedX.insert(x);

            u64 r = ask(v0, x);
            auto it = seen.find(r);
            if (it == seen.end()) {
                seen.emplace(r, x);
            } else {
                u64 prev = it->second;
                u64 d = (x > prev) ? (x - prev) : (prev - x);
                if (d > 0) {
                    M = std::gcd(M, d);
                    ++collisions;
                }
            }
            if (collisions >= 3 && M > 0) break;
        }

        // If no collision yet, keep trying within budget
        while (qcount < sampleBudget && (M == 0 || collisions < 2)) {
            u64 x;
            do {
                x = distX(rng);
            } while (usedX.find(x) != usedX.end());
            usedX.insert(x);

            u64 r = ask(v0, x);
            auto it = seen.find(r);
            if (it == seen.end()) {
                seen.emplace(r, x);
            } else {
                u64 prev = it->second;
                u64 d = (x > prev) ? (x - prev) : (prev - x);
                if (d > 0) {
                    M = std::gcd(M, d);
                    ++collisions;
                }
            }
        }

        // If still no collision, try a second vertex with remaining budget
        if (M == 0) {
            u64 v1 = 2;
            u64 baseRes2 = ask(v1, baseX);
            (void)baseRes2;
            seen.clear();
            usedX.clear();
            usedX.insert(baseX);

            while (qcount < sampleBudget) {
                u64 x;
                do {
                    x = distX(rng);
                } while (usedX.find(x) != usedX.end());
                usedX.insert(x);

                u64 r = ask(v1, x);
                auto it = seen.find(r);
                if (it == seen.end()) {
                    seen.emplace(r, x);
                } else {
                    u64 prev = it->second;
                    u64 d = (x > prev) ? (x - prev) : (prev - x);
                    if (d > 0) {
                        M = std::gcd(M, d);
                        ++collisions;
                    }
                }
                if (collisions >= 2 && M > 0) break;
            }
        }

        // If still no collision, as a last resort, try structured sampling on v0
        if (M == 0) {
            // Try linear progression with two different steps to force at least one collision probabilistically
            u64 steps[2] = { 999983ULL, 1000003ULL }; // large primes near 1e6
            for (int si = 0; si < 2 && qcount < sampleBudget; ++si) {
                seen.clear();
                for (int i = 0; i < 600 && qcount < sampleBudget; ++i) {
                    u64 x = baseX + steps[si] * (u64)(i + 1);
                    if (x > MAX_X - 5) break;
                    u64 r = ask(v0, x);
                    auto it = seen.find(r);
                    if (it == seen.end()) {
                        seen.emplace(r, x);
                    } else {
                        u64 prev = it->second;
                        u64 d = x > prev ? x - prev : prev - x;
                        if (d > 0) {
                            M = std::gcd(M, d);
                            ++collisions;
                        }
                    }
                }
                if (M > 0) break;
            }
        }

        // If still no collision, fallback guess (shouldn't happen in typical tests)
        if (M == 0) {
            // Best effort: try to deduce s by random m tests and gcd of successful ones
            // But without collisions, we cannot find any multiple-of-s deterministically.
            // We'll default to 3 to avoid impossible state; however judge would likely reject.
            // To minimize chance of wrong answer, attempt more sampling until near budget.
            while (qcount + 2 < 2480 && M == 0) {
                u64 x1 = distX(rng);
                u64 x2 = distX(rng);
                if (x1 == x2) continue;
                u64 r1 = ask(v0, x1);
                u64 r2 = ask(v0, x2);
                if (r1 == r2) {
                    u64 d = x1 > x2 ? x1 - x2 : x2 - x1;
                    M = d;
                    break;
                }
            }
            if (M == 0) M = 3; // fallback minimal cycle length
        }

        // Now refine M to s by dividing its prime factors using equality tests against base
        // Ensure baseX + T <= MAX_X
        if (baseX + M > MAX_X) {
            // choose a different base to fit
            baseX = MAX_X - M;
            baseRes = ask(v0, baseX);
        } else {
            // baseRes already computed for baseX=1 or for v1 earlier - recompute for safety on v0
            baseRes = ask(v0, baseX);
        }

        // Factor M
        vector<u64> fac;
        factor(M, fac);
        sort(fac.begin(), fac.end());
        // Count prime powers
        vector<pair<u64,int>> primes;
        for (size_t i = 0; i < fac.size();) {
            size_t j = i;
            while (j < fac.size() && fac[j] == fac[i]) ++j;
            primes.emplace_back(fac[i], (int)(j - i));
            i = j;
        }

        u64 S = M;
        for (auto &pe : primes) {
            u64 p = pe.first;
            int e = pe.second;
            for (int i = 0; i < e; ++i) {
                if (S % p == 0) {
                    u64 cand = S / p;
                    if (cand == 0) break;
                    if (baseX + cand > MAX_X) {
                        // adjust base
                        u64 newBase = MAX_X - cand;
                        baseRes = ask(v0, newBase);
                        baseX = newBase;
                    }
                    bool ok = eq_cached_base(v0, baseRes, baseX, cand);
                    if (ok) {
                        S = cand;
                        // continue trying same prime
                    } else {
                        break;
                    }
                }
            }
        }

        if (S < 3) S = 3; // constraints guarantee >=3; ensure not to output invalid small value by mistake

        cout << "! " << S << endl;
        cout.flush();
        int verdict;
        if (!(cin >> verdict)) return 0;
        if (verdict == -1) {
            return 0;
        }
    }
    return 0;
}