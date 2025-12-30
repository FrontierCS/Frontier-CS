#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    long long n;
    if (!(cin >> n)) return 0;

    long long s = 1;
    while (s * s * s < n) ++s;

    double r = 1.0 / (2.0 * s);
    long long cnt = 0;

    cout.setf(ios::fixed);
    cout << setprecision(10);

    for (long long i = 0; i < s && cnt < n; ++i) {
        double x = r + 2.0 * r * i;
        for (long long j = 0; j < s && cnt < n; ++j) {
            double y = r + 2.0 * r * j;
            for (long long k = 0; k < s && cnt < n; ++k) {
                double z = r + 2.0 * r * k;
                cout << x << ' ' << y << ' ' << z << '\n';
                if (++cnt == n) break;
            }
        }
    }

    return 0;
}