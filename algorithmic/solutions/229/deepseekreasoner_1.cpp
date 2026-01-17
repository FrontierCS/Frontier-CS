#include <bits/stdc++.h>
using namespace std;

typedef long long ll;

struct Run {
    int l, r;
    int min_val, max_val;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, x;
    cin >> n >> x;
    vector<int> t(n+1);
    for (int i = 1; i <= n; i++) {
        cin >> t[i];
    }

    // Compute original LIS length
    vector<int> tails;
    for (int i = 1; i <= n; i++) {
        auto it = lower_bound(tails.begin(), tails.end(), t[i]);
        if (it == tails.end()) tails.push_back(t[i]);
        else *it = t[i];
    }
    int orig_lis = tails.size();

    // If x == 0, cannot change anything
    if (x == 0) {
        cout << orig_lis << "\n";
        for (int i = 0; i < 10; i++) {
            cout << "1 1 0\n";
        }
        return 0;
    }

    // Compute strictly increasing runs
    vector<Run> runs;
    int start = 1;
    for (int i = 2; i <= n; i++) {
        if (t[i] <= t[i-1]) { // end of a strictly increasing run
            runs.push_back({start, i-1, t[start], t[i-1]});
            start = i;
        }
    }
    runs.push_back({start, n, t[start], t[n]});
    int m = runs.size();

    // If number of runs <= 11, try to make the whole array strictly increasing
    if (m <= 11) {
        vector<ll> required_delta(m-1);
        ll total_ops_needed = 0;
        bool feasible = true;
        for (int i = 0; i < m-1; i++) {
            int max_i = runs[i].max_val;
            int min_next = runs[i+1].min_val;
            // Since runs are separated by a drop, max_i >= min_next
            ll diff = max_i - min_next;
            required_delta[i] = diff + 1; // need s_{i+1} - s_i > diff
            // Each operation can contribute at most x (positive)
            ll ops_i = (required_delta[i] + x - 1) / x; // ceil division
            total_ops_needed += ops_i;
            if (total_ops_needed > 10) {
                feasible = false;
                break;
            }
        }
        if (feasible) {
            // Construct operations
            vector<tuple<int, int, ll>> ops;
            for (int i = 0; i < m-1; i++) {
                int l = runs[i+1].l;
                int r = n;
                ll delta = required_delta[i];
                ll ops_i = (delta + x - 1) / x;
                for (int j = 0; j < ops_i; j++) {
                    ll d;
                    if (j < ops_i - 1) d = x;
                    else d = delta - (ops_i - 1) * x;
                    ops.emplace_back(l, r, d);
                }
            }
            // Fill with dummy operations if necessary
            while (ops.size() < 10) {
                ops.emplace_back(1, 1, 0);
            }
            // Output claimed LIS length (n) and operations
            cout << n << "\n";
            for (auto [l, r, d] : ops) {
                cout << l << " " << r << " " << d << "\n";
            }
            return 0;
        }
    }

    // Fallback: output original LIS and dummy operations
    cout << orig_lis << "\n";
    for (int i = 0; i < 10; i++) {
        cout << "1 1 0\n";
    }
    return 0;
}