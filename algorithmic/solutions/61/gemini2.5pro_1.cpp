#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <map>

using namespace std;

using ll = long long;

const ll INF = 2e18; 

void solve() {
    int n, m;
    ll c;
    cin >> n >> m >> c;
    vector<ll> a(n);
    for (int i = 0; i < n; ++i) {
        cin >> a[i];
    }
    vector<ll> b(m);
    for (int i = 0; i < m; ++i) {
        cin >> b[i];
    }

    vector<ll> sa(n + 1, 0);
    for (int i = 0; i < n; ++i) {
        sa[i + 1] = sa[i] + a[i];
    }

    vector<ll> sb(m + 1, 0);
    for (int i = 0; i < m; ++i) {
        sb[i + 1] = sb[i] + b[i];
    }

    vector<ll> dp(n + 1, -INF);
    dp[0] = 0;

    map<ll, ll> prefix_max;
    prefix_max[-1] = -INF; 
    prefix_max[sa[0]] = dp[0];

    for (int i = 1; i <= n; ++i) {
        ll max_val = -INF;
        for (int k = 0; k <= m; ++k) {
            ll required_exp = (k > 0) ? sb[k] : 0;
            ll target_sa_j = sa[i] - required_exp;
            
            auto it = prefix_max.upper_bound(target_sa_j);
            --it;
            ll max_prev_dp = it->second;

            if (max_prev_dp > -INF + 1) { 
                 max_val = max(max_val, max_prev_dp + k);
            }
        }
        if (max_val > -INF + 1) {
            dp[i] = max_val - c;
        }
        
        auto it = prefix_max.upper_bound(sa[i]);
        ll prev_max = (--it)->second;
        if (dp[i] > prev_max) {
            prefix_max[sa[i]] = dp[i];
            it = prefix_max.find(sa[i]);
            ++it;
            while(it != prefix_max.end() && it->second <= dp[i]) {
                it = prefix_max.erase(it);
            }
        }
    }

    cout << dp[n] << endl;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    int t;
    cin >> t;
    while (t--) {
        solve();
    }
    return 0;
}