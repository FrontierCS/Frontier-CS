#include <bits/stdc++.h>
using namespace std;

using int64 = long long;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int T;
    if (!(cin >> T)) return 0;
    vector<unsigned long long> nums(T);
    unsigned long long mx = 0;
    for (int i = 0; i < T; ++i) {
        cin >> nums[i];
        mx = max(mx, nums[i]);
    }
    unsigned long long limit = (unsigned long long)(sqrtl((long double)mx)) + 1;
    vector<int> primes;
    if (limit >= 2) {
        vector<bool> isComp(limit + 1, false);
        for (unsigned long long i = 2; i <= limit; ++i) {
            if (!isComp[i]) {
                primes.push_back((int)i);
                if (i * i <= limit) {
                    for (unsigned long long j = i * i; j <= limit; j += i)
                        isComp[j] = true;
                }
            }
        }
    }

    for (int i = 0; i < T; ++i) {
        unsigned long long n = nums[i];
        if (n == 1) {
            cout << 1 << '\n';
            continue;
        }
        unsigned long long ans = 1;
        unsigned long long temp = n;
        for (int p : primes) {
            unsigned long long pp = (unsigned long long)p;
            if (pp * pp > temp) break;
            if (temp % pp == 0) {
                int cnt = 0;
                while (temp % pp == 0) {
                    temp /= pp;
                    ++cnt;
                }
                ans *= (cnt + 1);
            }
        }
        if (temp > 1) ans *= 2;
        cout << ans << '\n';
    }
    return 0;
}