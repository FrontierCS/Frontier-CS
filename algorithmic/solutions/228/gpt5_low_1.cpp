#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    string s;
    if (!(cin >> s)) return 0;
    int n = (int)s.size();
    vector<int> P(n+1, 0);
    for (int i = 0; i < n; ++i) P[i+1] = P[i] + (s[i] == '1');

    auto kmax_calc = [&](long long n)->int{
        long double dn = n;
        long double k = floor((sqrtl(1.0L + 4.0L*dn) - 1.0L)/2.0L);
        if (k < 0) k = 0;
        long long kk = (long long)k;
        while ((kk+1)*(kk+2) <= n) ++kk;
        while (kk*(kk+1) > n) --kk;
        return (int)kk;
    };

    int Kmax = kmax_calc(n);
    const long long Tbudget = 250000000LL; // target ~2.5e8 comparisons
    int K1 = (int)min<long long>(Kmax, max(1LL, Tbudget / max(1, n)));

    long long ans = 0;

    for (int k = 1; k <= K1; ++k) {
        int L = k*(k+1);
        if (L > n) break;
        // Count windows length L with exactly k ones
        for (int i = 0; i + L <= n; ++i) {
            if (P[i+L] - P[i] == k) ++ans;
        }
    }

    // Process k with large L where number of starts is small
    const int Smax = 200000; // maximum starts processed per k in this phase
    for (int k = Kmax; k > K1; --k) {
        long long L = 1LL*k*(k+1);
        long long starts = n - L + 1;
        if (starts <= 0) continue;
        if (starts > Smax) break;
        int iMax = (int)starts;
        for (int i = 0; i < iMax; ++i) {
            if (P[i + (int)L] - P[i] == k) ++ans;
        }
    }

    cout << ans << '\n';
    return 0;
}