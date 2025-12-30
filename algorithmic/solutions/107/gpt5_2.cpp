#include <bits/stdc++.h>
using namespace std;

static vector<int> sieve_primes(unsigned int n) {
    vector<bool> is_prime(n + 1, true);
    if (n >= 0) is_prime[0] = false;
    if (n >= 1) is_prime[1] = false;
    for (unsigned int i = 2; i * 1uLL * i <= n; ++i) {
        if (is_prime[i]) {
            for (unsigned long long j = 1ULL * i * i; j <= n; j += i) {
                is_prime[(size_t)j] = false;
            }
        }
    }
    vector<int> primes;
    for (unsigned int i = 2; i <= n; ++i) {
        if (is_prime[i]) primes.push_back((int)i);
    }
    return primes;
}

static unsigned long long count_divisors(unsigned long long n, const vector<int>& primes) {
    if (n == 0) return 0; // not expected, but safe-guard
    unsigned long long res = 1;
    unsigned long long temp = n;
    for (int p : primes) {
        unsigned long long pp = (unsigned long long)p * (unsigned long long)p;
        if (pp > temp) break;
        if (temp % p == 0) {
            unsigned int cnt = 0;
            while (temp % p == 0) {
                temp /= p;
                ++cnt;
            }
            res *= (cnt + 1);
        }
    }
    if (temp > 1) res *= 2;
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int T;
    if (!(cin >> T)) return 0;
    vector<unsigned long long> X(T);
    unsigned long long mx = 0;
    for (int i = 0; i < T; ++i) {
        cin >> X[i];
        if (X[i] > mx) mx = X[i];
    }
    unsigned int limit = (unsigned int)(sqrtl((long double)mx) + 1.0L);
    auto primes = sieve_primes(limit);
    for (int i = 0; i < T; ++i) {
        cout << count_divisors(X[i], primes) << "\n";
    }
    return 0;
}