#include <bits/stdc++.h>
using namespace std;

using u64 = unsigned long long;
using u128 = __uint128_t;

const u64 MAX_X = 5000000000000000000ULL; // 5e18
const int QUERY_LIMIT = 2500;

// RNG for Pollard Rho and random queries
static mt19937_64 rng((u64)chrono::steady_clock::now().time_since_epoch().count());

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
    static const u64 small_primes[] = {2,3,5,7,11,13,17,19,23,29,31,37};
    for (u64 p : small_primes) {
        if (n == p) return true;
        if (n % p == 0) return false;
    }
    u64 d = n - 1;
    int s = 0;
    while ((d & 1) == 0) {
        d >>= 1;
        ++s;
    }
    auto check = [&](u64 a)->bool{
        if (a % n == 0) return true;
        u64 x = pow_mod(a, d, n);
        if (x == 1 || x == n - 1) return true;
        for (int r = 1; r < s; ++r) {
            x = mul_mod(x, x, n);
            if (x == n - 1) return true;
        }
        return false;
    };
    static const u64 testPrimes[] = {2ULL,325ULL,9375ULL,28178ULL,450775ULL,9780504ULL,1795265022ULL};
    for (u64 a : testPrimes) {
        if (a == 0) continue;
        if (!check(a)) return false;
    }
    return true;
}

u64 pollard(u64 n) {
    if (n % 2 == 0) return 2;
    if (n % 3 == 0) return 3;
    u64 c = uniform_int_distribution<u64>(1, n - 1)(rng);
    u64 x = uniform_int_distribution<u64>(0, n - 1)(rng);
    u64 y = x;
    u64 d = 1;
    auto f = [&](u64 v)->u64{
        return (mul_mod(v, v, n) + c) % n;
    };
    while (d == 1) {
        x = f(x);
        y = f(f(y));
        u64 diff = x > y ? x - y : y - x;
        d = std::gcd(diff, n);
        if (d == n) {
            return pollard(n);
        }
    }
    return d;
}

void factor_rec(u64 n, vector<u64> &fac) {
    if (n == 1) return;
    if (isPrime(n)) {
        fac.push_back(n);
        return;
    }
    u64 d = pollard(n);
    factor_rec(d, fac);
    factor_rec(n / d, fac);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;

    for (int tc = 0; tc < T; ++tc) {
        int qcnt = 0;

        // Get one cycle vertex: next(1)
        cout << "? " << 1 << " " << 1 << "\n";
        cout.flush();
        ++qcnt;
        long long c0_ll;
        if (!(cin >> c0_ll)) return 0;
        u64 c0 = (u64)c0_ll;

        // Collision phase from c0
        unordered_map<u64, u64> val2x;
        val2x.reserve(4096);
        val2x.max_load_factor(0.7f);

        unordered_set<u64> used_x;
        used_x.reserve(4096);
        used_x.max_load_factor(0.7f);

        u64 g = 0;
        const int RESERVED_FOR_FACT = 80;
        while (qcnt < QUERY_LIMIT - RESERVED_FOR_FACT) {
            u64 x;
            do {
                x = uniform_int_distribution<u64>(1, MAX_X)(rng);
            } while (used_x.find(x) != used_x.end());
            used_x.insert(x);

            cout << "? " << c0 << " " << x << "\n";
            cout.flush();
            ++qcnt;
            long long v_ans_ll;
            if (!(cin >> v_ans_ll)) return 0;
            u64 v_ans = (u64)v_ans_ll;

            auto it = val2x.find(v_ans);
            if (it != val2x.end()) {
                u64 prev_x = it->second;
                u64 d = x > prev_x ? x - prev_x : prev_x - x;
                if (d > 0) {
                    if (g == 0) g = d;
                    else g = std::gcd(g, d);
                    // We could continue to refine g with more collisions,
                    // but one non-zero g is enough; break to save queries.
                    break;
                }
            } else {
                val2x[v_ans] = x;
            }
        }

        // Fallback if no collision found: just guess minimal valid cycle length 3.
        if (g == 0) {
            u64 s_guess = 3;
            cout << "! " << s_guess << "\n";
            cout.flush();
            int verdict;
            if (!(cin >> verdict)) return 0;
            if (verdict == -1) return 0;
            continue;
        }

        // Factor g
        vector<u64> fac;
        factor_rec(g, fac);
        sort(fac.begin(), fac.end());
        vector<pair<u64,int>> pf;
        for (u64 p : fac) {
            if (pf.empty() || pf.back().first != p) {
                pf.push_back({p,1});
            } else {
                pf.back().second++;
            }
        }

        // Base query for equality tests
        u64 base_x = MAX_X - g; // base_x + T <= MAX_X for all T <= g
        cout << "? " << c0 << " " << base_x << "\n";
        cout.flush();
        ++qcnt;
        long long base_ans_ll;
        if (!(cin >> base_ans_ll)) return 0;
        u64 base_ans = (u64)base_ans_ll;

        u64 Tcand = g;
        for (auto &pe : pf) {
            u64 p = pe.first;
            int e = pe.second;
            for (int i = 0; i < e; ++i) {
                if (Tcand % p != 0) break;
                u64 candidate = Tcand / p;
                cout << "? " << c0 << " " << (base_x + candidate) << "\n";
                cout.flush();
                ++qcnt;
                long long res_ll;
                if (!(cin >> res_ll)) return 0;
                u64 res = (u64)res_ll;
                if (res == base_ans) {
                    Tcand = candidate;
                } else {
                    break;
                }
            }
        }

        u64 s_final = Tcand;
        if (s_final < 3) s_final = 3; // safety clamp

        cout << "! " << s_final << "\n";
        cout.flush();
        int verdict;
        if (!(cin >> verdict)) return 0;
        if (verdict == -1) return 0;
    }

    return 0;
}