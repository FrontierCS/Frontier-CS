#include <bits/stdc++.h>
using namespace std;

using ll = long long;
using ull = unsigned long long;

int n, m;
ll c;
vector<ull> A, B;
vector<ll> dp;

inline int gval(ull x) {
    // returns largest k in [0..m] such that B[k] <= x
    int l = 0, r = m;
    while (l < r) {
        int mid = (l + r + 1) >> 1;
        if (B[mid] <= x) l = mid;
        else r = mid - 1;
    }
    return l;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        cin >> n >> m >> c;
        vector<ull> a(n+1), b(m+1);
        for (int i = 1; i <= n; ++i) cin >> a[i];
        for (int i = 1; i <= m; ++i) cin >> b[i];

        A.assign(n+1, 0);
        for (int i = 1; i <= n; ++i) A[i] = A[i-1] + a[i];

        B.assign(m+1, 0);
        for (int i = 1; i <= m; ++i) B[i] = B[i-1] + b[i];

        dp.assign(n+1, LLONG_MIN/4);
        dp[0] = 0;

        // Heuristic: assume argmax index is nondecreasing (monotone queue-like).
        // Fallback to scanning from 0..i-1 if needed.
        int opt = 0;
        for (int i = 1; i <= n; ++i) {
            ll best = LLONG_MIN/4;
            int bestj = 0;

            // Try from previous optimal j onward
            int start = opt;
            if (start > i-1) start = i-1;
            for (int j = start; j <= i-1; ++j) {
                ll val = dp[j] + (ll)gval(A[i] - A[j]) - c;
                if (val > best) {
                    best = val;
                    bestj = j;
                }
            }
            // Also try earlier j's in case monotonicity fails
            for (int j = 0; j < start; ++j) {
                ll val = dp[j] + (ll)gval(A[i] - A[j]) - c;
                if (val > best) {
                    best = val;
                    bestj = j;
                }
            }
            dp[i] = best;
            opt = bestj;
        }

        cout << dp[n] << "\n";
    }
    return 0;
}