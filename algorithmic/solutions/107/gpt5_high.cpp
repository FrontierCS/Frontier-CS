#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int T;
    if (!(cin >> T)) return 0;
    vector<long long> xs(T);
    for (int i = 0; i < T; ++i) {
        if (!(cin >> xs[i])) xs[i] = 1;
    }
    long long max_x = 1;
    for (auto v : xs) if (v > max_x) max_x = v;
    int limit = (int) sqrt((long double)max_x) + 1;
    vector<int> primes;
    if (limit >= 2) {
        vector<bool> is_prime(limit + 1, true);
        is_prime[0] = is_prime[1] = false;
        for (int i = 2; i * 1LL * i <= limit; ++i) {
            if (is_prime[i]) {
                for (long long j = 1LL * i * i; j <= limit; j += i) is_prime[(int)j] = false;
            }
        }
        for (int i = 2; i <= limit; ++i) if (is_prime[i]) primes.push_back(i);
    }
    for (int i = 0; i < T; ++i) {
        long long x = xs[i];
        if (x == 1) {
            cout << 1 << "\n";
            continue;
        }
        long long temp = x;
        long long ans = 1;
        for (int p : primes) {
            if (1LL * p * p > temp) break;
            if (temp % p == 0) {
                int cnt = 0;
                while (temp % p == 0) {
                    temp /= p;
                    cnt++;
                }
                ans *= (cnt + 1);
            }
        }
        if (temp > 1) ans *= 2;
        cout << ans << "\n";
    }
    return 0;
}