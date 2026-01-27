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
    vector<long long> tail;
    tail.reserve(n);
    for (auto val : t) {
        auto it = lower_bound(tail.begin(), tail.end(), val);
        if (it == tail.end()) tail.push_back(val);
        else *it = val;
    }
    cout << (int)tail.size() << "\n";
    // Output 10 no-op operations
    for (int i = 0; i < 10; ++i) {
        cout << 1 << " " << 1 << " " << 0 << "\n";
    }
    return 0;
}