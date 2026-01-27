#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) n = 1000000;

    vector<int> lp(n + 1, 0), primes;
    primes.reserve(n / 10);
    vector<signed char> val(n + 1, 1);
    val[1] = 1;

    for (int i = 2; i <= n; ++i) {
        if (lp[i] == 0) {
            lp[i] = i;
            primes.push_back(i);
            val[i] = -1; // Liouville: f(p) = -1
        }
        for (int p : primes) {
            long long j = 1LL * i * p;
            if (j > n) break;
            lp[j] = p;
            val[j] = val[i] * val[p]; // completely multiplicative
            if (i % p == 0) break;
        }
    }

    string out;
    out.reserve((size_t)n * 3);
    for (int i = 1; i <= n; ++i) {
        if (i > 1) out.push_back(' ');
        if (val[i] == 1) out.push_back('1');
        else out.append("-1");
    }
    out.push_back('\n');
    cout << out;
    return 0;
}