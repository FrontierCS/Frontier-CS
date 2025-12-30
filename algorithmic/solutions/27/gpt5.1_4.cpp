#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    long long n, m;
    if (!(cin >> n >> m)) return 0;

    long long k = n + m - 1;
    cout << k << '\n';

    // First row: all columns
    for (int c = 1; c <= m; ++c) {
        cout << 1 << ' ' << c << '\n';
    }
    // First column: remaining rows
    for (int r = 2; r <= n; ++r) {
        cout << r << ' ' << 1 << '\n';
    }

    return 0;
}