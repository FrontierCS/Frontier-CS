#include <bits/stdc++.h>
using namespace std;

typedef long long ll;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(0);
    
    int n, x;
    cin >> n >> x;
    vector<ll> t(n+1);
    for (int i = 1; i <= n; i++) {
        cin >> t[i];
    }
    
    // If x == 0, no changes possible.
    if (x == 0) {
        // Compute LIS of original array
        vector<ll> tails;
        for (int i = 1; i <= n; i++) {
            auto it = lower_bound(tails.begin(), tails.end(), t[i]);
            if (it == tails.end()) tails.push_back(t[i]);
            else *it = t[i];
        }
        int len = tails.size();
        cout << len << "\n";
        for (int i = 0; i < 10; i++) {
            cout << "1 1 0\n";
        }
        return 0;
    }
    
    // Find breaks where t[i] >= t[i+1]
    vector<tuple<int, ll, int>> breaks; // (i, diff, k)
    for (int i = 1; i < n; i++) {
        if (t[i] >= t[i+1]) {
            ll diff = t[i] - t[i+1] + 1; // need > diff-1
            int k = (diff + x - 1) / x; // ceil(diff/x)
            breaks.emplace_back(i, diff, k);
        }
    }
    
    // Sort by diff descending
    sort(breaks.begin(), breaks.end(), [](const auto& a, const auto& b) {
        return get<1>(a) > get<1>(b);
    });
    
    vector<tuple<int, int, int>> ops; // (l, r, d)
    int remaining = 10;
    for (auto& [i, diff, k] : breaks) {
        if (k <= remaining) {
            for (int j = 0; j < k; j++) {
                ops.emplace_back(i+1, n, x);
            }
            remaining -= k;
        } else {
            // Use all remaining operations on this break
            for (int j = 0; j < remaining; j++) {
                ops.emplace_back(i+1, n, x);
            }
            remaining = 0;
            break;
        }
        if (remaining == 0) break;
    }
    
    // Fill with dummy operations
    while (ops.size() < 10) {
        ops.emplace_back(1, 1, 0);
    }
    
    // Compute adjusted array v
    vector<ll> shift(n+2, 0);
    for (auto& [l, r, d] : ops) {
        if (d != 0 && l <= n) {
            shift[l] += d;
            if (r < n) shift[r+1] -= d; // not needed since r=n in our construction
        }
    }
    for (int i = 1; i <= n; i++) {
        shift[i] += shift[i-1];
    }
    vector<ll> v(n+1);
    for (int i = 1; i <= n; i++) {
        v[i] = t[i] + shift[i];
    }
    
    // Compute LIS of v
    vector<ll> tails;
    for (int i = 1; i <= n; i++) {
        auto it = lower_bound(tails.begin(), tails.end(), v[i]);
        if (it == tails.end()) tails.push_back(v[i]);
        else *it = v[i];
    }
    int len = tails.size();
    
    // Output
    cout << len << "\n";
    for (auto& [l, r, d] : ops) {
        cout << l << " " << r << " " << d << "\n";
    }
    
    return 0;
}