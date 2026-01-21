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

    // Linear sieve to compute smallest prime factor
    for (int i = 2; i <= n; ++i) {
        if (spf[i] == 0) {
            spf[i] = i;
            primes.push_back(i);
        }
        for (int p : primes) {
            long long v = 1LL * p * i;
            if (v > n) break;
            spf[v] = p;
            if (i % p == 0) break;
        }
    }

    // Deterministic pseudo-random generator
    auto rng64 = []() -> uint64_t {
        static uint64_t s = 0x9e3779b97f4a7c15ULL; // fixed seed
        s ^= s >> 12;
        s ^= s << 25;
        s ^= s >> 27;
        return s * 2685821657736338717ULL;
    };

    // Assign random signs to primes
    vector<int8_t> ps(n + 1, 0);
    for (int p : primes) {
        ps[p] = (rng64() & 1) ? int8_t(1) : int8_t(-1);
    }

    // Compute f using multiplicativity: f(i) = f(spf[i]) * f(i/spf[i])
    vector<int8_t> f(n + 1, 1);
    f[1] = 1;
    for (int i = 2; i <= n; ++i) {
        int p = spf[i];
        f[i] = int8_t(int(ps[p]) * int(f[i / p]));
    }

    // Output
    string out;
    out.reserve(n * 3 + 8);
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