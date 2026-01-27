#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    vector<int> spf(n + 1, 0);
    vector<int> primes;
    primes.reserve(max(1, n / 10));

    for (int i = 2; i <= n; i++) {
        if (spf[i] == 0) {
            spf[i] = i;
            primes.push_back(i);
        }
        for (int p : primes) {
            long long v = 1LL * p * i;
            if (v > n) break;
            spf[(int)v] = p;
            if (p == spf[i]) break;
        }
    }

    vector<int8_t> f(n + 1, 0);
    f[1] = 1;
    for (int i = 2; i <= n; i++) {
        f[i] = (int8_t)(-f[i / spf[i]]); // Liouville function: f(p) = -1 for all primes
    }

    string out;
    out.reserve((size_t)n * 3 + 2);
    for (int i = 1; i <= n; i++) {
        if (i > 1) out.push_back(' ');
        if (f[i] == 1) {
            out.push_back('1');
        } else {
            out.push_back('-');
            out.push_back('1');
        }
    }
    out.push_back('\n');
    cout << out;
    return 0;
}