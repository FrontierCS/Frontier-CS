#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    long long n;
    if (!(cin >> n)) return 0;

    long long m = 1;
    while (m * m * m < n) ++m;

    double step = 1.0 / static_cast<double>(m);
    long long cnt = 0;

    cout.setf(ios::fixed);
    cout << setprecision(10);

    for (long long i = 0; i < m && cnt < n; ++i) {
        double x = (i + 0.5) * step;
        for (long long j = 0; j < m && cnt < n; ++j) {
            double y = (j + 0.5) * step;
            for (long long k = 0; k < m && cnt < n; ++k) {
                double z = (k + 0.5) * step;
                cout << x << ' ' << y << ' ' << z << '\n';
                ++cnt;
            }
        }
    }

    return 0;
}