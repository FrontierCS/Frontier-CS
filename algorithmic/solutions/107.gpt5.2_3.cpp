#include <bits/stdc++.h>
using namespace std;

static const long long LIM = (long long)1e18;

static long long ask(long long q) {
    cout << "0 " << q << "\n";
    cout.flush();
    long long g;
    if (!(cin >> g)) exit(0);
    if (g == -1) exit(0);
    return g;
}

static vector<int> sieve_primes(int n) {
    vector<bool> isPrime(n + 1, true);
    isPrime[0] = isPrime[1] = false;
    for (int i = 2; 1LL * i * i <= n; i++) if (isPrime[i]) {
        for (int j = i * i; j <= n; j += i) isPrime[j] = false;
    }
    vector<int> primes;
    for (int i = 2; i <= n; i++) if (isPrime[i]) primes.push_back(i);
    return primes;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;

    const int MAXP = 2000;
    vector<int> primes = sieve_primes(MAXP);

    // Build blocks: product of distinct primes in each block <= 1e18
    vector<long long> blocksQ;
    vector<vector<int>> blocksP;
    for (int i = 0; i < (int)primes.size();) {
        __int128 cur = 1;
        vector<int> ps;
        while (i < (int)primes.size()) {
            int p = primes[i];
            if (cur * p > LIM) break;
            cur *= p;
            ps.push_back(p);
            i++;
        }
        if (ps.empty()) { // should not happen for primes<=2000
            ps.push_back(primes[i]);
            cur = primes[i];
            i++;
        }
        blocksQ.push_back((long long)cur);
        blocksP.push_back(std::move(ps));
    }

    for (int tc = 0; tc < T; tc++) {
        vector<int> found;
        vector<char> isFound(MAXP + 1, 0);

        // Discover which primes <= 2000 divide X
        for (int bi = 0; bi < (int)blocksQ.size(); bi++) {
            long long g = ask(blocksQ[bi]);
            if (g <= 1) continue;
            for (int p : blocksP[bi]) {
                if (g % p == 0) {
                    if (!isFound[p]) {
                        isFound[p] = 1;
                        found.push_back(p);
                    }
                    while (g % p == 0) g /= p;
                }
                if (g == 1) break;
            }
        }

        long long ans = 1;

        // Determine exact exponents for found primes
        for (int p : found) {
            __int128 q = 1;
            while (q * p <= LIM) q *= p;
            long long g = ask((long long)q);
            int e = 0;
            while (g % p == 0) {
                g /= p;
                e++;
            }
            ans *= (e + 1);
        }

        // Remaining part has primes > 2000 => divisor multiplier m in [1..4]
        // Output multiplier 2 guarantees 1/2 <= ans/d <= 2.
        ans *= 2;

        cout << "1 " << ans << "\n";
        cout.flush();
    }

    return 0;
}