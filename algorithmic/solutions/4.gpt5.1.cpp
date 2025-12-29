#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    long long k;
    if (!(cin >> n >> k)) return 0;

    vector<long long> v;
    v.reserve(1LL * n * n);

    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            long long x;
            cin >> x;
            v.push_back(x);
        }
    }

    nth_element(v.begin(), v.begin() + (k - 1), v.end());
    cout << v[k - 1] << '\n';

    return 0;
}