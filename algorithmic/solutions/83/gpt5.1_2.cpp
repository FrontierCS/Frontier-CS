#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    vector<int> lpf(n + 1, 0);
    vector<int> primes;
    primes.reserve(n / 10);

    // Linear sieve to compute least prime factor
    for (int i = 2; i <= n; ++i) {
        if (lpf[i] == 0) {
            lpf[i] = i;
            primes.push_back(i);
        }
        for (int p : primes) {
            long long v = 1LL * p * i;
            if (v > n) break;
            lpf[v] = p;
            if (p == lpf[i]) break;
        }
    }

    vector<int> f(n + 1);
    f[1] = 1;
    for (int i = 2; i <= n; ++i) {
        f[i] = -f[i / lpf[i]]; // Liouville function: (-1)^{Ω(i)}
    }

    for (int i = 1; i <= n; ++i) {
        cout << f[i];
        if (i < n) cout << ' ';
    }
    cout << '\n';

    return 0;
}