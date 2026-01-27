#include <bits/stdc++.h>
using namespace std;

using u64 = unsigned long long;
using u128 = __uint128_t;

// Miller-Rabin and Pollard-Rho for 64-bit integers

u64 mulmod(u64 a, u64 b, u64 mod) {
    return (u128)a * b % mod;
}

u64 powmod(u64 a, u64 e, u64 mod) {
    u64 r = 1;
    while (e) {
        if (e & 1) r = mulmod(r, a, mod);
        a = mulmod(a, a, mod);
        e >>= 1;
    }
    return r;
}

bool isPrime(u64 n) {
    if (n < 2) return false;
    for (u64 p : {2ULL,3ULL,5ULL,7ULL,11ULL,13ULL,17ULL,19ULL,23ULL,29ULL,31ULL,37ULL}) {
        if (n % p == 0) return n == p;
    }
    u64 d = n - 1, s = 0;
    while ((d & 1) == 0) { d >>= 1; ++s; }
    auto witness = [&](u64 a) {
        if (a % n == 0) return false;
        u64 x = powmod(a, d, n);
        if (x == 1 || x == n - 1) return false;
        for (u64 r = 1; r < s; ++r) {
            x = mulmod(x, x, n);
            if (x == n - 1) return false;
        }
        return true;
    };
    // Deterministic bases for 64-bit
    for (u64 a : {2ULL, 3ULL, 5ULL, 7ULL, 11ULL, 13ULL, 17ULL}) {
        if (a >= n) continue;
        if (witness(a)) return false;
    }
    return true;
}

u64 pollard(u64 n, std::mt19937_64 &rng) {
    if ((n & 1ULL) == 0ULL) return 2ULL;
    std::uniform_int_distribution<u64> dist(2ULL, n - 2ULL);
    while (true) {
        u64 c = dist(rng);
        u64 x = dist(rng);
        u64 y = x;
        u64 d = 1;
        auto f = [&](u64 v) { return (mulmod(v, v, n) + c) % n; };
        while (d == 1) {
            x = f(x);
            y = f(f(y));
            u64 diff = x > y ? x - y : y - x;
            d = std::gcd(diff, n);
        }
        if (d != n) return d;
    }
}

void factor(u64 n, vector<u64> &facs, std::mt19937_64 &rng) {
    if (n == 1) return;
    if (isPrime(n)) { facs.push_back(n); return; }
    u64 d = pollard(n, rng);
    factor(d, facs, rng);
    factor(n / d, facs, rng);
}

u64 ask(u64 v, u64 x) {
    cout << "? " << v << " " << x << endl;
    cout.flush();
    u64 res;
    if (!(cin >> res)) {
        // If interaction fails, exit gracefully
        exit(0);
    }
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    std::random_device rd;
    std::mt19937_64 rng((u64)chrono::high_resolution_clock::now().time_since_epoch().count() ^ ((u64)rd() << 1));

    const u64 X_MAX = 5000000000000000000ULL; // 5e18
    std::uniform_int_distribution<u64> distX(1ULL, X_MAX);

    for (int tc = 0; tc < n; ++tc) {
        u64 v = 1; // fixed starting vertex
        // We will collect up to M_max queries to find collisions
        const int M_max = 2400;
        const int target_collisions = 3;

        unordered_map<u64, u64> seen; // map from returned vertex label -> x producing it
        seen.reserve(M_max * 2);
        unordered_set<u64> used_x;
        used_x.reserve(M_max * 2);

        u64 g = 0; // gcd of differences where collisions occur
        int collisions = 0;

        for (int i = 0; i < M_max; ++i) {
            u64 x;
            do {
                x = distX(rng);
            } while (used_x.find(x) != used_x.end());
            used_x.insert(x);

            u64 y = ask(v, x);
            auto it = seen.find(y);
            if (it != seen.end()) {
                u64 prevx = it->second;
                u64 D = (x > prevx ? x - prevx : prevx - x);
                if (D > 0) {
                    g = g == 0 ? D : std::gcd(g, D);
                    collisions++;
                }
            } else {
                seen.emplace(y, x);
            }
            if (collisions >= target_collisions && g != 0) {
                // Early stop to save queries if we already have some gcd
                // But we still might continue a bit for robustness; skip for simplicity
                // break;
                ;
            }
        }

        // If still no collisions, we cannot deduce anything. Fallback: try extra attempts with the same v but biased x.
        if (g == 0) {
            // Try a small structured set to increase chance of collision modulo some s
            // We'll try 80 extra queries spaced by a random step
            const int extraQ = 80;
            u64 step = distX(rng) | 1ULL; // odd step
            u64 base = distX(rng);
            for (int i = 0; i < extraQ; ++i) {
                u64 x = base + i * step;
                if (x == 0 || x > X_MAX) {
                    x = (x % X_MAX) + 1;
                }
                if (used_x.find(x) != used_x.end()) continue;
                used_x.insert(x);
                u64 y = ask(v, x);
                auto it = seen.find(y);
                if (it != seen.end()) {
                    u64 prevx = it->second;
                    u64 D = (x > prevx ? x - prevx : prevx - x);
                    if (D > 0) {
                        g = g == 0 ? D : std::gcd(g, D);
                        collisions++;
                    }
                } else {
                    seen.emplace(y, x);
                }
            }
        }

        u64 s = 0;
        if (g == 0) {
            // As a last resort, guess some plausible value to avoid indefinite behavior.
            // Choose 3 (minimum allowed) as a safe guess.
            s = 3;
        } else {
            // Factor g and reduce to s using equality tests
            vector<u64> facs;
            factor(g, facs, rng);
            // Count prime powers
            unordered_map<u64, int> cnt;
            for (u64 p : facs) cnt[p]++;
            // Sort primes for deterministic behavior (optional)
            vector<pair<u64,int>> pf;
            pf.reserve(cnt.size());
            for (auto &kv : cnt) pf.emplace_back(kv.first, kv.second);
            sort(pf.begin(), pf.end());

            u64 cur = g;
            for (auto &pr : pf) {
                u64 p = pr.first;
                while (cur % p == 0) {
                    u64 cand = cur / p;
                    // Test if period divides cand
                    // Using t=1 ensures 1 + cand <= 5e18 for p>=2
                    u64 a = ask(v, 1);
                    u64 b = ask(v, 1 + cand);
                    if (a == b) {
                        cur = cand;
                    } else {
                        break;
                    }
                }
            }
            s = cur;
            if (s < 3) s = 3; // ensure minimum per problem
        }

        cout << "! " << s << endl;
        cout.flush();
        int verdict;
        if (!(cin >> verdict)) return 0;
        if (verdict == -1) return 0;
    }
    return 0;
}