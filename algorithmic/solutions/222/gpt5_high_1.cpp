#include <bits/stdc++.h>
using namespace std;

using u64 = unsigned long long;
using u128 = __uint128_t;

static mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());

struct Solver {
    int n;
    int q_used = 0;
    const int Q_LIMIT = 2500;
    const u64 XMAX = 5000000000000000000ULL; // 5e18

    u64 ask(u64 v, u64 x) {
        cout << "? " << v << " " << x << endl;
        cout.flush();
        u64 y;
        if (!(cin >> y)) {
            exit(0);
        }
        q_used++;
        return y;
    }

    void answer(u64 s) {
        cout << "! " << s << endl;
        cout.flush();
    }

    static inline u64 mul_mod(u64 a, u64 b, u64 mod) {
        return (u128)a * b % mod;
    }

    static inline u64 pow_mod(u64 a, u64 d, u64 mod) {
        u64 res = 1 % mod;
        while (d) {
            if (d & 1) res = mul_mod(res, a, mod);
            a = mul_mod(a, a, mod);
            d >>= 1;
        }
        return res;
    }

    bool isPrime(u64 n) {
        if (n < 2) return false;
        static u64 testPrimes[] = {2ULL,3ULL,5ULL,7ULL,11ULL,13ULL,17ULL,0};
        for (u64 p : testPrimes) {
            if (p == 0) break;
            if (n % p == 0) return n == p;
        }
        u64 d = n - 1, s = 0;
        while ((d & 1) == 0) { d >>= 1; s++; }
        auto trial = [&](u64 a)->bool {
            if (a % n == 0) return true;
            u64 x = pow_mod(a, d, n);
            if (x == 1 || x == n - 1) return true;
            for (u64 r = 1; r < s; r++) {
                x = mul_mod(x, x, n);
                if (x == n - 1) return true;
            }
            return false;
        };
        for (u64 a : testPrimes) {
            if (a == 0) break;
            if (!trial(a)) return false;
        }
        // Additional bases for 64-bit determinism
        static u64 moreBases[] = {19ULL,23ULL,29ULL,31ULL,37ULL,0};
        for (u64 a : moreBases) {
            if (a == 0) break;
            if (a >= n) continue;
            if (!trial(a)) return false;
        }
        return true;
    }

    u64 pollard(u64 n) {
        if (n % 2ULL == 0ULL) return 2ULL;
        if (n % 3ULL == 0ULL) return 3ULL;
        uniform_int_distribution<u64> dist(2ULL, n - 2ULL);
        while (true) {
            u64 c = dist(rng);
            u64 x = dist(rng);
            u64 y = x;
            u64 d = 1;
            auto f = [&](u64 v)->u64 {
                u64 t = mul_mod(v, v, n);
                t += c;
                if (t >= n) t -= n;
                return t;
            };
            while (d == 1) {
                x = f(x);
                y = f(f(y));
                u64 diff = x > y ? x - y : y - x;
                d = std::gcd(diff, n);
            }
            if (d != n) return d;
        }
    }

    void factor_rec(u64 n, vector<u64>& fac) {
        if (n == 1) return;
        if (isPrime(n)) { fac.push_back(n); return; }
        u64 d = pollard(n);
        factor_rec(d, fac);
        factor_rec(n / d, fac);
    }

    u64 getCollisionDifference(u64 v, int maxSamples) {
        unordered_map<u64, u64> seen; seen.reserve(maxSamples * 2);
        unordered_set<u64> usedX; usedX.reserve(maxSamples * 2);
        uniform_int_distribution<u64> dist(1ULL, XMAX);
        for (int i = 0; i < maxSamples; i++) {
            u64 x;
            do {
                x = dist(rng);
            } while (usedX.find(x) != usedX.end());
            usedX.insert(x);
            u64 y = ask(v, x);
            auto it = seen.find(y);
            if (it != seen.end()) {
                u64 xprev = it->second;
                u64 d = (x > xprev) ? (x - xprev) : (xprev - x);
                if (d == 0) continue; // should not happen due uniqueness
                return d;
            } else {
                seen.emplace(y, x);
            }
        }
        return 0;
    }

    bool dividesTest(u64 v, u64 delta, u64 r1) {
        u64 r2 = ask(v, 1 + delta);
        return r1 == r2;
    }

    u64 refineToExactS(u64 v, u64 d) {
        // d is a multiple of s
        // Factor d and iteratively divide by prime factors if possible
        vector<u64> fac;
        factor_rec(d, fac);
        unordered_map<u64,int> cnt;
        for (u64 p : fac) cnt[p]++;
        vector<pair<u64,int>> pf;
        pf.reserve(cnt.size());
        for (auto &kv : cnt) pf.push_back(kv);
        // sort to try small primes first (optional)
        sort(pf.begin(), pf.end());
        u64 sCand = d;
        u64 r1 = ask(v, 1); // base value for comparison
        for (auto &pe : pf) {
            u64 p = pe.first;
            int e = pe.second;
            for (int i = 0; i < e; i++) {
                u64 newCand = sCand / p;
                if (newCand == 0) break;
                if (dividesTest(v, newCand, r1)) {
                    sCand = newCand;
                } else {
                    break;
                }
            }
        }
        return sCand;
    }

    void solveOne() {
        q_used = 0;
        u64 v = 1;
        // Try to find a collision difference
        int budgetForSamples = 2100; // leave ~400 for factor tests
        u64 d = getCollisionDifference(v, budgetForSamples);
        if (d == 0) {
            // As a fallback, try more samples if budget allows
            int extra = max(0, Q_LIMIT - q_used - 100);
            if (extra > 0) {
                int extraSamples = min(extra, 400);
                d = getCollisionDifference(v, extraSamples);
            }
        }
        // If still no collision, make a last effort
        if (d == 0) {
            // Try from another vertex with remaining budget
            u64 v2 = 2;
            int extra = max(0, Q_LIMIT - q_used - 100);
            if (extra > 0) {
                d = getCollisionDifference(v2, extra);
                v = (d ? v2 : v);
            }
        }
        // If we still have no collision, we cannot proceed. Output a fallback guess (3) to avoid infinite loop.
        if (d == 0) {
            u64 s_guess = 3;
            answer(s_guess);
            int verdict;
            if (!(cin >> verdict)) exit(0);
            if (verdict != 1) exit(0);
            return;
        }
        u64 s = refineToExactS(v, d);
        answer(s);
        int verdict;
        if (!(cin >> verdict)) exit(0);
        if (verdict != 1) exit(0);
    }

    void run() {
        ios::sync_with_stdio(false);
        cin.tie(nullptr);

        if (!(cin >> n)) return;
        for (int i = 0; i < n; i++) {
            solveOne();
        }
    }
};

int main() {
    Solver solver;
    solver.run();
    return 0;
}