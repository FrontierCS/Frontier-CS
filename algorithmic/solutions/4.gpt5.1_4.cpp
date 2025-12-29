#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    long long k;
    if (!(cin >> n >> k)) return 0;

    vector<long long> a;
    a.reserve(1LL * n * n);

    long long x;
    for (long long i = 0; i < 1LL * n * n; ++i) {
        cin >> x;
        a.push_back(x);
    }

    if (k < 1 || k > (long long)a.size()) return 0;

    nth_element(a.begin(), a.begin() + (k - 1), a.end());
    cout << a[k - 1];

    return 0;
}