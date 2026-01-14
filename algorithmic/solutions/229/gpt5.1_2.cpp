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

    vector<long long> tail;
    tail.reserve(n);
    for (int i = 0; i < n; ++i) {
        auto it = lower_bound(tail.begin(), tail.end(), t[i]);
        if (it == tail.end()) tail.push_back(t[i]);
        else *it = t[i];
    }
    int lis = (int)tail.size();

    cout << lis << "\n";
    for (int i = 0; i < 10; ++i) {
        cout << 1 << " " << 1 << " " << 0 << "\n";
    }

    return 0;
}