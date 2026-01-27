#include <bits/stdc++.h>
using namespace std;

using ll = long long;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int T;
    if(!(cin >> T)) return 0;
    const ll INF = (ll)4e18;
    while (T--) {
        int n, m;
        ll c;
        cin >> n >> m >> c;
        vector<ll> a(n+1), P(n+1, 0);
        for (int i = 1; i <= n; ++i) {
            cin >> a[i];
            P[i] = P[i-1] + a[i];
        }
        vector<ll> b(m+1, 0), Tpref(m+1, 0);
        for (int i = 1; i <= m; ++i) {
            cin >> b[i];
            Tpref[i] = Tpref[i-1] + b[i];
        }
        auto Kval = [&](ll s)->int{
            if (s < 0) return 0;
            int k = int(upper_bound(Tpref.begin(), Tpref.end(), s) - Tpref.begin()) - 1;
            if (k < 0) k = 0;
            if (k > m) k = m;
            return k;
        };

        vector<ll> dp(n+1, (ll)-4e18);
        dp[0] = 0;

        vector<int> curK(n+1, 0);
        vector<ll> nextTime(n+1, INF);
        vector<ll> curVal(n+1, (ll)-4e18);
        vector<char> alive(n+1, 0);

        struct MinEvCmp {
            bool operator()(const pair<ll,int>& a, const pair<ll,int>& b) const {
                if (a.first != b.first) return a.first > b.first;
                return a.second > b.second;
            }
        };
        priority_queue<pair<ll,int>, vector<pair<ll,int>>, MinEvCmp> evHeap;

        priority_queue<pair<ll,int>> valHeap; // max by value
        priority_queue<pair<ll,int>, vector<pair<ll,int>>, MinEvCmp> pruneHeap; // min by max possible value

        auto push_event = [&](int j){
            if (!alive[j]) return;
            if (curK[j] < m) {
                nextTime[j] = P[j] + Tpref[curK[j] + 1];
                evHeap.push({nextTime[j], j});
            } else {
                nextTime[j] = INF;
            }
        };

        auto insert_j = [&](int j, ll currentBound){
            int k0 = Kval(0);
            curK[j] = k0;
            curVal[j] = dp[j] - c + curK[j];
            ll maxVal = dp[j] - c + m;
            if (maxVal <= currentBound) {
                alive[j] = 0;
                nextTime[j] = INF;
                return;
            }
            alive[j] = 1;
            valHeap.push({curVal[j], j});
            pruneHeap.push({maxVal, j});
            push_event(j);
        };

        // initialize with j=0 before any i
        alive[0] = 1;
        curK[0] = Kval(0);
        curVal[0] = dp[0] - c + curK[0];
        valHeap.push({curVal[0], 0});
        ll maxVal0 = dp[0] - c + m;
        pruneHeap.push({maxVal0, 0});
        if (curK[0] < m) {
            nextTime[0] = P[0] + Tpref[curK[0] + 1];
            evHeap.push({nextTime[0], 0});
        } else nextTime[0] = INF;

        ll lastBest = (ll)-4e18;

        for (int i = 1; i <= n; ++i) {
            ll x = P[i];

            // Process all events up to current x
            while (!evHeap.empty() && evHeap.top().first <= x) {
                auto [t, j] = evHeap.top(); evHeap.pop();
                if (!alive[j]) continue;
                if (t != nextTime[j]) continue; // stale
                int nk = Kval(x - P[j]);
                if (nk > curK[j]) {
                    curK[j] = nk;
                    curVal[j] = dp[j] - c + curK[j];
                    valHeap.push({curVal[j], j});
                }
                push_event(j);
            }

            // prune by current known bound (lastBest is previous dp value)
            while (!pruneHeap.empty() && pruneHeap.top().first <= lastBest) {
                auto [mxv, j] = pruneHeap.top(); pruneHeap.pop();
                if (!alive[j]) continue;
                // ensure still valid
                if (dp[j] - c + m <= lastBest) {
                    alive[j] = 0;
                }
            }

            // Get best value for dp[i]
            ll best = lastBest; // non-decreasing lower bound
            while (!valHeap.empty()) {
                auto [v, j] = valHeap.top();
                if (!alive[j] || v != curVal[j] || j >= i) {
                    valHeap.pop();
                    continue;
                }
                best = max(best, v);
                break;
            }
            if (best == (ll)-4e18) best = lastBest; // safety
            dp[i] = best;
            lastBest = dp[i];

            // Insert new j = i with pruning
            insert_j(i, lastBest);
        }

        cout << dp[n] << "\n";
    }
    return 0;
}