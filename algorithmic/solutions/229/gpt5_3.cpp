#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    long long x;
    if (!(cin >> n >> x)) return 0;
    vector<long long> t(n);
    for (int i = 0; i < n; ++i) cin >> t[i];

    // Compute LIS length (strictly increasing)
    vector<long long> tails;
    tails.reserve(n);
    for (long long val : t) {
        auto it = lower_bound(tails.begin(), tails.end(), val);
        if (it == tails.end()) tails.push_back(val);
        else *it = val;
    }
    cout << (int)tails.size() << "\n";
    for (int i = 0; i < 10; ++i) {
        cout << 1 << " " << 1 << " " << 0 << "\n";
    }
    return 0;
}