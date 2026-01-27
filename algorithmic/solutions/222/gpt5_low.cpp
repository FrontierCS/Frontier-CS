#include <bits/stdc++.h>
using namespace std;

using u64 = uint64_t;
using u128 = __uint128_t;

static inline u64 rnd64() {
    static std::mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());
    return rng();
}

u64 mod_mul(u64 a, u64 b, u64 mod) {
    return (u128)a * b % mod;
}

u64 mod_pow(u64 a, u64 d, u64 mod) {
    u64 r = 1;
    while (d) {
        if (d & 1) r = mod_mul(r, a, mod);
        a = mod_mul(a, a, mod);
        d >>= 1;
    }
    return r;
}

bool isPrime(u64 n) {
    if (n < 2) return false;
    static u64 testPrimes[] = {2,3,5,7,11,13,17,19,23,29,31,37};
    for (u64 p : testPrimes) {
        if (n % p == 0) return n == p;
    }
    u64 d = n - 1, s = 0;
    while ((d & 1) == 0) { d >>= 1; ++s; }
    auto trial = [&](u64 a)->bool{
        if (a % n == 0) return true;
        u64 x = mod_pow(a, d, n);
        if (x == 1 || x == n - 1) return true;
        for (u64 r = 1; r < s; ++r) {
            x = mod_mul(x, x, n);
            if (x == n - 1) return true;
        }
        return false;
    };
    // Deterministic bases for 64-bit
    u64 bases[] = {2ULL, 3ULL, 5ULL, 7ULL, 11ULL, 13ULL};
    for (u64 a : bases) {
        if (!trial(a)) return false;
    }
    return true;
}

u64 rho(u64 n) {
    if ((n & 1ULL) == 0) return 2;
    if (n % 3ULL == 0) return 3;
    u64 c = rnd64() % (n - 1) + 1;
    u64 x = rnd64() % (n - 2) + 2;
    u64 y = x;
    u64 d = 1;
    auto f = [&](u64 x){ return (mod_mul(x, x, n) + c) % n; };
    while (d == 1) {
        x = f(x);
        y = f(f(y));
        u64 diff = x > y ? x - y : y - x;
        d = std::gcd(diff, n);
        if (d == n) return rho(n);
    }
    return d;
}

void factor(u64 n, map<u64,int> &res) {
    if (n == 1) return;
    if (isPrime(n)) {
        res[n]++;
        return;
    }
    u64 d = rho(n);
    factor(d, res);
    factor(n / d, res);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    if (!(cin >> n)) return 0;
    for (int casei = 0; casei < n; ++casei) {
        auto ask = [&](u64 v, u64 x)->long long {
            cout << "? " << v << " " << x << endl;
            cout.flush();
            long long ret;
            if (!(cin >> ret)) exit(0);
            if (ret == -1) exit(0);
            return ret;
        };
        auto check_divides = [&](u64 m, long long baseVal)->bool {
            long long val = ask(1, 1 + m);
            return val == baseVal;
        };

        // Get base value at t=1
        long long baseVal = ask(1, 1);

        // Sampling to find one multiple M of s via collision
        unordered_map<long long, u64> seen;
        seen.reserve(4096);
        seen.max_load_factor(0.7f);
        u64 M = 0;

        // Try seeding seen with base sample to reduce trivial collision
        seen[baseVal] = 1;

        int max_samples = 2300; // leave budget for factoring and reductions
        for (int i = 0; i < max_samples && M == 0; ++i) {
            u64 t = (rnd64() % (5000000000000000000ULL)) + 1ULL; // [1,5e18]
            long long val = ask(1, t);
            auto it = seen.find(val);
            if (it != seen.end()) {
                u64 t0 = it->second;
                M = (t > t0) ? (t - t0) : (t0 - t);
                if (M == 0) {
                    // extremely unlikely; skip
                    continue;
                }
            } else {
                seen.emplace(val, t);
            }
        }

        if (M == 0) {
            // Fallback: try structured block sampling to force at least one collision
            // Use two blocks of size B to get expected ~B^2/s collisions
            const int B = 400;
            vector<pair<long long, u64>> block1, block2;
            block1.reserve(B);
            block2.reserve(B);
            u64 baseA = rnd64();
            u64 baseB = rnd64();
            for (int i = 0; i < B && M == 0; ++i) {
                u64 t = (baseA + i * 1000003ULL) % (5000000000000000000ULL - 1ULL) + 1ULL;
                long long val = ask(1, t);
                block1.emplace_back(val, t);
            }
            for (int i = 0; i < B && M == 0; ++i) {
                u64 t = (baseB + i * 1000033ULL) % (5000000000000000000ULL - 1ULL) + 1ULL;
                long long val = ask(1, t);
                block2.emplace_back(val, t);
            }
            unordered_map<long long, u64> mp;
            mp.reserve(B * 2);
            for (auto &p : block1) mp[p.first] = p.second;
            for (auto &p : block2) {
                auto it = mp.find(p.first);
                if (it != mp.end()) {
                    u64 t0 = it->second;
                    u64 t1 = p.second;
                    M = (t1 > t0) ? (t1 - t0) : (t0 - t1);
                    if (M) break;
                }
            }
            if (M == 0) {
                // As a last attempt, compare all within block1
                unordered_map<long long, u64> mp2;
                mp2.reserve(B);
                for (auto &p : block1) {
                    auto it = mp2.find(p.first);
                    if (it != mp2.end()) {
                        u64 t0 = it->second;
                        u64 t1 = p.second;
                        M = (t1 > t0) ? (t1 - t0) : (t0 - t1);
                        if (M) break;
                    } else mp2[p.first] = p.second;
                }
            }
        }

        if (M == 0) {
            // Could not find collision; as a safe fallback, declare minimal cycle 3 (guessed).
            // But better to try powers of two to find first multiple
            // Exponential search for equality (rarely succeeds unless s is small)
            u64 d = 1;
            bool found = false;
            for (int i = 0; i < 60; ++i) {
                if (check_divides(d, baseVal)) { M = d; found = true; break; }
                if (d > (u64)5e18 / 2) break;
                d <<= 1;
            }
            if (!found) M = d; // fallback
        }

        // Now reduce M down to s by factoring and dividing out factors while keeping divisibility
        map<u64,int> pf;
        factor(M, pf);
        for (auto [p, cnt] : pf) {
            for (int i = 0; i < cnt; ++i) {
                u64 M2 = M / p;
                if (M2 == 0) break;
                if (check_divides(M2, baseVal)) {
                    M = M2;
                } else {
                    break;
                }
            }
        }

        cout << "! " << M << endl;
        cout.flush();
        int verdict;
        if (!(cin >> verdict)) return 0;
        if (verdict == -1) return 0;
    }
    return 0;
}