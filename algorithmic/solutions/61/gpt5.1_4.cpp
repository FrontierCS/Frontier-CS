#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        int n, m;
        long long c;
        cin >> n >> m >> c;
        vector<long long> a(n + 1), b(m + 1);
        for (int i = 1; i <= n; ++i) cin >> a[i];
        for (int i = 1; i <= m; ++i) cin >> b[i];

        // Prefix sums of a
        vector<long long> prefA(n + 1, 0);
        for (int i = 1; i <= n; ++i) prefA[i] = prefA[i - 1] + a[i];

        // Prefix sums of b => thresholds B_k
        vector<long long> B(m + 1, 0);
        for (int i = 1; i <= m; ++i) B[i] = B[i - 1] + b[i];

        // DP
        const long long NEG_INF = (long long)-4e18;
        vector<long long> dp(n + 1, NEG_INF);
        dp[0] = 0;

        for (int i = 1; i <= n; ++i) {
            long long best = NEG_INF;
            for (int j = 0; j < i; ++j) {
                long long S = prefA[i] - prefA[j];
                // find largest k such that B[k] <= S
                int k = int(upper_bound(B.begin(), B.end(), S) - B.begin()) - 1;
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