#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int T;
    if (!(cin >> T)) return 0;
    
    const int MAXP = 100000;
    vector<int> primes;
    vector<bool> is_composite(MAXP + 1, false);
    for (int i = 2; i <= MAXP; ++i) {
        if (!is_composite[i]) {
            primes.push_back(i);
            if ((long long)i * i <= MAXP)
                for (long long j = 1LL * i * i; j <= MAXP; j += i)
                    is_composite[j] = true;
        }
    }
    
    while (T--) {
        unsigned long long X;
        if (!(cin >> X)) X = 1;
        unsigned long long n = X;
        unsigned long long ans = 1;
        for (int p : primes) {
            if (1ULL * p * p > n) break;
            if (n % p == 0) {
                int cnt = 0;
                while (n % p == 0) {
                    n /= p;
                    cnt++;
                }
                ans *= (cnt + 1);
            }
        }
        if (n > 1) ans *= 2;
        cout << ans << "\n";
    }
    return 0;
}