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

    // Linear sieve to compute smallest prime factors
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

    vector<int8_t> f(n + 1, 0);
    vector<int8_t> valPrime(n + 1, 0);
    string out;
    out.reserve(3LL * n + 10);

    long long S = 0;

    for (int i = 1; i <= n; ++i) {
        int8_t val;
        if (i == 1) {
            val = 1;
        } else if (spf[i] == i) { // prime
            val = (S <= 0 ? 1 : -1);
            valPrime[i] = val;
        } else {
            int p = spf[i];
            val = int8_t(int(f[i / p]) * int(valPrime[p]));
        }
        f[i] = val;
        S += val;

        if (val == 1) out.push_back('1');
        else { out.push_back('-'); out.push_back('1'); }
        if (i < n) out.push_back(' ');
    }
    out.push_back('\n');

    cout << out;
    return 0;
}