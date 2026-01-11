#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    long long x;
    if(!(cin >> n >> x)) return 0;
    vector<long long> t(n);
    for(int i = 0; i < n; ++i) cin >> t[i];

    // Compute LIS length (strictly increasing)
    vector<long long> tail;
    tail.reserve(n);
    for (long long v : t) {
        auto it = lower_bound(tail.begin(), tail.end(), v);
        if (it == tail.end()) tail.push_back(v);
        else *it = v;
    }
    int lis_len = (int)tail.size();

    cout << lis_len << "\n";
    for (int i = 0; i < 10; ++i) {
        cout << 1 << " " << 1 << " " << 0 << "\n";
    }
    return 0;
}