#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    long long n;
    if (!(cin >> n)) return 0;

    long long k = 1;
    while (k * k * k < n) ++k;

    cout.setf(ios::fixed);
    cout << setprecision(10);

    long long printed = 0;
    for (long long i = 0; i < k && printed < n; ++i) {
        double x = (i + 0.5) / (double)k;
        for (long long j = 0; j < k && printed < n; ++j) {
            double y = (j + 0.5) / (double)k;
            for (long long l = 0; l < k && printed < n; ++l) {
                double z = (l + 0.5) / (double)k;
                cout << x << ' ' << y << ' ' << z << '\n';
                ++printed;
            }
        }
    }

    return 0;
}