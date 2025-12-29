#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    long long n;
    if(!(cin >> n)) return 0;
    
    long long m = (long long)floor(sqrtl((long double)n));
    if (m * m < n) m++;
    
    cout.setf(std::ios::fixed);
    cout << setprecision(6) << (double)m << "\n";
    
    long long cnt = 0;
    for (long long i = 0; i < m && cnt < n; ++i) {
        for (long long j = 0; j < m && cnt < n; ++j) {
            double x = j + 0.5;
            double y = i + 0.5;
            double a = 0.0;
            cout << setprecision(6) << x << " " << y << " " << a << "\n";
            ++cnt;
        }
    }
    return 0;
}