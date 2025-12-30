#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    long long n;
    if (!(cin >> n)) return 0;
    
    long long m = sqrtl((long double)n);
    while (m * m < n) ++m;
    
    cout.setf(ios::fixed);
    cout << setprecision(6) << (double)m << "\n";
    
    for (long long i = 0; i < n; ++i) {
        long long y = i / m;
        long long x = i % m;
        double xi = x + 0.5;
        double yi = y + 0.5;
        double ai = 0.0;
        cout << setprecision(6) << xi << " " << yi << " " << ai << "\n";
    }
    return 0;
}