#include <bits/stdc++.h>
using namespace std;
typedef long long ll;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    int T;
    cin >> T;
    while (T--) {
        int n, m;
        ll c;
        cin >> n >> m >> c;
        vector<ll> a(n + 1);
        for (int i = 1; i <= n; ++i) cin >> a[i];
        vector<ll> b(m + 1);
        for (int i = 1; i <= m; ++i) cin >> b[i];
        vector<ll> preB(m + 1, 0);
        for (int i = 1; i <= m; ++i) preB[i] = preB[i - 1] + b[i];
        vector<ll> s(n + 1, 0);
        for (int i = 1; i <= n; ++i) s[i] = s[i - 1] + a[i];
        vector<ll> dp(n + 1, LLONG_MIN);
        dp[0] = 0;
        for (int i = 1; i <= n; ++i) {
            for (int j = 0; j < i; ++j) {
                ll sum = s[i] - s[j];
                int k = upper_bound(preB.begin(), preB.end(), sum) - preB.begin() - 1;
                if (k < 0) k = 0;
                dp[i] = max(dp[i], dp[j] + k - c);
            }
        }
        cout << dp[n] << '\n';
    }
    return 0;
}