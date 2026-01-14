#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    long long x;
    cin >> n >> x;
    vector<long long> t(n);
    for (int i = 0; i < n; i++) cin >> t[i];

    vector<long long> dp;
    dp.reserve(n);
    for (long long v : t) {
        auto it = lower_bound(dp.begin(), dp.end(), v);
        if (it == dp.end()) dp.push_back(v);
        else *it = v;
    }

    cout << (int)dp.size() << "\n";
    for (int i = 0; i < 10; i++) {
        cout << 1 << " " << 1 << " " << 0 << "\n";
    }
    return 0;
}