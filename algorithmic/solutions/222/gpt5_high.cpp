#include <bits/stdc++.h>
using namespace std;

using u64 = unsigned long long;
using u128 = __uint128_t;

static std::mt19937_64 rng((u64)chrono::high_resolution_clock::now().time_since_epoch().count());

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
    static u64 testPrimes[] = {2ULL,3ULL,5ULL,7ULL,11ULL,13ULL,17ULL,0};
    for (int i = 0; testPrimes[i]; ++i) {
        if (n % testPrimes[i] == 0) return n == testPrimes[i];
    }
    u64 d = n - 1, s = 0;
    while ((d & 1) == 0) { d >>= 1; ++s; }
    auto trial = [&](u64 a)->bool{
        if (a % n == 0) return true;
        u64 x = pow_mod(a, d, n);
        if (x == 1 || x == n - 1) return true;
        for (u64 r = 1; r < s; ++r) {
            x = mul_mod(x, x, n);
            if (x == n - 1) return true;
        }
        return false;
    };
    for (int i = 0; testPrimes[i]; ++i) {
        if (!trial(testPrimes[i])) return false;
    }
    return true;
}

u64 rho(u64 n) {
    if ((n & 1ULL) == 0ULL) return 2ULL;
    std::uniform_int_distribution<u64> dist(2ULL, n - 2ULL);
    while (true) {
        u64 c = dist(rng);
        u64 x = dist(rng), y = x, d = 1;
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

u64 ask(u64 v, u64 x) {
    cout << "? " << v << " " << x << endl;
    cout.flush();
    u64 ans;
    if (!(cin >> ans)) exit(0);
    return ans;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    const u64 X_LIMIT = 5000000000000000000ULL; // 5e18
    for (int tc = 0; tc < n; ++tc) {
        // Get a cycle node
        u64 c = ask(1, 1);

        // Prepare storage for seen nodes
        const int MAXV = 1000000 + 5;
        vector<u64> seen(MAXV, 0ULL);

        u64 g = 0ULL;
        int queries_used = 1; // initial ask

        // Sample until first collision or until near limit
        int max_samples = 2400; // leave room for reduction and final checks
        std::uniform_int_distribution<u64> dist(1ULL, X_LIMIT);

        for (int i = 0; i < max_samples; ++i) {
            u64 x = dist(rng);
            u64 y = ask(c, x);
            ++queries_used;
            if (y < seen.size()) {
                if (seen[y] == 0ULL) {
                    seen[y] = x;
                } else {
                    u64 d = (x > seen[y]) ? (x - seen[y]) : (seen[y] - x);
                    if (d != 0) {
                        g = std::gcd(g, d);
                        break;
                    }
                }
            } else {
                // y should be <= 1e6 as per statement, but handle gracefully
                // Use unordered_map as fallback
                // We'll rarely reach here; allocate on demand
                static unordered_map<u64, u64> seen_map;
                auto it = seen_map.find(y);
                if (it == seen_map.end()) {
                    seen_map[y] = x;
                } else {
                    u64 d = (x > it->second) ? (x - it->second) : (it->second - x);
                    if (d != 0) {
                        g = std::gcd(g, d);
                        break;
                    }
                }
            }
        }

        // If no collision was found, try further a bit
        if (g == 0ULL) {
            int extra = 100;
            for (int i = 0; i < extra; ++i) {
                u64 x = dist(rng);
                u64 y = ask(c, x);
                ++queries_used;
                if (y < seen.size()) {
                    if (seen[y] == 0ULL) {
                        seen[y] = x;
                    } else {
                        u64 d = (x > seen[y]) ? (x - seen[y]) : (seen[y] - x);
                        if (d != 0) {
                            g = std::gcd(g, d);
                            break;
                        }
                    }
                }
            }
        }

        // If still no collision, we have to guess (fallback). We'll try a few structured queries.
        if (g == 0ULL) {
            // Try to force collision by querying repeating x modulo small M
            // This is a last resort; not guaranteed but may help.
            u64 base = dist(rng);
            u64 step = 1000003ULL; // prime > 1e6
            u64 y0 = ask(c, base);
            ++queries_used;
            for (int i = 1; i <= 100 && !g; ++i) {
                u64 x = base + step * (u64)i;
                if (x > X_LIMIT) break;
                u64 y = ask(c, x);
                ++queries_used;
                if (y == y0) {
                    g = step * (u64)i;
                    break;
                }
            }
        }

        // If still no collision, output a default answer 3 to proceed
        if (g == 0ULL) {
            cout << "! " << 3 << endl;
            cout.flush();
            int ok;
            if (!(cin >> ok)) return 0;
            if (ok == -1) return 0;
            continue;
        }

        // Reduce g to the minimal t such that next^t(c) == c
        // Factor g using Pollard Rho
        vector<u64> facs;
        factor(g, facs);
        sort(facs.begin(), facs.end());
        // unique primes with exponents
        vector<pair<u64,int>> pf;
        for (size_t i = 0; i < facs.size();) {
            size_t j = i;
            while (j < facs.size() && facs[j] == facs[i]) ++j;
            pf.push_back({facs[i], (int)(j - i)});
            i = j;
        }

        // Try dividing by each prime as much as possible while property holds
        for (auto &pr : pf) {
            u64 p = pr.first;
            while (g % p == 0) {
                u64 t = g / p;
                u64 ret = ask(c, t);
                ++queries_used;
                if (ret == c) g = t;
                else break;
            }
        }

        // Output the final result
        cout << "! " << g << endl;
        cout.flush();
        int ok;
        if (!(cin >> ok)) return 0;
        if (ok == -1) return 0;
    }

    return 0;
}