#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    long long n;
    if (!(cin >> n)) return 0;
    
    long long m = sqrtl((long double)n);
    if (m * m < n) m++;
    long double L = (long double)m;
    
    cout.setf(ios::fixed);
    cout << setprecision(6) << (double)L << "\n";
    
    long long printed = 0;
    for (long long i = 0; i < m && printed < n; ++i) {
        for (long long j = 0; j < m && printed < n; ++j) {
            long double x = (long double)j + 0.5L;
            long double y = (long double)i + 0.5L;
            cout << setprecision(6) << (double)x << " " << (double)y << " " << 0.0 << "\n";
            ++printed;
        }
    }
    
    return 0;
}