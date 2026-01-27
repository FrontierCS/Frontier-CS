#include <bits/stdc++.h>
using namespace std;

using u64 = unsigned long long;
using u128 = __uint128_t;

static const unsigned long long X_LIMIT = 1000000ULL;
static const unsigned long long XMAX = 5000000000000000000ULL; // 5e18

// Send a query and read the response
long long ask(unsigned long long v, unsigned long long x) {
    cout << "? " << v << " " << x << endl;
    cout.flush();
    long long r;
    if (!(cin >> r)) exit(0);
    return r;
}

void answer(unsigned long long s) {
    cout << "! " << s << endl;
    cout.flush();
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    // Precompute small primes up to 1000
    const int P_LIMIT = 1000;
    vector<int> primes;
    vector<bool> is_comp(P_LIMIT + 1, false);
    for (int i = 2; i <= P_LIMIT; ++i) {
        if (!is_comp[i]) {
            primes.push_back(i);
            if ((long long)i * i <= P_LIMIT) {
                for (int j = i * i; j <= P_LIMIT; j += i) is_comp[j] = true;
            }
        }
    }

    std::mt19937_64 rng((unsigned long long)chrono::high_resolution_clock::now().time_since_epoch().count());

    for (int tc = 0; tc < n; ++tc) {
        // obtain a cycle node c0 from vertex 1
        long long c0 = ask(1, 1);
        if (c0 < 0) return 0;

        auto divisibleBy = [&](unsigned long long K)->bool {
            long long res = ask((unsigned long long)c0, K);
            if (res < 0) exit(0);
            return (res == c0);
        };

        // Build m by multiplying small primes (<= 1000)
        unsigned long long m = 1;
        for (int p : primes) {
            // increase exponent while possible
            while (true) {
                // Check overflow and bounds
                if (m > (unsigned long long)1e6) break;
                if ((long double)m * (long double)p > (long double)XMAX) break;
                unsigned long long cand = m * (unsigned long long)p;
                if (cand > (unsigned long long)1e6) break;
                if (divisibleBy(cand)) {
                    m = cand;
                } else break;
            }
        }

        // Try to find a residual large prime factor s' (>1000), such that s = m * s'
        // We attempt random X in [1, X_LIMIT], test if s | m*X -> s' | X.
        // If yes, factor X by dividing small primes to extract residual > 1 (must be s').
        unsigned long long s_residual = 1;
        int attempts = 0;
        int max_attempts = 2000;

        while (attempts < max_attempts) {
            ++attempts;
            unsigned long long X = (rng() % X_LIMIT) + 1ULL;
            // If m * X exceeds 5e18, skip
            if ((long double)m * (long double)X > (long double)XMAX) continue;

            if (divisibleBy(m * X)) {
                // factor X by small primes up to 1000
                unsigned long long Y = X;
                for (int p : primes) {
                    while (Y % (unsigned long long)p == 0ULL) Y /= (unsigned long long)p;
                }
                if (Y > 1ULL) {
                    s_residual = Y;
                    break;
                }
                // else rare: X is composed only of small primes, try again
            }
        }

        unsigned long long s = m;
        if (s_residual > 1) {
            // verify and include residual
            if ((long double)s * (long double)s_residual <= (long double)XMAX && s * s_residual <= (unsigned long long)1e6) {
                s *= s_residual;
            } else {
                // If multiplying exceeds limits or upper bound, try to adjust (fallback: keep m)
            }
        }

        // As a safety check, if we can still multiply s by any small prime powers (<=1000), do it
        for (int p : primes) {
            while (true) {
                if (s > (unsigned long long)1e6) break;
                if ((long double)s * (long double)p > (long double)XMAX) break;
                unsigned long long cand = s * (unsigned long long)p;
                if (cand > (unsigned long long)1e6) break;
                if (divisibleBy(cand)) s = cand; else break;
            }
        }

        // Final answer
        answer(s);
        int verdict;
        if (!(cin >> verdict)) return 0;
        if (verdict != 1) return 0;
    }
    return 0;
}