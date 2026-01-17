#include <bits/stdc++.h>
using namespace std;

using ll = long long;

void compute(int l, int r, int optl, int optr, vector<ll>& dp, const vector<ll>& S, const vector<ll>& B, int m, ll c) {
    if (l > r) return;
    int mid = (l + r) / 2;
    pair<ll, int> best = {LLONG_MIN / 2, -1};
    for (int j = max(0, optl); j <= min(mid - 1, optr); ++j) {
        ll sumseg = S[mid] - S[j];
        int low = 0, hi = m;
        while (low <= hi) {
            int md = low + (hi - low) / 2;
            if (B[md] <= sumseg) {
                low = md + 1;
            } else {
                hi = md - 1;
            }
        }
        int lev = hi;
        ll val = dp[j] + lev;
        if (val > best.first) {
            best = {val, j};
        }
    }
    dp[mid] = best.first - c;
    compute(l, mid - 1, optl, best.second, dp, S, B, m, c);
    compute(mid + 1, r, best.second, optr, dp, S, B, m, c);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int T;
    cin >> T;
    for (int t = 0; t < T; ++t) {
        int n, m;
        ll c;
        cin >> n >> m >> c;
        vector<ll> a(n + 1);
        for (int i = 1; i <= n; ++i) {
            cin >> a[i];
        }
        vector<ll> S(n + 1, 0);
        for (int i = 1; i <= n; ++i) {
            S[i] = S[i - 1] + a[i];
        }
        vector<ll> b(m + 1);
        for (int i = 1; i <= m; ++i) {
            cin >> b[i];
        }
        vector<ll> B(m + 1, 0);
        for (int k = 1; k <= m; ++k) {
            B[k] = B[k - 1] + b[k];
        }
        vector<ll> dp(n + 1, 0);
        compute(1, n, 0, n, dp, S, B, m, c);
        cout << dp[n] << '\n';
    }
    return 0;
}