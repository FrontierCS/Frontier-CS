#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    long long n;
    if (!(cin >> n)) return 0;

    long long s = 1;
    while (s * s * s < n) ++s;
    int S = static_cast<int>(s);
    double invS = 1.0 / S;

    cout.setf(ios::fixed);
    cout << setprecision(10);

    long long count = 0;
    for (int i = 0; i < S && count < n; ++i) {
        double x = (i + 0.5) * invS;
        for (int j = 0; j < S && count < n; ++j) {
            double y = (j + 0.5) * invS;
            for (int k = 0; k < S && count < n; ++k) {
                double z = (k + 0.5) * invS;
                cout << x << ' ' << y << ' ' << z << '\n';
                ++count;
            }
        }
    }

    return 0;
}