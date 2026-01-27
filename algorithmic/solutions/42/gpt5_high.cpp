#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    long long n;
    if (!(cin >> n)) return 0;
    
    long long k = sqrtl((long double)n);
    if (k * k < n) ++k;
    double L = (double)k;
    
    cout.setf(std::ios::fixed); 
    cout << setprecision(6);
    cout << L << "\n";
    
    long long cnt = 0;
    for (long long r = 0; r < k && cnt < n; ++r) {
        for (long long c = 0; c < k && cnt < n; ++c) {
            double x = 0.5 + (double)c;
            double y = 0.5 + (double)r;
            cout << x << " " << y << " " << 0.0 << "\n";
            ++cnt;
        }
    }
    
    return 0;
}