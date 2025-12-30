#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;

    // Precompute primes up to sqrt(1e9) = 31623
    const int MAXN = 31623;
    vector<int> primes;
    vector<bool> is_composite(MAXN + 1, false);
    for (int i = 2; i <= MAXN; ++i) {
        if (!is_composite[i]) {
            primes.push_back(i);
            if ((long long)i * i <= MAXN)
                for (int j = i * i; j <= MAXN; j += i)
                    is_composite[j] = true;
        }
    }

    while (T--) {
        long long x;
        cin >> x;
        long long n = x;
        long long res = 1;

        for (int p : primes) {
            if (1LL * p * p > n) break;
            if (n % p == 0) {
                int cnt = 0;
                while (n % p == 0) {
                    n /= p;
                    ++cnt;
                }
                res *= (cnt + 1);
            }
        }
        if (n > 1) res *= 2; // remaining prime factor

        cout << res << '\n';
    }

    return 0;
}