#include <bits/stdc++.h>
using namespace std;
typedef long long ll;

const ll INF = 1e18;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int T;
    cin >> T;
    while (T--) {
        int n, m;
        ll c;
        cin >> n >> m >> c;
        vector<ll> a(n + 1), b(m + 1);
        for (int i = 1; i <= n; ++i) cin >> a[i];
        for (int i = 1; i <= m; ++i) cin >> b[i];

        vector<ll> A(n + 1), B(m + 1);
        A[0] = 0;
        for (int i = 1; i <= n; ++i) A[i] = A[i - 1] + a[i];
        B[0] = 0;
        for (int i = 1; i <= m; ++i) B[i] = B[i - 1] + b[i];

        vector<ll> dp(n + 1, -INF);
        dp[0] = 0;
        vector<ll> pref_max(n + 1, -INF);
        pref_max[0] = 0;

        for (int i = 1; i <= n; ++i) {
            ll best = -INF;
            // only consider k such that B[k] <= A[i]
            int k_max = upper_bound(B.begin(), B.end(), A[i]) - B.begin() - 1;
            for (int k = 0; k <= k_max; ++k) {
                ll x = A[i] - B[k];
                // find largest j with A[j] <= x and j < i
                int lo = 0, hi = i - 1, idx = -1;
                while (lo <= hi) {
                    int mid = (lo + hi) / 2;
                    if (A[mid] <= x) {
                        idx = mid;
                        lo = mid + 1;
                    } else {
                        hi = mid - 1;
                    }
                }
                if (idx >= 0) {
                    ll val = (k - c) + pref_max[idx];
                    if (val > best) best = val;
                }
            }
            dp[i] = best;
            pref_max[i] = max(pref_max[i - 1], dp[i]);
        }
        cout << dp[n] << '\n';
    }
    return 0;
}