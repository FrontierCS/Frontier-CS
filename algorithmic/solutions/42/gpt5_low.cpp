#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    long long n;
    if (!(cin >> n)) return 0;
    
    long long k = ceil(sqrt((long double)n));
    double L = (double)k;
    
    cout.setf(std::ios::fixed); 
    cout << setprecision(9);
    cout << L << "\n";
    
    for (long long i = 0; i < n; ++i) {
        long long r = i / k;
        long long c = i % k;
        double x = 0.5 + c;
        double y = 0.5 + r;
        cout << x << " " << y << " " << 0.0 << "\n";
    }
    return 0;
}