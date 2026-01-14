#include <bits/stdc++.h>
using namespace std;

using u128 = unsigned __int128;
using u64 = unsigned long long;
using i64 = long long;

static random_device rd;
static mt19937_64 rng(rd());

u64 mul_mod(u64 a, u64 b, u64 mod) {
    return (u128)a * b % mod;
}
u64 pow_mod(u64 a, u64 e, u64 mod) {
    u64 r = 1;
    while (e) {
        if (e & 1) r = mul_mod(r, a, mod);
        a = mul_mod(a, a, mod);
        e >>= 1;
    }
    return r;
}
bool isPrime64(u64 n) {
    if (n < 2) return false;
    static u64 testPrimes[] = {2ULL,3ULL,5ULL,7ULL,11ULL,13ULL,17ULL,19ULL,23ULL,0};
    for (int i=0; testPrimes[i]; ++i) {
        if (n % testPrimes[i] == 0) return n == testPrimes[i];
    }
    u64 d = n - 1;
    int s = 0;
    while ((d & 1) == 0) { d >>= 1; ++s; }
    auto check = [&](u64 a) {
        if (a % n == 0) return true;
        u64 x = pow_mod(a, d, n);
        if (x == 1 || x == n - 1) return true;
        for (int r = 1; r < s; ++r) {
            x = mul_mod(x, x, n);
            if (x == n - 1) return true;
        }
        return false;
    };
    // Deterministic bases for 64-bit
    u64 bases[] = {2ULL, 3ULL, 5ULL, 7ULL, 11ULL, 13ULL, 17ULL, 0ULL};
    for (int i=0; bases[i]; ++i) {
        if (!check(bases[i])) return false;
    }
    return true;
}
u64 pollard(u64 n) {
    if ((n & 1ULL) == 0) return 2;
    if (n % 3ULL == 0) return 3;
    uniform_int_distribution<u64> dist(2, n-2);
    while (true) {
        u64 c = dist(rng);
        u64 x = dist(rng);
        u64 y = x;
        u64 d = 1;
        auto f = [&](u64 v){ return (mul_mod(v, v, n) + c) % n; };
        while (d == 1) {
            x = f(x);
            y = f(f(y));
            u64 diff = x > y ? x - y : y - x;
            d = std::gcd(diff, n);
        }
        if (d != n) return d;
    }
}
void factor(u64 n, vector<u64>& res) {
    if (n == 1) return;
    if (isPrime64(n)) { res.push_back(n); return; }
    u64 d = pollard(n);
    factor(d, res);
    factor(n/d, res);
}
long long ask(long long v, unsigned long long x) {
    cout << "? " << v << " " << x << endl;
    cout.flush();
    long long r;
    if (!(cin >> r)) {
        exit(0);
    }
    return r;
}
int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    if (!(cin >> n)) return 0;
    const u64 MAXX = 5000000000000000000ULL;

    for (int tc = 0; tc < n; ++tc) {
        // Get a cycle vertex c via one step from 1
        long long c = ask(1, 1);
        // We'll operate from starting vertex c
        auto askC = [&](u64 x)->long long {
            return ask(c, x);
        };

        // Cache F(1) for later divisibility checks
        long long f1 = askC(1);

        unordered_map<long long, u64> seen; // vertex id -> x
        seen.reserve(4096);
        seen.max_load_factor(0.7f);
        // Treat F(0) = c as known
        seen[c] = 0;

        // Keep also cache of x->y to reuse in checks if needed
        unordered_map<u64, long long> xy;
        xy.reserve(4096);
        xy.max_load_factor(0.7f);
        xy[1] = f1;

        u64 diff = 0;
        // We'll try up to 2400 random queries to find a collision
        int max_random_queries = 2400;
        uniform_int_distribution<u64> dist(1, MAXX);
        unordered_set<u64> usedx;
        usedx.reserve(4096);
        usedx.insert(1);

        for (int i = 0; i < max_random_queries; ++i) {
            u64 x;
            do {
                x = dist(rng);
            } while (usedx.find(x) != usedx.end());
            usedx.insert(x);
            long long y = askC(x);
            xy[x] = y;
            auto it = seen.find(y);
            if (it != seen.end()) {
                u64 prevx = it->second;
                if (prevx != x) {
                    diff = (x > prevx) ? (x - prevx) : (prevx - x);
                    if (diff == 0) continue;
                    break;
                }
            } else {
                seen.emplace(y, x);
            }
        }

        // If still no collision, try a small BSGS-like pass to intersect with seen
        if (diff == 0) {
            int giants = 200;
            // pick a random step
            u64 step = dist(rng) | 1ULL;
            for (int j = 1; j <= giants; ++j) {
                u64 x = step * (u64)j;
                if (x == 0 || x > MAXX) { continue; }
                if (usedx.insert(x).second == false) continue;
                long long y = askC(x);
                xy[x] = y;
                auto it = seen.find(y);
                if (it != seen.end()) {
                    u64 prevx = it->second;
                    if (prevx != x) {
                        diff = (x > prevx) ? (x - prevx) : (prevx - x);
                        if (diff != 0) break;
                    }
                } else {
                    seen.emplace(y, x);
                }
            }
        }

        // In the very unlikely case diff is still zero, keep querying until found
        while (diff == 0) {
            u64 x;
            do {
                x = dist(rng);
            } while (usedx.find(x) != usedx.end());
            usedx.insert(x);
            long long y = askC(x);
            xy[x] = y;
            auto it = seen.find(y);
            if (it != seen.end()) {
                u64 prevx = it->second;
                if (prevx != x) {
                    diff = (x > prevx) ? (x - prevx) : (prevx - x);
                    if (diff != 0) break;
                }
            } else {
                seen.emplace(y, x);
            }
        }

        // Now diff is a multiple of s. Factor diff and shrink to minimal s.
        vector<u64> fac;
        factor(diff, fac);
        sort(fac.begin(), fac.end());

        u64 ans = diff;
        // Divisibility test using F(1 + L) == F(1)
        auto divisible = [&](u64 L)->bool {
            if (L > MAXX - 1) return false;
            long long y2 = askC(1 + L);
            return y2 == f1;
        };

        for (size_t i = 0; i < fac.size();) {
            u64 p = fac[i];
            size_t j = i;
            while (j < fac.size() && fac[j] == p) ++j;
            // Try to divide ans by p^k as much as possible
            for (size_t k = i; k < j; ++k) {
                if (ans % p == 0) {
                    u64 candidate = ans / p;
                    if (divisible(candidate)) {
                        ans = candidate;
                    } else {
                        break;
                    }
                }
            }
            i = j;
        }

        cout << "! " << ans << endl;
        cout.flush();
        long long verdict;
        if (!(cin >> verdict)) return 0;
        if (verdict != 1) return 0;
    }
    return 0;
}