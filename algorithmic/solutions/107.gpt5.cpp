#include <bits/stdc++.h>
using namespace std;

vector<int> sieve(int n) {
    vector<bool> isPrime(n + 1, true);
    isPrime[0] = isPrime[1] = false;
    for (int i = 2; i * 1LL * i <= n; ++i) {
        if (isPrime[i]) {
            for (int j = i * i; j <= n; j += i)
                isPrime[j] = false;
        }
    }
    vector<int> primes;
    for (int i = 2; i <= n; ++i)
        if (isPrime[i]) primes.push_back(i);
    return primes;
}

long long tau(long long n, const vector<int>& primes) {
    if (n <= 1) return 1;
    long long res = 1;
    for (int p : primes) {
        if (1LL * p * p > n) break;
        if (n % p == 0) {
            int cnt = 0;
            while (n % p == 0) {
                n /= p;
                cnt++;
            }
            res *= (cnt + 1);
        }
    }
    if (n > 1) res *= 2;
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    vector<long long> tokens;
    long long x;
    while (cin >> x) tokens.push_back(x);
    if (tokens.empty()) return 0;

    int T = (int)tokens[0];
    int available = (int)tokens.size() - 1;
    int use = min(T, available);

    // Sieve up to 1e6 to comfortably factor numbers up to 1e12 (covers 1e9 easily)
    vector<int> primes = sieve(1000000);

    for (int i = 0; i < use; ++i) {
        long long n = tokens[1 + i];
        cout << tau(n, primes) << "\n";
    }
    return 0;
}