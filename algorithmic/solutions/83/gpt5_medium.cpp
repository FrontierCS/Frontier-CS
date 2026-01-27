#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;

    vector<int> spf(n + 1, 0), primes;
    if (n >= 1) spf[1] = 1;
    for (int i = 2; i <= n; ++i) {
        if (spf[i] == 0) {
            spf[i] = i;
            primes.push_back(i);
        }
        for (int p : primes) {
            long long x = 1LL * i * p;
            if (x > n) break;
            spf[x] = p;
            if (p == spf[i]) break;
        }
    }

    vector<signed char> f(n + 1, 1);
    if (n >= 1) f[1] = 1;
    for (int i = 2; i <= n; ++i) {
        f[i] = -f[i / spf[i]];
    }

    for (int i = 1; i <= n; ++i) {
        if (i > 1) cout << ' ';
        cout << int(f[i]);
    }
    cout << '\n';
    return 0;
}