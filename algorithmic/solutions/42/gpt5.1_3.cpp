#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    long long n;
    if (!(cin >> n)) return 0;

    long long k = sqrt((long double)n);
    if (k * k < n) ++k;
    long double L = (long double)k;

    cout.setf(ios::fixed);
    cout << setprecision(10);
    cout << L << "\n";

    long long placed = 0;
    for (long long i = 0; i < k && placed < n; ++i) {
        for (long long j = 0; j < k && placed < n; ++j) {
            long double x = (long double)j + 0.5L;
            long double y = (long double)i + 0.5L;
            cout << x << " " << y << " " << 0.0L << "\n";
            ++placed;
        }
    }

    return 0;
}