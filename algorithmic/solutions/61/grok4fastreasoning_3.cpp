#include <bits/stdc++.h>
using namespace std;

using ll = long long;
const ll INF = 1LL << 60;

void compute(int l, int r, int optl, int optr, vector<ll>& dp, const vector<ll>& S, const vector<ll>& req, ll c, int n) {
    if (l > r) return;
    int mid = (l + r) / 2;
    pair<ll, int> best = {-INF, -1};
    for (int j = optl; j <= min(mid - 1, optr); ++j) {
        ll tempsum = S[mid] - S[j];
        auto it = upper_bound(req.begin(), req.end(), tempsum);
        int lev = (it - req.begin()) - 1;
        ll val = dp[j] + lev;
        if (val > best.first || (val == best.first && j < best.second)) {
            best = {val, j};
        }
    }
    dp[mid] = best.first - c;
    compute(l, mid - 1, optl, best.second, dp, S, req, c, n);
    compute(mid + 1, r, best.second, optr, dp, S, req, c, n);
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
        vector<ll> a(n);
        for (int i = 0; i < n; ++i) cin >> a[i];
        vector<ll> b(m);
        for (int i = 0; i < m; ++i) cin >> b[i];
        vector<ll> req(m + 1, 0);
        for (int k = 1; k <= m; ++k) {
            req[k] = req[k - 1] + b[k - 1];
        }
        vector<ll> S(n + 1, 0);
        for (int i = 1; i <= n; ++i) {
            S[i] = S[i - 1] + a[i - 1];
        }
        vector<ll> dp(n + 1, 0);
        compute(1, n, 0, n, dp, S, req, c, n);
        cout << dp[n] << '\n';
    }
    return 0;
}