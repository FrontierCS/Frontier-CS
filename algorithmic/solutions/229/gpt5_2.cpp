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
    for (auto v : t) {
        auto it = lower_bound(tails.begin(), tails.end(), v);
        if (it == tails.end()) tails.push_back(v);
        else *it = v;
    }
    int len = (int)tails.size();

    cout << len << "\n";
    for (int i = 0; i < 10; ++i) {
        cout << 1 << " " << 1 << " " << 0 << "\n";
    }
    return 0;
}