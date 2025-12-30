#include <bits/stdc++.h>
using namespace std;

static const long long LIMX = 1000000000LL;
static const long long LIMQ = (long long)1e18;

static vector<int> sievePrimes(int n) {
    vector<int> primes;
    vector<bool> isPrime(n + 1, true);
    isPrime[0] = isPrime[1] = false;
    for (int i = 2; i <= n; i++) {
        if (!isPrime[i]) continue;
        primes.push_back(i);
        if ((long long)i * i <= n) {
            for (long long j = 1LL * i * i; j <= n; j += i) isPrime[(int)j] = false;
        }
    }
    return primes;
}

static long long ask(long long q) {
    cout << "0 " << q << "\n";
    cout.flush();
    long long g;
    if (!(cin >> g)) exit(0);
    if (g == -1) exit(0);
    return g;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;

    vector<int> primes = sievePrimes(1000);

    // Build query groups as products of primes (each prime once) so that product <= 1e18.
    vector<long long> groups;
    {
        __int128 cur = 1;
        for (int p : primes) {
            if (cur * p > LIMQ) {
                groups.push_back((long long)cur);
                cur = 1;
            }
            cur *= p;
        }
        if (cur > 1) groups.push_back((long long)cur);
    }

    for (int tc = 0; tc < T; tc++) {
        int queries = 0;

        vector<int> found;
        found.reserve(16);

        // Detect all prime divisors <= 1000.
        for (long long Q : groups) {
            long long g = ask(Q);
            queries++;

            long long x = g;
            for (int p : primes) {
                if (x % p == 0) {
                    found.push_back(p);
                    while (x % p == 0) x /= p;
                }
                if (x == 1) break;
            }
        }

        sort(found.begin(), found.end());
        found.erase(unique(found.begin(), found.end()), found.end());

        long long d_part = 1;

        // For each found prime, determine its exact exponent in X by querying p^k (k max such that p^k <= 1e9).
        for (int p : found) {
            long long pw = 1;
            while (pw <= LIMX / p) pw *= p; // largest power of p <= 1e9
            long long g = ask(pw);
            queries++;

            int e = 0;
            while (g % p == 0) {
                g /= p;
                e++;
            }
            d_part *= (e + 1);
        }

        // Remaining part (all primes > 1000) has divisor count in {1,2,3,4}; multiply by 2 to stay within factor-2 always.
        long long ans = d_part * 2;

        cout << "1 " << ans << "\n";
        cout.flush();
    }

    return 0;
}