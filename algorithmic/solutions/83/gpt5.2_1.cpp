#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    vector<int> primes;
    primes.reserve(max(1, n / 10));
    vector<int> lp(n + 1, 0);
    vector<int8_t> f(n + 1, 1);
    if (n >= 1) f[1] = 1;

    for (int i = 2; i <= n; i++) {
        if (lp[i] == 0) {
            lp[i] = i;
            primes.push_back(i);
            f[i] = -1; // Liouville: f(p) = -1 for all primes
        }
        for (int p : primes) {
            long long x = 1LL * p * i;
            if (x > n) break;
            lp[(int)x] = p;
            f[(int)x] = (int8_t)(-f[i]); // multiply by a prime flips sign
            if (i % p == 0) break;
        }
    }

    string out;
    out.reserve((size_t)n * 3 + 2);
    for (int i = 1; i <= n; i++) {
        if (f[i] == 1) out += '1';
        else out += "-1";
        out += (i == n ? '\n' : ' ');
    }
    cout << out;
    return 0;
}