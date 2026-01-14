#include <bits/stdc++.h>
using namespace std;

using ll = long long;

ll get_level(ll S, const vector<ll>& pref) {
    if (S < 0) return 0;
    auto it = upper_bound(pref.begin(), pref.end(), S);
    return (it - pref.begin()) - 1;
}

void compute(int l, int r, int optl, int optr, const vector<ll>& P, vector<ll>& dp, ll cc, const vector<ll>& pref) {
    if (l > r) return;
    int mid = (l + r) / 2;
    ll best_val = LLONG_MIN / 2;
    int best_j = -1;
    for (int j = optl; j <= min(mid - 1, optr); ++j) {
        ll S = P[mid] - P[j];
        ll lev = get_level(S, pref);
        ll val = dp[j] + lev - cc;
        if (val > best_val) {
            best_val = val;
            best_j = j;
        }
    }
    dp[mid] = best_val;
    compute(l, mid - 1, optl, best_j, P, dp, cc, pref);
    compute(mid + 1, r, best_j, optr, P, dp, cc, pref);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    int T;
    cin >> T;
    for (int t = 0; t < T; ++t) {
        int n, m;
        ll c;
        cin >> n >> m >> c;
        vector<ll> a(n + 1, 0);
        for (int i = 1; i <= n; ++i) {
            cin >> a[i];
        }
        vector<ll> P(n + 1, 0);
        for (int i = 1; i <= n; ++i) {
            P[i] = P[i - 1] + a[i];
        }
        vector<ll> b(m);
        for (int i = 0; i < m; ++i) {
            cin >> b[i];
        }
        vector<ll> pref(m + 1, 0);
        for (int k = 1; k <= m; ++k) {
            pref[k] = pref[k - 1] + b[k - 1];
        }
        vector<ll> dp(n + 1, LLONG_MIN / 2);
        dp[0] = 0;
        compute(1, n, 0, n - 1, P, dp, c, pref);
        cout << dp[n] << '\n';
    }
    return 0;
}