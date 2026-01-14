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

    vector<long long> dp;
    dp.reserve(n);
    for (int i = 0; i < n; ++i) {
        auto it = lower_bound(dp.begin(), dp.end(), t[i]);
        if (it == dp.end()) dp.push_back(t[i]);
        else *it = t[i];
    }

    cout << dp.size() << '\n';
    for (int i = 0; i < 10; ++i) {
        cout << 1 << ' ' << 1 << ' ' << 0 << '\n';
    }

    return 0;
}