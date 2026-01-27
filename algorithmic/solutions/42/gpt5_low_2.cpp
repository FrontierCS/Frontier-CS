#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    long long n;
    if(!(cin >> n)) return 0;
    long long Lside = 0;
    while (Lside * Lside < n) ++Lside;
    double L = static_cast<double>(Lside);
    cout.setf(std::ios::fixed); cout<<setprecision(6);
    cout << L << "\n";
    long long printed = 0;
    for (long long y = 0; y < Lside && printed < n; ++y) {
        for (long long x = 0; x < Lside && printed < n; ++x) {
            double cx = x + 0.5;
            double cy = y + 0.5;
            cout << cx << " " << cy << " " << 0.0 << "\n";
            ++printed;
        }
    }
    return 0;
}