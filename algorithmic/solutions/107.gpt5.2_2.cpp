#include <bits/stdc++.h>
using namespace std;

static const long long LIMQ = (long long)1e18;

static long long ask(long long q) {
    cout << "0 " << q << "\n";
    cout.flush();
    long long g;
    if (!(cin >> g)) exit(0);
    if (g == -1) exit(0);
    return g;
}

static void answer(long long ans) {
    cout << "1 " << ans << "\n";
    cout.flush();
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;

    // Primes up to 1000
    const int MAXP = 1000;
    vector<int> primes;
    vector<bool> isPrime(MAXP + 1, true);
    isPrime[0] = isPrime[1] = false;
    for (int i = 2; i * i <= MAXP; i++) {
        if (isPrime[i]) for (int j = i * i; j <= MAXP; j += i) isPrime[j] = false;
    }
    for (int i = 2; i <= MAXP; i++) if (isPrime[i]) primes.push_back(i);

    // Group primes into products <= 1e18
    vector<long long> groups;
    {
        __int128 cur = 1;
        for (int p : primes) {
            if (cur * p > (__int128)LIMQ) {
                groups.push_back((long long)cur);
                cur = 1;
            }
            cur *= p;
        }
        if (cur > 1) groups.push_back((long long)cur);
    }

    for (int tc = 0; tc < T; tc++) {
        vector<int> found;
        found.reserve(16);

        for (long long q : groups) {
            long long g = ask(q);
            if (g <= 1) continue;
            for (int p : primes) {
                if (g % p == 0) {
                    found.push_back(p);
                    while (g % p == 0) g /= p;
                }
                if (g == 1) break;
            }
        }

        long long d_small = 1;
        for (int p : found) {
            __int128 pw = 1;
            while (pw * p <= (__int128)LIMQ) pw *= p;
            long long g = ask((long long)pw);
            int e = 0;
            while (g % p == 0) {
                g /= p;
                e++;
            }
            d_small *= (e + 1);
        }

        long long ans = 2 * d_small;
        answer(ans);
    }

    return 0;
}