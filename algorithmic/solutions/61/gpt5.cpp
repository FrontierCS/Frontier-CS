#include <bits/stdc++.h>
using namespace std;

using ll = long long;

struct Candidate {
    int idx;       // u index
    ll A;          // Dpref[u] at insertion time
    int start;     // earliest row i where this candidate becomes optimal
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        int n, m;
        ll c;
        cin >> n >> m >> c;
        vector<ll> a(n+1), P(n+1, 0);
        for (int i = 1; i <= n; ++i) {
            cin >> a[i];
            P[i] = P[i-1] + a[i];
        }
        vector<ll> B(m);
        for (int i = 0; i < m; ++i) {
            ll x; cin >> x;
            B[i] = (i ? B[i-1] : 0) + x;
        }

        auto level = [&](ll diff)->int{
            // number of B <= diff
            return int(upper_bound(B.begin(), B.end(), diff) - B.begin());
        };

        vector<ll> dp(n+1, LLONG_MIN/4), Dpref(n+1, LLONG_MIN/4);
        dp[0] = 0;
        Dpref[0] = 0;

        deque<Candidate> dq;
        dq.push_back({0, Dpref[0], 1});

        auto valueAt = [&](int i, const Candidate &cand)->ll{
            // assume i >= cand.idx + 1
            ll diff = P[i] - P[cand.idx];
            int k = level(diff);
            return cand.A + (ll)k - c;
        };

        auto betterOrEqual = [&](int i, const Candidate &a, const Candidate &b)->bool{
            // return true if a is >= b at row i
            return valueAt(i, a) >= valueAt(i, b);
        };

        for (int i = 1; i <= n; ++i) {
            while (dq.size() >= 2 && dq[1].start <= i) dq.pop_front();
            dp[i] = valueAt(i, dq.front());
            Dpref[i] = max(Dpref[i-1], dp[i]);

            if (Dpref[i] > Dpref[i-1]) {
                Candidate newC{ i, Dpref[i], n+1 };
                // Insert new candidate
                while (!dq.empty()) {
                    Candidate last = dq.back();
                    int left = max(i + 1, last.start);
                    if (left > n) { newC.start = n+1; break; }
                    if (!betterOrEqual(n, newC, last)) { newC.start = n+1; break; }
                    int lo = left, hi = n;
                    while (lo < hi) {
                        int mid = (lo + hi) >> 1;
                        if (betterOrEqual(mid, newC, last)) hi = mid;
                        else lo = mid + 1;
                    }
                    newC.start = lo;
                    if (newC.start <= last.start) dq.pop_back();
                    else break;
                }
                if (newC.start <= n) dq.push_back(newC);
            }
        }

        cout << dp[n] << "\n";
    }
    return 0;
}