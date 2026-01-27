#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    if (n < 1) return 0;

    vector<int> spf(n + 1, 0);
    vector<int> primes;
    primes.reserve(n / 10);

    for (int i = 2; i <= n; ++i) {
        if (spf[i] == 0) {
            spf[i] = i;
            primes.push_back(i);
        }
        for (int p : primes) {
            long long x = 1LL * p * i;
            if (x > n || p > spf[i]) break;
            spf[x] = p;
        }
    }

    vector<int> f(n + 1);
    f[1] = 1;

    uint64_t rng = 123456789;
    auto rand_sign = [&]() -> int {
        rng ^= rng << 7;
        rng ^= rng >> 9;
        return (rng & 1) ? 1 : -1;
    };

    for (int i = 2; i <= n; ++i) {
        int p = spf[i];
        int j = i / p;
        if (p == i) { // prime
            f[i] = rand_sign();
        } else {
            f[i] = f[p] * f[j];
        }
    }

    for (int i = 1; i <= n; ++i) {
        if (i > 1) cout << ' ';
        cout << f[i];
    }
    cout << '\n';

    return 0;
}