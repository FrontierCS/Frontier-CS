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

    for (int i = 2; i <= n; ++i) {
        if (spf[i] == 0) {
            spf[i] = i;
            primes.push_back(i);
        }
        for (int p : primes) {
            if (p > spf[i] || 1LL * i * p > n) break;
            spf[i * p] = p;
        }
    }

    vector<int> f(n + 1, 1);
    f[1] = 1;
    for (int i = 2; i <= n; ++i) {
        f[i] = -f[i / spf[i]];
    }

    string out;
    out.reserve(3LL * n + 10);
    for (int i = 1; i <= n; ++i) {
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