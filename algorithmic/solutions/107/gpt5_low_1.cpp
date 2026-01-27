#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int T;
    if (!(cin >> T)) return 0;
    
    // Precompute primes up to 100000 (sufficient for sqrt(1e9) ~ 31623)
    int limit = 100000;
    vector<int> primes;
    vector<bool> is_composite(limit + 1, false);
    for (int i = 2; i <= limit; ++i) {
        if (!is_composite[i]) {
            primes.push_back(i);
            if ((long long)i * i <= limit) {
                for (int j = i * i; j <= limit; j += i)
                    is_composite[j] = true;
            }
        }
    }
    
    while (T--) {
        long long X;
        if (!(cin >> X)) X = 0;
        long long n = X;
        long long ans = 1;
        for (int p : primes) {
            if (1LL * p * p > n) break;
            if (n % p == 0) {
                int cnt = 0;
                while (n % p == 0) {
                    n /= p;
                    cnt++;
                }
                ans *= (cnt + 1);
            }
        }
        if (n > 1) ans *= 2; // n is prime
        cout << ans << "\n";
    }
    return 0;
}