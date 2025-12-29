#include <bits/stdc++.h>
using namespace std;
typedef long long ll;

void compute(int L, int R, int optl, int optr, vector<ll>& dp, const vector<ll>& S, const vector<ll>& cost, ll c) {
    if (L > R) return;
    int mid = (L + R) / 2;
    pair<ll, int> best = {LLONG_MIN / 2, -1};
    for (int j = optl; j <= min(mid - 1, optr); ++j) {
        ll U = S[mid] - S[j];
        auto it = upper_bound(cost.begin(), cost.end(), U);
        ll lev = it - cost.begin() - 1;
        ll val = dp[j] + lev - c;
        if (val > best.first) {
            best = {val, j};
        }
    }
    dp[mid] = best.first;
    compute(L, mid - 1, optl, best.second, dp, S, cost, c);
    compute(mid + 1, R, best.second, optr, dp, S, cost, c);
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
        vector<ll> a(n);
        for (auto& x : a) cin >> x;
        vector<ll> b(m);
        for (auto& x : b) cin >> x;
        vector<ll> S(n + 1, 0);
        for (int i = 1; i <= n; ++i) {
            S[i] = S[i - 1] + a[i - 1];
        }
        vector<ll> cost(m + 1, 0);
        for (int k = 1; k <= m; ++k) {
            cost[k] = cost[k - 1] + b[k - 1];
        }
        vector<ll> dp(n + 1, LLONG_MIN / 2);
        dp[0] = 0;
        compute(1, n, 0, n - 1, dp, S, cost, c);
        cout << dp[n] << '\n';
    }
    return 0;
}