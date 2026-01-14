#include <bits/stdc++.h>
using namespace std;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, x;
    cin >> n >> x;
    vector<int> t(n);
    for (int i = 0; i < n; ++i) {
        cin >> t[i];
    }

    // Compute original LIS length
    vector<int> dp;
    for (int val : t) {
        auto it = lower_bound(dp.begin(), dp.end(), val);
        if (it == dp.end()) {
            dp.push_back(val);
        } else {
            *it = val;
        }
    }
    int orig_lis = dp.size();

    // Find positions where sequence is non-increasing (1-indexed)
    vector<int> bad;
    for (int i = 0; i < n - 1; ++i) {
        if (t[i] >= t[i + 1]) {
            bad.push_back(i + 1);
        }
    }

    // If at most 10 such positions, try to make the whole sequence increasing
    if (bad.size() <= 10) {
        vector<pair<int, int>> segments; // (start, end) inclusive, 1-indexed
        int start = 1;
        for (int b : bad) {
            segments.emplace_back(start, b);
            start = b + 1;
        }
        segments.emplace_back(start, n);

        vector<int> inc;
        bool possible = true;
        for (size_t i = 0; i + 1 < segments.size(); ++i) {
            int last_idx = segments[i].second;
            int first_next_idx = segments[i + 1].first;
            int need = t[last_idx - 1] - t[first_next_idx - 1] + 1;
            inc.push_back(need);
            if (need > x) {
                possible = false;
                break;
            }
        }

        if (possible) {
            cout << n << "\n";
            int op_count = 0;
            for (size_t i = 0; i < inc.size(); ++i) {
                int l = segments[i + 1].first;
                int r = n;
                int d = inc[i];
                cout << l << " " << r << " " << d << "\n";
                ++op_count;
            }
            while (op_count < 10) {
                cout << "1 1 0\n";
                ++op_count;
            }
            return 0;
        }
    }

    // Fallback: original LIS and dummy operations
    cout << orig_lis << "\n";
    for (int i = 0; i < 10; ++i) {
        cout << "1 1 0\n";
    }
    return 0;
}