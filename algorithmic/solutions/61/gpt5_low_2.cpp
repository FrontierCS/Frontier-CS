#include <bits/stdc++.h>
using namespace std;

using ll = long long;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int T;
    if(!(cin >> T)) return 0;
    while (T--) {
        int n, m;
        ll c;
        cin >> n >> m >> c;
        vector<ll> a(n+1), P(n+1, 0);
        for (int i = 1; i <= n; ++i) {
            cin >> a[i];
            P[i] = P[i-1] + a[i];
        }
        vector<ll> b(m+1), B(m+1, 0);
        for (int i = 1; i <= m; ++i) {
            cin >> b[i];
            B[i] = B[i-1] + b[i];
        }
        // B[0]=0 .. B[m]
        auto H = [&](ll S)->ll{
            // returns max k in [0..m] with B[k] <= S
            if (S < 0) return 0;
            int k = int(upper_bound(B.begin(), B.end(), S) - B.begin()) - 1;
            if (k < 0) k = 0;
            if (k > m) k = m;
            return k;
        };

        vector<ll> dp(n+1, (ll)-4e18);
        dp[0] = 0;

        function<void(int,int,int,int)> solve = [&](int l, int r, int optL, int optR){
            if (l > r) return;
            int mid = (l + r) >> 1;
            ll bestVal = (ll)-4e18;
            int bestK = optL;
            int upper = min(optR, mid - 1);
            for (int j = optL; j <= upper; ++j) {
                ll val = dp[j] + H(P[mid] - P[j]) - c;
                if (val > bestVal) {
                    bestVal = val;
                    bestK = j;
                }
            }
            dp[mid] = bestVal;
            solve(l, mid - 1, optL, bestK);
            solve(mid + 1, r, bestK, optR);
        };

        solve(1, n, 0, n-1);

        cout << dp[n] << "\n";
    }
    return 0;
}