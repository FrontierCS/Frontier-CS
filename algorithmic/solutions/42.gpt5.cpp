#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    long long n;
    if (!(cin >> n)) return 0;
    long long k = (long long)ceil(sqrt((long double)n));
    double L = (double)k;

    cout.setf(std::ios::fixed); 
    cout << setprecision(6);
    cout << L << "\n";
    for (long long i = 0; i < n; ++i) {
        long long row = i / k;
        long long col = i % k;
        double x = col + 0.5;
        double y = row + 0.5;
        double a = 0.0;
        cout << x << " " << y << " " << a << "\n";
    }
    return 0;
}