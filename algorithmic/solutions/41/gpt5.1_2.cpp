#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    long long n;
    if (!(cin >> n)) return 0;

    vector<long long> a;
    long long cur = 1;
    while (cur <= n && (int)a.size() < 1000000) {
        a.push_back(cur);
        if (cur > n / 2) break;
        cur *= 2;
    }

    cout << a.size() << '\n';
    for (size_t i = 0; i < a.size(); ++i) {
        if (i) cout << ' ';
        cout << a[i];
    }
    cout << '\n';

    return 0;
}