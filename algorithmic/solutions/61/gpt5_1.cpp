#include <bits/stdc++.h>
using namespace std;

using int64 = long long;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        int n, m;
        int64 c;
        cin >> n >> m >> c;
        vector<int64> a(n + 1), b(m + 1);
        for (int i = 1; i <= n; ++i) cin >> a[i];
        for (int i = 1; i <= m; ++i) cin >> b[i];
        
        vector<int64> SA(n + 1, 0), SB(m + 1, 0);
        for (int i = 1; i <= n; ++i) SA[i] = SA[i - 1] + a[i];
        for (int i = 1; i <= m; ++i) SB[i] = SB[i - 1] + b[i];
        
        auto Mval = [&](int64 s) -> int {
            int l = 0, r = m;
            while (l < r) {
                int mid = (l + r + 1) >> 1;
                if (SB[mid] <= s) l = mid;
                else r = mid - 1;
            }
            return l;
        };
        
        int z = 0;
        while (z + 1 <= m && SB[z + 1] == 0) ++z;
        if ((int64)z >= c) {
            int64 ans = 0;
            for (int i = 1; i <= n; ++i) {
                int k = Mval(a[i]);
                ans += (int64)k - c;
            }
            cout << ans << '\n';
            continue;
        }
        
        vector<int64> dp(n + 1, LLONG_MIN / 4);
        dp[0] = 0;
        
        function<void(int,int,int,int)> solve = [&](int L, int R, int optL, int optR) {
            if (L > R) return;
            int mid = (L + R) >> 1;
            int64 bestVal = LLONG_MIN / 4;
            int bestK = optL;
            int upper = min(mid - 1, optR);
            if (optL <= upper) {
                for (int j = optL; j <= upper; ++j) {
                    int kval = Mval(SA[mid] - SA[j]);
                    int64 v = dp[j] + (int64)kval - c;
                    if (v > bestVal) {
                        bestVal = v;
                        bestK = j;
                    }
                }
            } else {
                // Fallback to j=0 if range empty (shouldn't happen normally)
                int kval = Mval(SA[mid] - SA[0]);
                bestVal = dp[0] + (int64)kval - c;
                bestK = 0;
            }
            dp[mid] = bestVal;
            solve(L, mid - 1, optL, bestK);
            solve(mid + 1, R, bestK, optR);
        };
        
        solve(1, n, 0, n - 1);
        cout << dp[n] << '\n';
    }
    return 0;
}