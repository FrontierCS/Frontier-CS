#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int T;
    if (!(cin >> T)) return 0;
    vector<long long> X(T);
    for (int i = 0; i < T; ++i) {
        if (!(cin >> X[i])) X[i] = 1;
    }

    const int MAXP = 100000; // > sqrt(1e9) = 31623 is enough
    vector<bool> is_prime(MAXP + 1, true);
    is_prime[0] = is_prime[1] = false;
    for (int i = 2; i * 1LL * i <= MAXP; ++i) {
        if (is_prime[i]) {
            for (int j = i * i; j <= MAXP; j += i) is_prime[j] = false;
        }
    }
    vector<int> primes;
    for (int i = 2; i <= MAXP; ++i) if (is_prime[i]) primes.push_back(i);

    auto tau = [&](long long n) {
        if (n <= 1) return 1LL;
        long long res = 1;
        long long m = n;
        for (int p : primes) {
            if (1LL * p * p > m) break;
            if (m % p == 0) {
                int cnt = 0;
                while (m % p == 0) {
                    m /= p;
                    ++cnt;
                }
                res *= (cnt + 1);
            }
        }
        if (m > 1) res *= 2; // remaining prime factor
        return res;
    };

    for (int i = 0; i < T; ++i) {
        cout << tau(X[i]) << "\n";
    }
    return 0;
}