#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    long long n;
    if (!(cin >> n)) return 0;
    
    int k = (int)ceil(sqrt((long double)n));
    double L = (double)k;
    
    cout.setf(ios::fixed);
    cout << setprecision(10);
    cout << L << "\n";
    
    for (long long i = 0; i < n; ++i) {
        long long row = i / k;
        long long col = i % k;
        double x = 0.5 + col;
        double y = 0.5 + row;
        cout << x << " " << y << " 0.000000\n";
    }
    
    return 0;
}