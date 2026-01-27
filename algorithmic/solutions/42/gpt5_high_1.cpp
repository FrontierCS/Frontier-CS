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
    cout << setprecision(6) << L << "\n";

    for (long long i = 0; i < n; ++i) {
        long long r = i / m;
        long long c = i % m;
        double x = (double)c + 0.5;
        double y = (double)r + 0.5;
        double a = 0.0;
        cout << setprecision(6) << x << " " << y << " " << a << "\n";
    }

    return 0;
}