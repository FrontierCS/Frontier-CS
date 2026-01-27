#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    vector<vector<int>> a(n, vector<int>(n));
    for (int i = 0; i < n; ++i)
        for (int j = 0; j < n; ++j)
            cin >> a[i][j];

    int B = 0;
    while ((1 << B) < n) ++B;
    int fullMask = (1 << B) - 1;

    vector<int> p(n);
    for (int i = 0; i < n; ++i) {
        int val = fullMask;
        for (int j = 0; j < n; ++j) {
            val &= a[i][j];
        }
        p[i] = val;
    }

    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << p[i];
    }
    cout << '\n';

    return 0;
}