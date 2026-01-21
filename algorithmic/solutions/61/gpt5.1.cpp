#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;
    const long long NEG_INF = (long long)-4e18;

    while (T--) {
        int n, m;
        long long c;
        cin >> n >> m >> c;
        vector<long long> a(n + 1), b(m + 1);
        for (int i = 1; i <= n; ++i) cin >> a[i];
        for (int i = 1; i <= m; ++i) cin >> b[i];

        vector<long long> pa(n + 1), pb(m + 1);
        for (int i = 1; i <= n; ++i) pa[i] = pa[i - 1] + a[i];
        for (int i = 1; i <= m; ++i) pb[i] = pb[i - 1] + b[i];

        vector<long long> dp(n + 1, NEG_INF);
        dp[0] = 0;

        for (int i = 1; i <= n; ++i) {
            long long best = NEG_INF;
            for (int j = 0; j < i; ++j) {
                long long L = pa[i] - pa[j];
                int k = upper_bound(pb.begin(), pb.end(), L) - pb.begin() - 1;
                if (k < 0) k = 0;
                long long cand = dp[j] + k - c;
                if (cand > best) best = cand;
            }
            dp[i] = best;
        }

        cout << dp[n] << '\n';
    }

    return 0;
}