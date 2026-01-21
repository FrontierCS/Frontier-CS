#include <bits/stdc++.h>
using namespace std;

using ll = long long;
const ll NEG_INF = (ll)-4e18;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        int n, m;
        ll c;
        cin >> n >> m >> c;
        vector<ll> a(n + 1), b(m + 1);
        for (int i = 1; i <= n; ++i) cin >> a[i];
        for (int i = 1; i <= m; ++i) cin >> b[i];

        vector<ll> preA(n + 1, 0), preB(m + 1, 0);
        for (int i = 1; i <= n; ++i) preA[i] = preA[i - 1] + a[i];
        for (int i = 1; i <= m; ++i) preB[i] = preB[i - 1] + b[i];

        vector<ll> dp(n + 1, NEG_INF);
        dp[0] = 0;

        for (int i = 1; i <= n; ++i) {
            ll best = NEG_INF;
            for (int t = 0; t < i; ++t) {
                ll S = preA[i] - preA[t];
                int k = upper_bound(preB.begin(), preB.end(), S) - preB.begin() - 1;
                if (k < 0) k = 0;
                if (k > m) k = m;
                ll cand = dp[t] + (ll)k - c;
                if (cand > best) best = cand;
            }
            dp[i] = best;
        }

        cout << dp[n] << "\n";
    }
    return 0;
}