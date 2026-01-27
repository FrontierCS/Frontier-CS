#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    if (!(cin >> n)) return 0;
    for (int i = 0; i < n; ++i) {
        int x, y;
        long long r;
        cin >> x >> y >> r;
        int a = x, b = y, c = x + 1, d = y + 1;
        // Ensure within bounds
        if (c > 10000) c = 10000, a = c - 1;
        if (d > 10000) d = 10000, b = d - 1;
        cout << a << ' ' << b << ' ' << c << ' ' << d << '\n';
    }
    return 0;
}