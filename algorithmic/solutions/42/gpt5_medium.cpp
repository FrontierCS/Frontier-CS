#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    long long n;
    if (!(cin >> n)) return 0;
    
    long long m = (long long)ceil(sqrt((long double)n));
    cout.setf(ios::fixed);
    cout << setprecision(6) << (double)m << "\n";
    
    for (long long i = 0; i < n; ++i) {
        long long row = i / m;
        long long col = i % m;
        double x = (double)col + 0.5;
        double y = (double)row + 0.5;
        cout << x << " " << y << " " << 0.0 << "\n";
    }
    return 0;
}