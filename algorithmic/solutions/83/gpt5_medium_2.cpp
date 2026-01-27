#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;

    vector<int> spf(n + 1, 0);
    vector<int> primes;
    if (n >= 1) spf[1] = 1;
    for (int i = 2; i <= n; ++i) {
        if (spf[i] == 0) {
            spf[i] = i;
            primes.push_back(i);
        }
        for (int p : primes) {
            long long v = 1LL * p * i;
            if (v > n) break;
            spf[v] = p;
            if (p == spf[i]) break;
        }
    }

    vector<int8_t> f(n + 1, 1);
    f[1] = 1;

    uint64_t rng = 88172645463393265ull;
    auto xorshift = [&]() -> uint64_t {
        rng ^= rng << 7;
        rng ^= rng >> 9;
        return rng;
    };

    for (int i = 2; i <= n; ++i) {
        if (spf[i] == i) {
            f[i] = (xorshift() & 1) ? 1 : -1; // assign random ±1 to primes
        } else {
            f[i] = (int8_t)(f[spf[i]] * f[i / spf[i]]);
        }
    }

    string out;
    out.reserve((size_t)n * 3 + 2);
    for (int i = 1; i <= n; ++i) {
        if (f[i] == 1) out += '1';
        else out += "-1";
        if (i < n) out += ' ';
    }
    out += '\n';
    cout << out;

    return 0;
}