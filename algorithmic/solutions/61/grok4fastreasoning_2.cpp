#include <bits/stdc++.h>
using namespace std;
typedef long long ll;
const ll INF = 1LL << 60;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
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
        vector<ll> A(n + 1, 0);
        for (int i = 1; i <= n; ++i) A[i] = A[i - 1] + a[i - 1];
        vector<ll> B(m + 1, 0);
        for (int i = 1; i <= m; ++i) B[i] = B[i - 1] + b[i - 1];
        vector<ll> dp(n + 1, -INF);
        dp[0] = 0;
        auto cost = [&](int j, int i) -> ll {
            ll s = A[i] - A[j];
            auto it = upper_bound(B.begin(), B.end(), s);
            return (it - B.begin()) - 1;
        };
        function<void(int, int, int, int)> solve = [&](int L, int R, int optl, int optr) {
            if (L > R) return;
            int mid = (L + R) / 2;
            pair<ll, int> best = {-INF, -1};
            for (int j = optl; j <= min(mid - 1, optr); ++j) {
                ll val = dp[j] + cost(j, mid);
                if (val > best.first) {
                    best = {val, j};
                }
            }
            dp[mid] = best.first - c;
            solve(L, mid - 1, optl, best.second);
            solve(mid + 1, R, best.second, optr);
        };
        solve(1, n, 0, n - 1);
        cout << dp[n] << '\n';
    }
}