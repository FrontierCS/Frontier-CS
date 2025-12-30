#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    vector<long long> v;
    long long x;
    while (cin >> x) v.push_back(x);
    if (v.empty()) return 0;

    int n = (int)v[0];

    cout << 3;
    for (int i = 1; i <= n; ++i) {
        cout << ' ' << i;
    }
    cout << '\n';
    return 0;
}