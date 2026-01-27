#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int T;
    if(!(cin >> T)) return 0;
    while (T--) {
        int n, m;
        long long c;
        cin >> n >> m >> c;
        vector<long long> a(n), b(m+1,0), B(m+1,0);
        long long X = 0;
        for (int i = 0; i < n; ++i) {
            cin >> a[i];
            X += a[i];
        }
        for (int i = 1; i <= m; ++i) {
            cin >> b[i];
            B[i] = B[i-1] + b[i];
        }
        long long ans = LLONG_MIN;
        int maxd = n;
        for (int d = 1; d <= maxd; ++d) {
            long long Xd = X / d;
            int q = upper_bound(B.begin(), B.end(), Xd) - B.begin() - 1;
            if (q < 0) q = 0;
            if (q > m) q = m;
            long long L = 0;
            if (q == m) {
                L = 1LL * d * m;
            } else {
                long long full = 1LL * d * B[q];
                long long rem = X - full;
                if (b[q+1] == 0) {
                    L = 1LL * d * m;
                } else {
                    long long r = rem / b[q+1];
                    if (r > d) r = d;
                    L = 1LL * d * q + r;
                }
            }
            long long val = L - 1LL * c * d;
            if (val > ans) ans = val;
        }
        cout << ans << "\n";
    }
    return 0;
}