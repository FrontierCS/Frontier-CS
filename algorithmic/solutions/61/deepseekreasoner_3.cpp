#include <bits/stdc++.h>
using namespace std;

typedef long long ll;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    int T;
    cin >> T;
    while (T--) {
        int n, m, c;
        cin >> n >> m >> c;
        vector<ll> a(n + 1);
        vector<ll> A(n + 1, 0);
        for (int i = 1; i <= n; i++) {
            cin >> a[i];
            A[i] = A[i - 1] + a[i];
        }
        vector<ll> b(m + 1);
        vector<ll> B(m + 1, 0);
        for (int i = 1; i <= m; i++) {
            cin >> b[i];
            B[i] = B[i - 1] + b[i];
        }
        vector<ll> dp(n + 1, -1e18);
        dp[0] = 0;
        for (int i = 1; i <= n; i++) {
            for (int j = 0; j < i; j++) {
                ll s = A[i] - A[j];
                int k = upper_bound(B.begin(), B.end(), s) - B.begin() - 1;
                dp[i] = max(dp[i], dp[j] + k - c);
            }
        }
        cout << dp[n] << '\n';
    }
    return 0;
}