#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    long long n;
    if (!(cin >> n)) return 0;

    if (n <= 1) {
        cout << 0 << '\n';
        return 0;
    }

    long long a = 1;
    while (a * a < n) ++a;

    vector<long long> lens;

    // Small lengths: 2..a-1
    if (a > 2) {
        long long maxSmall = min(n, a - 1);
        for (long long L = 2; L <= maxSmall; ++L) {
            lens.push_back(L);
        }
    }

    // Multiples of a: a, 2a, ..., floor(n/a)*a
    long long p = n / a;
    for (long long k = 1; k <= p; ++k) {
        long long L = k * a;
        if (L >= 2) lens.push_back(L);
    }

    long long m = 0;
    for (long long L : lens) {
        m += (n + 1) - L;
    }

    cout << m << '\n';

    for (long long L : lens) {
        long long x, y;
        if (L < a) {
            x = 1;
            y = L - 1;
        } else if (L == a) {
            x = a - 1;
            y = 1;
        } else {
            x = L - a;
            y = a;
        }

        for (long long u = 0; u + L <= n; ++u) {
            long long c = u + x;
            long long v = u + L;
            cout << u << ' ' << c << ' ' << v << '\n';
        }
    }

    return 0;
}