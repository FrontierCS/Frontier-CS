#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;

    const int LIMIT = 40000;
    vector<int> primes;
    vector<bool> is_comp(LIMIT + 1, false);
    for (int i = 2; i <= LIMIT; ++i) {
        if (!is_comp[i]) {
            primes.push_back(i);
            if (1LL * i * i <= LIMIT)
                for (long long j = 1LL * i * i; j <= LIMIT; j += i)
                    is_comp[(int)j] = true;
        }
    }

    while (T--) {
        long long X;
        if (!(cin >> X)) break;
        long long n = X;
        long long ans = 1;

        for (int p : primes) {
            if (1LL * p * p > n) break;
            if (n % p == 0) {
                int cnt = 0;
                while (n % p == 0) {
                    n /= p;
                    ++cnt;
                }
                ans *= (cnt + 1);
            }
        }
        if (n > 1) ans *= 2;

        cout << ans << '\n';
    }

    return 0;
}