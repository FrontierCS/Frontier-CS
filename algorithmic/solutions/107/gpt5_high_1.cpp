#include <bits/stdc++.h>
using namespace std;

long long count_divisors(long long n) {
    if (n == 0) return 0;
    if (n == 1) return 1;
    long long ans = 1;
    int cnt = 0;
    while ((n & 1LL) == 0) {
        n >>= 1;
        cnt++;
    }
    if (cnt) ans *= (cnt + 1);
    for (long long p = 3; p * p <= n; p += 2) {
        cnt = 0;
        while (n % p == 0) {
            n /= p;
            cnt++;
        }
        if (cnt) ans *= (cnt + 1);
    }
    if (n > 1) ans *= 2;
    return ans;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;
    vector<unsigned long long> xs;
    xs.reserve(T);
    for (int i = 0; i < T; ++i) {
        unsigned long long x;
        if (cin >> x) xs.push_back(x);
        else break;
    }
    for (size_t i = 0; i < xs.size(); ++i) {
        cout << count_divisors((long long)xs[i]) << "\n";
    }
    for (int i = (int)xs.size(); i < T; ++i) {
        cout << 1 << "\n";
    }
    return 0;
}