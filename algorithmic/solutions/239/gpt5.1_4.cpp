#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    long long n;
    if (!(cin >> n)) return 0;

    long long m = n * (n - 1) / 2;
    cout << m << '\n';

    for (long long len = 2; len <= n; ++len) {
        for (long long u = 0; u + len <= n; ++u) {
            long long c = u + 1;
            long long v = u + len;
            cout << u << ' ' << c << ' ' << v << '\n';
        }
    }

    return 0;
}