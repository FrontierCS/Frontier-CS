#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;
    vector<int> spf(n + 1, 0), primes;
    primes.reserve(n / 10);
    for (int i = 2; i <= n; ++i) {
        if (spf[i] == 0) {
            spf[i] = i;
            primes.push_back(i);
        }
        for (int p : primes) {
            long long x = 1LL * p * i;
            if (x > n) break;
            spf[x] = p;
            if (p == spf[i]) break;
        }
    }

    vector<int> f(n + 1, 1);
    for (int i = 2; i <= n; ++i) {
        f[i] = -f[i / spf[i]];
    }

    string out;
    out.reserve(3LL * n + 1);
    for (int i = 1; i <= n; ++i) {
        if (f[i] == 1) out += '1';
        else { out += '-'; out += '1'; }
        if (i < n) out += ' ';
    }
    out += '\n';
    cout << out;
    return 0;
}