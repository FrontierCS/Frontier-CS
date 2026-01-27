#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    long long n;
    if (!(cin >> n)) return 0;
    long long k = sqrt((long double)n);
    while (k * k < n) ++k;
    cout.setf(ios::fixed);
    cout << setprecision(6) << (double)k << "\n";
    for (long long i = 0; i < n; ++i) {
        long long x = i % k;
        long long y = i / k;
        double cx = 0.5 + (double)x;
        double cy = 0.5 + (double)y;
        double a = 0.0;
        cout << setprecision(6) << cx << " " << cy << " " << a << "\n";
    }
    return 0;
}