#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;

    vector<int> spf(n + 1, 0);
    vector<int> primes;
    primes.reserve(n / 10);

    if (n >= 1) spf[1] = 1;
    for (int i = 2; i <= n; ++i) {
        if (spf[i] == 0) {
            spf[i] = i;
            primes.push_back(i);
        }
        for (int p : primes) {
            long long v = 1LL * i * p;
            if (v > n) break;
            spf[v] = p;
            if (p == spf[i]) break;
        }
    }

    vector<int8_t> f(n + 1, 1);
    for (int i = 2; i <= n; ++i) {
        f[i] = -f[i / spf[i]];
    }

    string out;
    out.reserve((size_t)3 * n + 2);
    for (int i = 1; i <= n; ++i) {
        if (f[i] == 1) out.push_back('1');
        else { out.push_back('-'); out.push_back('1'); }
        if (i < n) out.push_back(' ');
        else out.push_back('\n');
    }
    cout << out;
    return 0;
}