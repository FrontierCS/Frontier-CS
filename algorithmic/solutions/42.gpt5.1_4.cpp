#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    long long n;
    if (!(cin >> n)) return 0;

    long long m = (long long)ceil(sqrt((long double)n));
    double L = (double)m;

    cout.setf(ios::fixed);
    cout << setprecision(6);
    cout << L << "\n";

    for (long long k = 0; k < n; ++k) {
        long long row = k / m;
        long long col = k % m;
        double x = 0.5 + col;
        double y = 0.5 + row;
        double a = 0.0;
        cout << x << " " << y << " " << a << "\n";
    }

    return 0;
}